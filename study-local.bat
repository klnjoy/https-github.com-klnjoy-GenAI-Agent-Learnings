@echo off
REM ============================================================
REM  study-local.bat  —  FULL local study site (one click)
REM
REM  Builds the COMPLETE site including the course modules
REM  (notebooks, PDFs, drawio, images all openable in the browser)
REM  and opens it at http://localhost:8080.
REM
REM  This is LOCAL ONLY. The course modules are the instructor's
REM  materials and are NOT published to the public GitHub site —
REM  they live only on your machine via the OneDrive source below.
REM ============================================================
cd /d "%~dp0"

REM --- Point at your local study-material source (OneDrive) ---
REM If your OneDrive path differs, edit the line below.
set "GENAI_SOURCE_ROOT=%USERPROFILE%\OneDrive - Portland General Electric Company\Personal\GENAI-AGENTICAI"

if not exist "%GENAI_SOURCE_ROOT%" (
  echo.
  echo  WARNING: study-material source not found at:
  echo    %GENAI_SOURCE_ROOT%
  echo  The site will still build, but without the course modules.
  echo  Edit GENAI_SOURCE_ROOT in this file to point at your folder.
  echo.
)

echo [1/3] Syncing content + modules (this reads the study material)...
python sync_docs.py
echo [2/3] Building the site...
python -m mkdocs build --clean
echo [3/3] Copying module files (PDFs / notebooks / diagrams)...
python finalize_site.py

echo.
echo  Full study site ready. Opening http://localhost:8080
echo  (Close this window to stop the server.)
start "" http://localhost:8080
cd site
python -m http.server 8080
