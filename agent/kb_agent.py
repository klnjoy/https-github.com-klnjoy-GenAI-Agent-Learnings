"""
Query engine for the knowledge-base agent.

Retrieves the most relevant chunks (optionally filtered by area) and produces an
answer. Two answer modes:

  - "extractive" (default): no LLM needed. Returns the top passages verbatim with
    citations. Works offline, behind the proxy, with zero setup.
  - "llm": if an LLM backend is configured, synthesizes a grounded answer from the
    retrieved context. Pluggable — see get_llm() below.

Every answer includes citations back to the source markdown pages.
"""

from __future__ import annotations

import os
import textwrap
from dataclasses import dataclass

from kb_index import load_index, search


@dataclass
class Answer:
    text: str
    citations: list  # list[{"label": str, "url": str}]
    area: str
    used_llm: bool


SYSTEM_PROMPT = (
    "You are a study assistant answering ONLY from the provided context, which "
    "comes from the user's personal GenAI/data knowledge base. If the answer is "
    "not in the context, say you don't have it in the knowledge base. Be concise "
    "and cite the source pages."
)


# ---------------------------------------------------------------------------
# Pluggable LLM slot (Phase 2). Returns a callable(prompt) -> str, or None.
#
# Backend is chosen by the KB_LLM env var:
#   KB_LLM=bedrock   -> Amazon Bedrock (needs boto3 + AWS creds)
#   KB_LLM=openai    -> OpenAI (needs openai + OPENAI_API_KEY)
#   KB_LLM=azure     -> Azure OpenAI (needs openai + AZURE_OPENAI_* vars)
#   KB_LLM=ollama    -> local Ollama (no key; needs Ollama running)
#   KB_LLM=auto      -> try openai, azure, bedrock, ollama in that order
#   (unset/none)     -> extractive mode, no LLM
#
# Any failure to initialize returns None and the agent falls back to extractive.
# ---------------------------------------------------------------------------

def get_llm():
    backend = os.environ.get("KB_LLM", "").lower().strip()
    if not backend or backend == "none":
        return None
    builders = {
        "bedrock": _bedrock_llm,
        "openai": _openai_llm,
        "azure": _azure_llm,
        "ollama": _ollama_llm,
    }
    if backend == "auto":
        for name in ("openai", "azure", "bedrock", "ollama"):
            fn = builders[name]()
            if fn:
                print(f"[kb] using LLM backend: {name}")
                return fn
        print("[kb] KB_LLM=auto but no backend available; extractive mode.")
        return None
    builder = builders.get(backend)
    if not builder:
        print(f"[kb] unknown KB_LLM='{backend}'; extractive mode.")
        return None
    return builder()


def _bedrock_llm():
    try:
        import boto3
    except ImportError:
        return None
    import json
    model_id = os.environ.get("KB_BEDROCK_MODEL",
                              "anthropic.claude-3-5-sonnet-20240620-v1:0")
    region = os.environ.get("AWS_REGION") or os.environ.get("AWS_DEFAULT_REGION") or "us-west-2"
    # Use the standard AWS_PROFILE convention; None -> boto3 default resolution.
    profile = os.environ.get("AWS_PROFILE") or None

    # Optional custom CA bundle (some networks sit behind a TLS-inspecting
    # proxy). Set AWS_CA_BUNDLE to your bundle path if needed; otherwise the
    # system trust store is used. Must be set BEFORE boto3 resolves the
    # SSO/OIDC token (a client `verify=` arg is too late for token exchange).
    ca_bundle = os.environ.get("AWS_CA_BUNDLE")
    try:
        session = boto3.Session(profile_name=profile) if profile else boto3.Session()
        client_kwargs = {"region_name": region}
        if ca_bundle:
            client_kwargs["verify"] = ca_bundle
        client = session.client("bedrock-runtime", **client_kwargs)
    except Exception as exc:  # noqa: BLE001
        print(f"[kb] Bedrock init failed ({exc}); extractive mode. "
              "Are your AWS credentials set (e.g. `aws sso login`)?")
        return None

    def call(prompt: str) -> str:
        body = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 700,
            "system": SYSTEM_PROMPT,
            "messages": [{"role": "user", "content": prompt}],
        }
        resp = client.invoke_model(modelId=model_id, body=json.dumps(body))
        payload = json.loads(resp["body"].read())
        return payload["content"][0]["text"]

    return call


