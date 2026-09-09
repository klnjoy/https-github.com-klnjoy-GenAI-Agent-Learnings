"""
CLI for the knowledge-base agent.

Usage:
    python ask.py --reindex                 # (re)build the index
    python ask.py "What is Cortex Analyst?"  # one-shot question (all areas)
    python ask.py --area snowflake "..."     # filter to an area (your 'agents')
    python ask.py                            # interactive chat loop

Areas: snowflake, databricks, dbt, aws, rag, mcp, langchain, langgraph,
       prompt-engineering, agentcore, graph-db, interview, general, all
"""

from __future__ import annotations

import argparse
import sys

# Force UTF-8 output so arrows/emoji in content don't crash the Windows console.
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

from kb_index import build_index, save_index, load_index, INDEX_PATH
from kb_agent import answer


def _print_answer(ans) -> None:
    tag = "LLM" if ans.used_llm else "from KB"
    print(f"\n[{ans.area}] ({tag})\n")
    print(ans.text.strip())
    if ans.citations:
        print("\nSources:")
        for c in ans.citations:
            label = c["label"] if isinstance(c, dict) else c
            print(f"  - {label}")
    print()


def _ensure_index():
    if not INDEX_PATH.exists():
        print("No index found — building it now...")
        save_index(build_index())


def main() -> None:
    ap = argparse.ArgumentParser(description="Ask the GenAI knowledge base.")
    ap.add_argument("question", nargs="*", help="Your question")
    ap.add_argument("--area", default="all", help="Restrict to an area")
    ap.add_argument("--k", type=int, default=4, help="Chunks to retrieve")
    ap.add_argument("--reindex", action="store_true", help="Rebuild the index")
    args = ap.parse_args()

    if args.reindex:
        save_index(build_index())
        idx = load_index()
        print(f"Reindexed {len(idx['chunks'])} chunks.")
        if not args.question:
            return

    _ensure_index()
    index = load_index()

    if args.question:
        q = " ".join(args.question)
        _print_answer(answer(q, area=args.area, k=args.k, index=index))
        return

    # Interactive loop
    area = args.area
    print("KB agent ready. Type a question, '/area <name>' to filter, or '/quit'.")
    print(f"Current area: {area}\n")
    while True:
        try:
            q = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if not q:
            continue
        if q in ("/quit", "/exit", "quit", "exit"):
            break
        if q.startswith("/area"):
            parts = q.split(maxsplit=1)
            area = parts[1].strip() if len(parts) > 1 else "all"
            print(f"(area set to: {area})")
            continue
        _print_answer(answer(q, area=area, k=args.k, index=index))


if __name__ == "__main__":
    main()
