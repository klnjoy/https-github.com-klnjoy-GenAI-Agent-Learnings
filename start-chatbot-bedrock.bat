@echo off
REM Same as start-chatbot.bat, but runs the agent with Amazon Bedrock so the
REM chatbot gives synthesized answers (not just retrieved passages).
REM
REM PREREQUISITES:
REM   1. Your AWS credentials must be available. If you use SSO:
REM        aws sso login --profile YOUR_PROFILE
REM   2. Set your profile/region below (or set them in your environment).
REM      Leave AWS_PROFILE unset to use boto3's default credential resolution.
cd /d "%~dp0"

REM ---- Configure these to match your AWS setup ----
set AWS_PROFILE=
set AWS_REGION=us-west-2

if not exist "site\index.html" (
  echo Building the site first...
  python sync_docs.py
  python -m mkdocs build --clean
  python finalize_site.py
)

echo Starting the agent backend WITH Bedrock on http://localhost:8000 ...
start "KB Agent (Bedrock)" cmd /k "cd /d "%~dp0agent" && set KB_LLM=bedrock&& set AWS_PROFILE=%AWS_PROFILE%&& set AWS_REGION=%AWS_REGION%&& uvicorn serve:app --port 8000"

timeout /t 3 /nobreak >nul

echo Opening the site at http://localhost:8080 ...
start "" http://localhost:8080
cd site
python -m http.server 8080
