@echo off
cd /d "%~dp0"
echo Starting SyllabusPilot...
.\.venv\Scripts\streamlit.exe run app.py
pause
