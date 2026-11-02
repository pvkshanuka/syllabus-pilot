# Convenient runner script for SyllabusPilot
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

Write-Host "🎓 Starting SyllabusPilot..." -ForegroundColor Cyan
& "$ScriptDir\.venv\Scripts\streamlit.exe" run "$ScriptDir\app.py"
