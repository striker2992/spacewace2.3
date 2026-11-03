@echo off
cd /d "%~dp0"
call venv\Scripts\activate.bat
python demo_publica.py
pause
