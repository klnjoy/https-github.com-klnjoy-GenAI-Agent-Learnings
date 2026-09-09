@echo off
REM Double-click to serve the site over HTTP (so diagrams/search work) and open it.
cd /d "%~dp0"
if not exist "site\index.html" (
  echo Building the site first...
  python sync_docs.py
  python -m mkdocs build --clean
  python finalize_site.py
)
echo Serving at http://localhost:8080  (close this window to stop)
start "" http://localhost:8080
cd site
python -m http.server 8080
