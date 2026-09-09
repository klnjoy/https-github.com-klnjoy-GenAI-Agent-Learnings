"""
Copy the heavy module files (PDFs, rendered notebooks, diagrams) into the built
site/ INCREMENTALLY — only files that are new or changed size.

mkdocs is configured to EXCLUDE Course-Modules/files/ from its build (see
exclude_docs in mkdocs.yml), so `mkdocs build` stays fast (markdown only). This
script tops up the built site with the large assets without re-copying the
~470 MB every time.

Run order:
    python sync_docs.py
    python -m mkdocs build --clean
    python finalize_site.py
"""

from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "docs" / "Course-Modules" / "files"
DST = ROOT / "site" / "Course-Modules" / "files"


def main() -> None:
    if not SRC.exists():
        print(f"No module files to copy (missing {SRC}).")
        return
    DST.mkdir(parents=True, exist_ok=True)
    copied = skipped = 0
    for src in SRC.rglob("*"):
        if src.is_dir():
            continue
        rel = src.relative_to(SRC)
        dst = DST / rel
        try:
            if dst.exists() and dst.stat().st_size == src.stat().st_size:
                skipped += 1
                continue
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
            copied += 1
        except OSError as exc:
            print(f"WARNING: could not copy {rel}: {exc}")
    print(f"Site files synced: {copied} copied, {skipped} unchanged (skipped).")


if __name__ == "__main__":
    main()
