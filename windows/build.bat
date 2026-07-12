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
pyinstaller --onefile --noconsole --name GeminiMic --icon icon.ico ^
    --collect-all sounddevice --collect-all comtypes --collect-all uiautomation ^
    --hidden-import pystray._win32 ^
    --hidden-import pynput.keyboard._win32 --hidden-import pynput.mouse._win32 ^
    --noconfirm gemini_mic.py

echo.
echo Build complete. Output: dist\GeminiMic.exe
endlocal
