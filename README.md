# GenAI Docs Site (MkDocs)

A [MkDocs](https://www.mkdocs.org/) site (Material theme) that gathers **all `.md` files**
from two locations and publishes them as one searchable website:

| Section in site      | Source folder |
|----------------------|---------------|
| `GENAI-AGENTICAI`    | Set via the `GENAI_SOURCE_ROOT` environment variable (defaults to `~/GENAI-AGENTICAI`) |
| `Personal-SourceCode`| `C:\Dev\SoureceCode\Personal` |

The source files are **not** edited. `sync_docs.py` copies them into `docs/` and
builds an auto-generated landing page (`docs/index.md`) with links to every document.

## Authoring your own notes (Technologies & GenAI Topics)

You write these pages by hand — they live in `content/` and are copied verbatim
into `docs/` on every sync (never overwritten by the auto-sync):

```
content/
  Technologies/        Snowflake, AWS, Databricks
  GenAI-Topics/        Prompt Engineering, RAG, LangChain, LangGraph,
                       MCP, Bedrock, AgentCore, Graph DB
```

To add content to an area, just edit or add `.md` files in the matching folder,
e.g. `content/Technologies/snowflake/warehouses.md`, then run
`python sync_docs.py`. New pages appear in the nav automatically. Set a nav icon
on a page with YAML front matter at the top:

```markdown
---
icon: material/snowflake
---
```

Course modules are auto-linked into the matching GenAI topic (e.g. MODULE5-RAG
shows up as a "Related course module" callout on the RAG page).

## Opening module files (PDFs, notebooks, diagrams)

`sync_docs.py` copies the openable files from each extracted module into
`docs/Course-Modules/files/<module>/` and links them on the module page:

- **PDFs** open inline in the browser.
- **Jupyter notebooks (.ipynb)** are converted to HTML (via `nbconvert`) and
  open as rendered pages. A few notebooks with incompatible metadata may fail
  to convert — they're still listed, just without a link.
- **.drawio** diagrams download (browsers can't render them natively).
- Word/PowerPoint files are listed for reference but not copied (to keep the
  site size down); open them from the source folder.

Because these files are copied in, the built `site/` is large (~470 MB). That's
expected. `use_directory_urls: false` is set so the file links resolve cleanly.

## One-time setup

Packages are already installed. If you ever need to reinstall (note the corporate
SSL trusted-host flags):

```powershell
python -m pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org -r requirements.txt
```

## Everyday use

Build the full static site (fast — heavy module files are copied separately and
incrementally, so `mkdocs build` only renders the markdown in a few seconds):

```powershell
python sync_docs.py            # prep docs/ from sources + authored content
python -m mkdocs build --clean # render markdown pages (fast; excludes big files)
python finalize_site.py        # incrementally copy module PDFs/notebooks into site/
```

Or as a one-liner:

```powershell
python sync_docs.py; python -m mkdocs build --clean; python finalize_site.py
```

For live editing, `python -m mkdocs serve` (http://127.0.0.1:8000) builds
in-memory instantly — best for iterating on content/CSS.

> **Why the 3 steps?** The course-module files (PDFs, rendered notebooks,
> diagrams ~470 MB) are excluded from the mkdocs build (`exclude_docs` in
> mkdocs.yml) and copied into `site/` by `finalize_site.py`, which skips files
> that are already there. This keeps builds fast and avoids re-copying 470 MB
> every time. The first `finalize_site.py` run copies everything; later runs are
> near-instant.

Re-run these any time you add or change markdown, then refresh the browser.

## Adding another source folder

Edit the `SOURCE_ROOTS` list near the top of `sync_docs.py`:

```python
SOURCE_ROOTS = [
    ("GENAI-AGENTICAI", Path(r"C:\...\GENAI-AGENTICAI")),
    ("Personal-SourceCode", Path(r"C:\Dev\SoureceCode\Personal")),
    ("My-New-Section", Path(r"C:\path\to\folder")),   # <- add here
]
```

## Notes

- `docs/` and `site/` are regenerated; treat them as build output.
- The nav is built automatically from the folder structure under `docs/`.
- Search, dark/light toggle, and code-copy buttons come from the Material theme.
