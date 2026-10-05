@echo off
setlocal
cd /d "%~dp0"

echo Starting Fantasy Lineup Optimizer...

where py >nul 2>nul
if %ERRORLEVEL%==0 (
  py -3 launch.py
  goto :end
)

where python >nul 2>nul
if %ERRORLEVEL%==0 (
  python launch.py
  goto :end
)

where python3 >nul 2>nul
if %ERRORLEVEL%==0 (
  python3 launch.py
  goto :end
)

echo.
echo ERROR: Python 3.9+ was not found.
echo Install Python from https://www.python.org/downloads/ then try again.
echo Make sure "Add python.exe to PATH" is checked during install.
echo.
pause
exit /b 1

:end
if errorlevel 1 pause
endlocal
