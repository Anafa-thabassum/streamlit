@echo off
cd /d "%~dp0"
if not exist .venv\Scripts\streamlit.exe (
  echo First run: follow the installation steps in README.md
  exit /b 1
)
.venv\Scripts\streamlit.exe run app.py

