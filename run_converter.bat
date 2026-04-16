@echo off
setlocal
cd /d "%~dp0"
if exist "%~dp0dist\ConversorHeicJpgJair.exe" (
    "%~dp0dist\ConversorHeicJpgJair.exe" --pause-on-finish
) else if exist "%~dp0dist\ConversorHeicJpgJair\ConversorHeicJpgJair.exe" (
    "%~dp0dist\ConversorHeicJpgJair\ConversorHeicJpgJair.exe" --pause-on-finish
) else (
    python "%~dp0convert_heic_to_jpg.py" --pause-on-finish
)
endlocal
