@echo off
REM Rebuild everything after you change content, then reindex the agent.
cd /d "%~dp0"
echo [1/4] Syncing content...
python sync_docs.py
echo [2/4] Building site...
python -m mkdocs build --clean
echo [3/4] Copying module files...
python finalize_site.py
echo [4/4] Reindexing agent...
python agent\ask.py --reindex
echo.
echo Done. Run start.bat to view at http://localhost:8080
pause
