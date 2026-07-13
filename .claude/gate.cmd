@echo off
REM Done-gate for gemini-mic (Android is cloud-CI-built; only Python desktop is checkable locally)
REM 1) Syntax-check all Python desktop sources
python -m py_compile windows\gemini_mic.py windows\generate_icon.py mac\gemini_mic_mac.py
if errorlevel 1 exit /b 1
REM 2) Run the Windows edition self-test (prompt/clean/format logic) via the project venv
windows\.venv\Scripts\python.exe windows\gemini_mic.py --selftest
if errorlevel 1 exit /b 1
exit /b 0