def _openai_llm():
    if not os.environ.get("OPENAI_API_KEY"):
        return None
    try:
        from openai import OpenAI
    except ImportError:
        return None
    try:
        client = OpenAI()
    except Exception:
        return None
    model = os.environ.get("KB_OPENAI_MODEL", "gpt-4o-mini")

    def call(prompt: str) -> str:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        )
        return resp.choices[0].message.content

    return call


def _azure_llm():
    endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT")
    key = os.environ.get("AZURE_OPENAI_API_KEY")
    deployment = os.environ.get("AZURE_OPENAI_DEPLOYMENT")
    if not (endpoint and key and deployment):
        return None
    try:
        from openai import AzureOpenAI
    except ImportError:
        return None
    try:
        client = AzureOpenAI(
            azure_endpoint=endpoint,
            api_key=key,
            api_version=os.environ.get("AZURE_OPENAI_API_VERSION", "2024-06-01"),
        )
    except Exception:
        return None

    def call(prompt: str) -> str:
        resp = client.chat.completions.create(
            model=deployment,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        )
        return resp.choices[0].message.content

    return call


def _ollama_llm():
    """Local Ollama via its HTTP API — no API key, no external network."""
    import json
    import urllib.request
    host = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
    model = os.environ.get("KB_OLLAMA_MODEL", "llama3")

    def call(prompt: str) -> str:
        body = json.dumps({
            "model": model,
            "prompt": f"{SYSTEM_PROMPT}\n\n{prompt}",
            "stream": False,
        }).encode("utf-8")
        req = urllib.request.Request(
            f"{host}/api/generate", data=body,
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            return json.loads(resp.read())["response"]

    # Probe availability so KB_LLM=auto can skip a dead Ollama quickly.
    try:
        urllib.request.urlopen(f"{host}/api/tags", timeout=2).read()
    except Exception:
        return None
    return call


# ---------------------------------------------------------------------------
# Answering
# ---------------------------------------------------------------------------

def _source_to_url(source: str) -> str:
    """Map an indexed source path to the built site's relative URL.

    sync_docs.py copies content/* into docs/*, and mkdocs (use_directory_urls:
    false) builds each `.md` to a sibling `.html`. So:
      content/GenAI-Topics/rag/index.md   -> GenAI-Topics/rag/index.html
      docs/Course-Modules/module1.md      -> Course-Modules/module1.html
    The chatbot is served from the site root, so a root-relative URL works from
    any page.
    """
    path = source
    for prefix in ("content/", "docs/"):
        if path.startswith(prefix):
            path = path[len(prefix):]
            break
    if path.endswith(".md"):
        path = path[:-3] + ".html"
    return "/" + path


def _format_context(hits) -> str:
    blocks = []
    for i, (score, c) in enumerate(hits, 1):
        blocks.append(
            f"[{i}] Page: {c['page']} > {c['title']}  (source: {c['source']})\n"
            f"{c['text']}"
        )
    return "\n\n".join(blocks)


SUGGESTED_QUESTIONS = (
    "- What is RAG, and how does it work?\n"
    "- How do I build my first agent?\n"
    "- Prompt engineering best practices\n"
    "- How do I set up a vector database?\n"
    "- What is Snowflake Cortex?\n"
    "- MCP vs A2A"
)


def _smalltalk(question: str) -> str | None:
    """Friendly canned replies for greetings/small talk so the chatbot doesn't
    dead-end with 'I don't have anything on that' for a simple 'hi'."""
    q = question.strip().lower().rstrip("!?.")
    greetings = {"hi", "hello", "hey", "yo", "hiya", "hey there", "good morning",
                 "good afternoon", "good evening", "howdy"}
    thanks = {"thanks", "thank you", "thx", "ty", "cheers", "appreciate it"}
    helpish = {"help", "what can you do", "how do you work", "what do you know",
               "who are you", "what is this"}
    if q in greetings:
        return ("Hi! 👋 I'm your study assistant for this GenAI & data knowledge "
                "base. Ask me about a topic and I'll answer from the site with "
                "sources. Try:\n\n" + SUGGESTED_QUESTIONS)
    if q in thanks:
        return "You're welcome! Ask me anything else about the material."
    if q in helpish:
        return ("I answer questions from this site's GenAI, Agentic AI, and data "
                "content — with citations. Use the **area** dropdown to focus on "
                "one topic. Try:\n\n" + SUGGESTED_QUESTIONS)
    return None


def answer(question: str, area: str | None = None, k: int = 4,
           index=None) -> Answer:
    # Greetings / small talk: reply warmly instead of searching the KB.
    chat = _smalltalk(question)
    if chat is not None:
        return Answer(text=chat, citations=[], area=area or "all", used_llm=False)

    index = index or load_index()
    hits = search(index, question, area=area, k=k)

    if not hits:
        scope = f" in area '{area}'" if area and area != "all" else ""
        return Answer(
            text=(f"I don't have anything on that{scope} in the knowledge base "
                  f"yet. Here are some questions I *can* help with:\n\n"
                  f"{SUGGESTED_QUESTIONS}"),
            citations=[], area=area or "all", used_llm=False,
        )

    citations = []
    seen_labels = set()
    for _s, c in hits:
        label = f"{c['page']} > {c['title']}"
        if label in seen_labels:
            continue
        seen_labels.add(label)
        citations.append({"label": label, "url": _source_to_url(c["source"])})

    llm = get_llm()
    if llm:
        context = _format_context(hits)
        prompt = (
            f"Context from the knowledge base:\n\n{context}\n\n"
            f"Question: {question}\n\n"
            "Answer using only the context above. Cite the [n] sources you used."
        )
        try:
            text = llm(prompt)
            return Answer(text=text, citations=citations,
                          area=area or "all", used_llm=True)
        except Exception as exc:  # noqa: BLE001
            print(f"[kb] LLM call failed ({exc}); using extractive answer.")

    # Extractive fallback (no LLM): assemble a clean, organized answer from the
    # best-matching PAGE rather than returning a single small chunk. Pages here
    # are split into heading-based sections at index time, so the best hit is
    # often just a short page intro. To give a step-by-step feel, we gather that
    # page's sections in document order and lay them out with their headings as
    # bold sub-steps. This reads far better than one stray paragraph.
    #
    # Skip empty/tiny hits (e.g. a section that was almost entirely a diagram
    # before its code fences were stripped at index time).
    usable = [(s, c) for (s, c) in hits if len(c["text"].split()) >= 8]
    if not usable:
        usable = hits  # nothing substantial; fall back to whatever we have

    text = _build_page_answer(usable[0][1], index)
    return Answer(text=text, citations=citations, area=area or "all", used_llm=False)


def _build_page_answer(top_chunk: dict, index) -> str:
    """Compose a readable, structured answer from the best-matching page.

    Pulls every section of the same source page (in original order) and formats
    each as **Heading** + body, so the reader gets the full walkthrough instead
    of a single stray paragraph. Falls back to the single chunk if the page
    can't be reassembled.
    """
    source = top_chunk.get("source")
    page = top_chunk.get("page", "")

    # All chunks from the same source page, kept in index (document) order.
    same_page = [c for c in index["chunks"]
                 if c.get("source") == source and len(c["text"].split()) >= 4]

    if not same_page:
        body = top_chunk["text"].strip()
        return body[:1400].rsplit(" ", 1)[0] + " ..." if len(body) > 1400 else body

    parts: list[str] = []
    total = 0
    BUDGET = 2600  # keep the chat answer readable, not a wall of text

    for c in same_page:
        seg = c["text"].strip()
        if not seg:
            continue
        heading = (c.get("title") or "").strip()
        # Don't repeat the page title as a section heading; it's the intro.
        if heading and heading.lower() != page.lower():
            block = f"**{heading}**\n{seg}"
        else:
            block = seg
        # Trim any single oversized section.
        if len(block) > 1000:
            block = block[:1000].rsplit(" ", 1)[0] + " ..."
        parts.append(block)
        total += len(block)
        if total >= BUDGET:
            parts.append("_… see the full page for the rest._")
            break

    header = f"Here's what the knowledge base has on **{page}**:\n" if page else ""
    return header + "\n\n".join(parts)
