@echo off
setlocal enabledelayedexpansion

REM ----- Setup & logging -----
set "LOG=%PREFIX%\movinglines-postlink.log"
if not exist "%PREFIX%\" mkdir "%PREFIX%\" >NUL 2>&1

REM Ensure System32 is on PATH so tools like chcp are available if invoked
if not defined SystemRoot set "SystemRoot=%WINDIR%"
if exist "%SystemRoot%\System32" set "PATH=%SystemRoot%\System32;%PATH%"
if exist "%SystemRoot%\System32\chcp.com" chcp 65001 >NUL

echo == movinglines post-link: %DATE% %TIME% ==>> "%LOG%"
echo PREFIX=%PREFIX%>> "%LOG%"

REM ----- Make sure Python/pip exist in the target env -----
if not exist "%PREFIX%\python.exe" (
  echo No python at %PREFIX%\python.exe; skipping pip install.>> "%LOG%"
  goto end
)

set "PIP_DISABLE_PIP_VERSION_CHECK=1"
set "PYTHONUTF8=1"

"%PREFIX%\python.exe" -m pip --version >> "%LOG%" 2>&1
if errorlevel 1 (
  "%PREFIX%\python.exe" -m ensurepip --upgrade >> "%LOG%" 2>&1
)

REM ----- Install PyPI-only dependency WITHOUT deps (avoid resolver conflicts) -----
echo Installing flightplandb via pip --no-deps ...>> "%LOG%"
"%PREFIX%\python.exe" -m pip install --no-input --disable-pip-version-check --no-warn-script-location --no-deps flightplandb >> "%LOG%" 2>&1
if errorlevel 1 (
  echo WARNING: pip install flightplandb failed; leaving package installed.>> "%LOG%"
  echo You can run manually: "%PREFIX%\python.exe" -m pip install --no-deps flightplandb>> "%LOG%"
)

:end
echo Post-link completed.>> "%LOG%"

endlocal
exit /b 0
