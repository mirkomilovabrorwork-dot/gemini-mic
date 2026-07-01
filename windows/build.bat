@echo off
setlocal

cd /d "%~dp0"

echo === Creating virtual environment ===
if not exist venv (
    python -m venv venv
)

call venv\Scripts\activate.bat

echo === Installing dependencies ===
pip install --upgrade pip
pip install -r requirements.txt
pip install pyinstaller

echo === Generating icon.ico ===
python generate_icon.py

echo === Building GeminiMic.exe ===
pyinstaller --onefile --noconsole --name GeminiMic --icon icon.ico gemini_mic.py

echo.
echo Build complete. Output: dist\GeminiMic.exe
endlocal
