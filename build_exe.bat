@echo off
setlocal
cd /d "%~dp0"
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist *.spec del /q *.spec
pyinstaller --clean --noconfirm --onedir --name ConversorHeicJpgJair convert_heic_to_jpg.py
endlocal
