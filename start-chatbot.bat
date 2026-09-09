@echo off
REM One-click: start the agent backend + the site, then open the browser.
REM The floating "Ask" chatbot on the site will talk to the backend.
cd /d "%~dp0"

REM Build the site if it isn't there yet.
if not exist "site\index.html" (
  echo Building the site first...
  python sync_docs.py
  python -m mkdocs build --clean
  python finalize_site.py
)

REM --- 1. Agent backend (FastAPI) in its own window, on port 8000 ---
REM Set KB_LLM=bedrock here to get synthesized answers (needs aws sso login).
echo Starting the agent backend on http://localhost:8000 ...
start "KB Agent (backend)" cmd /k "cd /d "%~dp0agent" && uvicorn serve:app --port 8000"

REM Give the backend a moment to boot.
timeout /t 3 /nobreak >nul

REM --- 2. Site server on port 8080 in this window ---
echo Opening the site at http://localhost:8080 ...
start "" http://localhost:8080
cd site
python -m http.server 8080
