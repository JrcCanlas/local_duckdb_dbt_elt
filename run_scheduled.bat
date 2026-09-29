@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

set "LOG_DIR=%~dp0logs"
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"
set "LOG_FILE=%LOG_DIR%\scheduler.log"

echo [ %date% %time% ] ERP pipeline started
echo [ %date% %time% ] ERP pipeline started >> "%LOG_FILE%"

if exist "%~dp0elt_runner.exe" (
    echo Running packaged ERP pipeline...
    powershell -NoProfile -Command "& { & '%~dp0elt_runner.exe' --pipeline erp 2>&1 | Tee-Object -FilePath '%LOG_FILE%' }"
    set "EXITCODE=%ERRORLEVEL%"
    echo [ %date% %time% ] ERP pipeline finished with exit code=%EXITCODE%
    echo [ %date% %time% ] ERP pipeline finished with exit code=%EXITCODE% >> "%LOG_FILE%"
    exit /b %EXITCODE%
)

if exist "%~dp0\.venv\Scripts\python.exe" (
    echo Running source ERP pipeline...
    powershell -NoProfile -Command "& { & '%~dp0\.venv\Scripts\python.exe' '%~dp0main.py' --pipeline erp 2>&1 | Tee-Object -FilePath '%LOG_FILE%' }"
    set "EXITCODE=%ERRORLEVEL%"
    echo [ %date% %time% ] ERP pipeline finished with exit code=%EXITCODE%
    echo [ %date% %time% ] ERP pipeline finished with exit code=%EXITCODE% >> "%LOG_FILE%"
    exit /b %EXITCODE%
)

echo ERROR: No runnable ERP entrypoint found.
echo Expected either: "%~dp0elt_runner.exe" or "%~dp0\.venv\Scripts\python.exe"
echo Please build the packaged client or restore the local venv.
echo ERROR: No runnable ERP entrypoint found. >> "%LOG_FILE%"
exit /b 1