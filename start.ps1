# Serve the built site over HTTP so Mermaid diagrams, search, and links all work.
# (Opening index.html via file:// breaks Mermaid — always use this instead.)
#
# Usage:  right-click > Run with PowerShell   (or)   .\start.ps1

$ErrorActionPreference = "Stop"
$site = Join-Path $PSScriptRoot "site"

if (-not (Test-Path (Join-Path $site "index.html"))) {
    Write-Host "site/ not built yet. Building now..." -ForegroundColor Yellow
    python sync_docs.py
    python -m mkdocs build --clean
    python finalize_site.py
}

$port = 8080
Write-Host "Serving the GenAI Knowledge Base at http://localhost:$port" -ForegroundColor Green
Write-Host "Press Ctrl+C to stop." -ForegroundColor DarkGray
Start-Process "http://localhost:$port"
Set-Location $site
python -m http.server $port
