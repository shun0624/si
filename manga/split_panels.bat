@echo off
rem Drag and drop manga page images onto this file.
setlocal
set "HERE=%~dp0"
set "COMFY="
if exist "%HERE%comfyui_location.txt" set /p COMFY=<"%HERE%comfyui_location.txt"
set "PY=%COMFY%\python_embeded\python.exe"
if not exist "%PY%" set "PY=python"
"%PY%" -s "%HERE%scripts\split_panels.py" --comfy "%COMFY%" %*
pause
