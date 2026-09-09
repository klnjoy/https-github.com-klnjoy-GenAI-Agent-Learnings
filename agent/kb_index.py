"""
Knowledge-base indexer + TF-IDF retriever for the GenAI docs site.

Pure standard library (no external deps, no network) so it works behind the
corporate proxy with zero setup. It:

  1. Walks the authored content/ and Course-Modules markdown.
  2. Splits each page into heading-based chunks.
  3. Tags every chunk with an "area" (snowflake, dbt, databricks, rag, ...).
  4. Builds a TF-IDF index and ranks chunks by cosine similarity to a query.

Used by kb_agent.py (query engine) and ask.py (CLI).
"""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from dataclasses import dataclass, asdict
from pathlib import Path

SITE_ROOT = Path(__file__).resolve().parent.parent
CONTENT_DIR = SITE_ROOT / "content"
DOCS_DIR = SITE_ROOT / "docs"          # includes generated Course-Modules pages
INDEX_PATH = Path(__file__).resolve().parent / "kb_index.json"

# Folders to index (relative to their roots). We index authored content and the
# generated module catalog pages, but not the huge copied binaries.
INDEX_ROOTS = [
    ("content", CONTENT_DIR),
    ("docs-course", DOCS_DIR / "Course-Modules"),
]

# Map a path/text fragment to an "area" tag for filtering.
AREA_RULES = [
    ("snowflake", ("snowflake", "cortex")),
    ("databricks", ("databricks", "spark", "delta", "lakehouse", "mosaic")),
    ("dbt", ("/dbt/", "dbt ", "materializ", "analytics engineer")),
    ("fastapi", ("/fastapi/", "fastapi", "pydantic", "uvicorn", "asgi", "starlette")),
    ("aws", ("/aws/", "lambda", "bedrock", "s3 ")),
    ("vector-db", ("/vector-db/", "vector database", "hnsw", "ivf", "ann index",
                   "cosine similarity", "pgvector", "faiss", "embedding")),
    ("retrieval-tuning", ("/retrieval-tuning/", "top-k", "reranking", "rerank",
                          "cross-encoder", "filtering")),
    ("embeddings", ("/embeddings/", "embedding model", "mtej", "mteb",
                    "sentence-transformer")),
    ("a2a", ("/a2a/", "agent-to-agent", "a2a", "multi-agent coordination")),
    ("cost-optimization", ("/cost-optimization/", "cost optimization",
                           "model routing", "prompt caching")),
    ("rag", ("/rag/", "retrieval-augmented", "retrieval augmented", "chunk")),
    ("mcp", ("/mcp/", "model context protocol")),
    ("langchain", ("/langchain/", "langchain", "lcel")),
    ("langgraph", ("/langgraph/", "langgraph")),
    ("context-engineering", ("/context-engineering/", "context window",
                             "context engineering", "compaction", "memory buffer")),
    ("prompt-engineering", ("/prompt-engineering/", "prompt", "few-shot",
                            "chain-of-thought")),
    ("agent-engineering", ("/agent-engineering/", "agent pattern", "tool design",
                           "multi-agent", "react pattern")),
    ("agentcore", ("/agentcore/", "agentcore", "agentic", "agent loop")),
    ("observability", ("/observability/", "observability", "llm-as-judge",
                       "llm as judge", "tracing", "evaluation metric", "langsmith",
                       "langfuse")),
    ("llmops", ("/llmops/", "llmops", "model serving", "inference server",
                "deployment", "kv cache", "quantization")),
    ("llm-fundamentals", ("/llm-fundamentals/", "token", "temperature",
                          "top-p", "fine-tuning", "transformer")),
    ("graph-db", ("/graph-db/", "graph db", "cypher", "gremlin", "graphrag")),
    ("start-here", ("/start-here/", "learning path", "start here")),
    ("setup-guides", ("/setup-guides/", "setup guide", "getting started",
                      "first rag app", "first agent", "local environment")),
    ("documentation", ("/documentation/", "troubleshooting", "faq",
                       "architecture overview", "model selection")),
    ("enterprise", ("/enterprise/", "rbac", "audit log", "compliance",
                    "reference architecture", "security architecture")),
    ("interview", ("interview",)),
]

