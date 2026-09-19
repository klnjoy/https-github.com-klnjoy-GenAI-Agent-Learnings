"""
Build docs/assets/interview_questions.json for the interactive Practice mode.

Parses the interview Q&A markdown in personal-docs/ and extracts:
  - `??? question "PROMPT"` collapsibles, using the following indented block as
    the model answer (code fences and admonition markers stripped).

Each question is tagged with a topic (from the filename) and a track, so the
Practice page can offer role-based sessions. Output is a static JSON the
browser loads — no backend needed.

Run:  python build_practice_questions.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "personal-docs"
OUT = ROOT / "docs" / "assets" / "interview_questions.json"

# filename stem -> (topic label, [tracks])
TOPICS: dict[str, tuple[str, list[str]]] = {
    "SQL_Interview_QA": ("SQL", ["data"]),
    "DataEngineering_Interview_QA": ("Data Engineering", ["data"]),
    "Snowflake_Interview_QA": ("Snowflake", ["data"]),
    "Databricks_Interview_QA": ("Databricks", ["data"]),
    "dbt_Interview_QA": ("dbt", ["data"]),
    "Python_Interview_QA": ("Python", ["data", "ai", "fde"]),
    "AWS_Interview_QA": ("AWS", ["data", "ai"]),
    "DevOps_Interview_QA": ("DevOps", ["data"]),
    "AI_Engineer_Interview_QA": ("AI Engineer", ["ai"]),
    "Agents_Interview_QA": ("Agents", ["ai"]),
    "LangChain_LangGraph_Interview_QA": ("LangChain/LangGraph", ["ai"]),
    "MCP_Interview_QA": ("MCP", ["ai"]),
    "GenAI_Interview_QA": ("GenAI", ["ai"]),
    "Behavioral_STAR_Interview_QA": ("Behavioral", ["data", "ai", "fde", "lead"]),
}

Q_RE = re.compile(r'^\?\?\?\s+question\s+"(.+?)"\s*$')


def clean(text: str) -> str:
    # collapse whitespace, drop leftover markdown emphasis markers lightly
    text = re.sub(r"\s+", " ", text).strip()
    return text


def extract(md_path: Path) -> list[dict]:
    lines = md_path.read_text(encoding="utf-8", errors="replace").splitlines()
    out: list[dict] = []
    i = 0
    n = len(lines)
    while i < n:
        m = Q_RE.match(lines[i].strip())
        if not m:
            i += 1
            continue
        prompt = m.group(1)
        i += 1
        # Collect the indented answer block (lines indented under the admonition).
        body: list[str] = []
        while i < n:
            ln = lines[i]
            if ln.strip() == "":
                body.append("")
                i += 1
                continue
            # indented content belongs to the admonition (>= 4 spaces)
            if ln.startswith("    "):
                body.append(ln[4:])
                i += 1
            else:
                break
        # Build the model answer: drop code fences, keep prose + inline.
        text = "\n".join(body)
        text = re.sub(r"```[\s\S]*?```", "", text)   # remove code blocks
        text = clean(text)
        if prompt and text:
            out.append({"q": prompt, "a": text})
    return out


def main() -> None:
    questions: list[dict] = []
    per_topic: dict[str, int] = {}
    for stem, (topic, tracks) in TOPICS.items():
        path = SRC / f"{stem}.md"
        if not path.exists():
            print(f"skip (missing): {stem}")
            continue
        items = extract(path)
        for it in items:
            it["topic"] = topic
            it["tracks"] = tracks
            it["source"] = stem
            questions.append(it)
        per_topic[topic] = len(items)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_by": "build_practice_questions.py",
        "count": len(questions),
        "topics": sorted({q["topic"] for q in questions}),
        "questions": questions,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"Wrote {len(questions)} questions to {OUT}")
    for t, c in sorted(per_topic.items()):
        print(f"  {t:20} {c}")


if __name__ == "__main__":
    main()
