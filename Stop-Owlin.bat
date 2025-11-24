@echo off
title OWLIN - Stop Services
echo ?? Stopping Owlin backend (python) and frontend (node) processes...
taskkill /IM python.exe /F >nul 2>&1
taskkill /IM node.exe /F >nul 2>&1
echo ? All Owlin processes stopped.
pause