STOPWORDS = set(
    "a an the of to in for on and or is are be with as by from at this that it "
    "you your we our can will not what how when which use used using into out "
    "up do does done via per than then them they their its it's".split()
)

TOKEN_RE = re.compile(r"[a-z0-9]+")


def tokenize(text: str) -> list[str]:
    return [t for t in TOKEN_RE.findall(text.lower()) if t not in STOPWORDS and len(t) > 1]


def detect_area(path_str: str, text: str) -> str:
    hay = (path_str + " " + text[:400]).lower()
    for area, keys in AREA_RULES:
        if any(k in hay for k in keys):
            return area
    return "general"


def strip_frontmatter(text: str) -> str:
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            return text[end + 4:]
    return text


def clean_body(text: str) -> str:
    """Remove markdown/admonition artifacts so retrieved text reads cleanly."""
    # Drop fenced code blocks entirely (```mermaid ...```, ```python ...```, etc.).
    # These render as raw text in the chat bubble and pollute retrieval; the
    # prose around them carries the meaning we want to index and return.
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    # Drop HTML comments (e.g. <!-- RELATED-MODULE -->) and raw HTML tags.
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    text = re.sub(r"</?[a-zA-Z][^>]*>", "", text)
    out = []
    for ln in text.splitlines():
        # "??? question \"X\"" / "!!! note \"X\"" -> "Q: X" / "Note: X"
        m = re.match(r'^\s*[?!]{3}\s+(\w+)\s+"(.+?)"\s*$', ln)
        if m:
            kind, title = m.group(1), m.group(2)
            label = "Q" if kind.lower() == "question" else kind.capitalize()
            out.append(f"{label}: {title}")
            continue
        out.append(ln)
    cleaned = "\n".join(out)
    # Collapse the runs of blank lines left where code/diagram blocks were removed.
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned).strip()
    return cleaned


@dataclass
class Chunk:
    id: int
    area: str
    title: str          # nearest heading
    page: str           # page title (first H1)
    source: str         # relative source path for citation
    text: str
    weight: float = 1.0  # ranking multiplier (authored prose > file catalogs)


def chunk_weight(source: str, body: str) -> float:
    """Prefer authored prose; down-weight generated module file-list catalogs."""
    w = 1.0
    if source.startswith("content/"):
        w *= 1.35                      # hand-written study content
    if "Course-Modules/" in source:
        w *= 0.5                       # catalog pages (mostly file lists)
    # If most lines look like "- `file` — size" list items, penalize further.
    lines = [ln for ln in body.splitlines() if ln.strip()]
    if lines:
        listy = sum(1 for ln in lines if ln.lstrip().startswith(("- ", "* ")))
        if listy / len(lines) > 0.6:
            w *= 0.4
    # Down-weight thin, mostly-diagram sections. `body` here has already had its
    # code/mermaid fences stripped by clean_body, so a section that was almost
    # entirely a diagram now has very little prose left — it shouldn't win
    # retrieval over pages that actually explain the concept.
    if len(body.split()) < 25:
        w *= 0.3
    return w


def chunk_markdown(text: str) -> list[tuple[str, str, str]]:
    """Split into (page_title, heading, body) by markdown headings."""
    text = strip_frontmatter(text)
    lines = text.splitlines()
    page_title = ""
    chunks: list[tuple[str, str, str]] = []
    cur_heading = ""
    buf: list[str] = []

    def flush():
        body = "\n".join(buf).strip()
        if body:
            chunks.append((page_title, cur_heading, body))

    in_fence = False
    for ln in lines:
        # Track fenced code blocks so we never treat a Python comment like
        # "# cap iterations" as a markdown heading.
        if ln.lstrip().startswith("```"):
            in_fence = not in_fence
            buf.append(ln)
            continue
        m = None if in_fence else re.match(r"^(#{1,3})\s+(.*\S)\s*$", ln)
        if m:
            level, htext = len(m.group(1)), m.group(2).strip()
            # clean icon shortcodes / emoji from headings
            htext = re.sub(r":[a-z0-9_+-]+:", "", htext).strip()
            if level == 1 and not page_title:
                page_title = htext
            flush()
            buf = []
            cur_heading = htext
        else:
            buf.append(ln)
    flush()
    # clean each chunk body of markdown artifacts
    return [(pt, h, clean_body(b)) for (pt, h, b) in chunks]


