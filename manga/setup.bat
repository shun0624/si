@echo off
rem Manga production set installer (ComfyUI + nodes + models + tools)
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1"
pause