def build_index() -> dict:
    chunks: list[Chunk] = []
    cid = 0
    for label, root in INDEX_ROOTS:
        if not root.exists():
            continue
        for md in sorted(root.rglob("*.md")):
            raw = md.read_text(encoding="utf-8", errors="replace")
            rel = md.relative_to(SITE_ROOT).as_posix()
            for page_title, heading, body in chunk_markdown(raw):
                area = detect_area(rel, heading + " " + body)
                chunks.append(Chunk(
                    id=cid, area=area,
                    title=heading or page_title,
                    page=page_title or md.stem,
                    source=rel, text=body,
                    weight=chunk_weight(rel, body),
                ))
                cid += 1

    # TF-IDF
    docs_tokens = [tokenize(c.title + " " + c.text) for c in chunks]
    df: Counter = Counter()
    for toks in docs_tokens:
        for t in set(toks):
            df[t] += 1
    n = len(chunks) or 1
    idf = {t: math.log((n + 1) / (dfi + 1)) + 1 for t, dfi in df.items()}

    vectors = []
    for toks in docs_tokens:
        tf = Counter(toks)
        vec = {t: (tf[t] / len(toks)) * idf[t] for t in tf} if toks else {}
        norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
        vectors.append({t: v / norm for t, v in vec.items()})

    return {
        "chunks": [asdict(c) for c in chunks],
        "idf": idf,
        "vectors": vectors,
    }


def save_index(index: dict, path: Path = INDEX_PATH) -> None:
    path.write_text(json.dumps(index), encoding="utf-8")


def load_index(path: Path = INDEX_PATH) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def query_vector(text: str, idf: dict) -> dict:
    toks = tokenize(text)
    if not toks:
        return {}
    tf = Counter(toks)
    vec = {t: (tf[t] / len(toks)) * idf.get(t, math.log(2) + 1) for t in tf}
    norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
    return {t: v / norm for t, v in vec.items()}


def search(index: dict, question: str, area: str | None = None, k: int = 4):
    qv = query_vector(question, index["idf"])
    q_terms = set(tokenize(question))
    results = []
    for i, cvec in enumerate(index["vectors"]):
        chunk = index["chunks"][i]
        if area and area != "all" and chunk["area"] != area:
            continue
        # cosine sim (both normalized) = dot product, times chunk quality weight
        score = sum(qv.get(t, 0.0) * w for t, w in cvec.items())
        score *= chunk.get("weight", 1.0)

        # Title/heading boost: a query like "prompt engineering best practices"
        # should strongly prefer the page literally titled "Prompt Engineering"
        # over a page that merely happens to say "best practices". We reward
        # overlap between query terms and the chunk's page title + heading.
        if q_terms:
            title_terms = set(tokenize(chunk.get("page", "") + " " + chunk.get("title", "")))
            overlap = len(q_terms & title_terms)
            if overlap:
                score *= 1.0 + 0.6 * overlap

        if score > 0:
            results.append((score, chunk))
    results.sort(key=lambda x: x[0], reverse=True)
    return results[:k]


if __name__ == "__main__":
    idx = build_index()
    save_index(idx)
    areas = Counter(c["area"] for c in idx["chunks"])
    print(f"Indexed {len(idx['chunks'])} chunks into {INDEX_PATH}")
    print("By area:", dict(areas))
