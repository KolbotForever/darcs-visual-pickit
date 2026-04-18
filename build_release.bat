@echo off
setlocal EnableExtensions

title Build Darc's Visual Pickit Folder Build

echo.
echo ==========================================
echo   Darc's Visual Pickit Folder Build Script
echo ==========================================
echo.

cd /d "%~dp0"

set "PYTHON_CMD="
set "SCRIPT_NAME="
set "EXE_NAME="
set "DIST_DIR="
set "ICON_FILE="
set "FONT_FILE="

echo Working folder:
echo %CD%
echo.

call :resolve_python
if errorlevel 1 (
    pause
    exit /b 1
)

call :load_release_metadata
if errorlevel 1 (
    pause
    exit /b 1
)

set "SCRIPT_NAME=%RELEASE_ENTRY_SCRIPT%"
set "EXE_NAME=%RELEASE_EXE_NAME%"
set "DIST_DIR=dist\%EXE_NAME%"
set "ICON_FILE=%RELEASE_ICON_FILE%"
set "FONT_FILE=%RELEASE_FONT_FILE%"

echo [1/7] Using Python:
echo %PYTHON_CMD%
echo.
echo Release metadata:
echo %RELEASE_APP_VERSION% ^| %RELEASE_APP_BUILD_DATE%
echo Entry script: %SCRIPT_NAME%
echo.

echo [2/7] Installing required build dependencies...
call %PYTHON_CMD% -m pip install pyinstaller customtkinter pillow
if errorlevel 1 (
    echo [ERROR] Failed to install required build dependencies.
    pause
    exit /b 1
)

echo [3/7] Checking required files...
if not exist "%SCRIPT_NAME%" (
    echo [ERROR] Missing script: %SCRIPT_NAME%
    pause
    exit /b 1
)
if not exist "%ICON_FILE%" (
    echo [ERROR] Missing icon file: %ICON_FILE%
    pause
    exit /b 1
)
if not exist "%FONT_FILE%" (
    echo [ERROR] Missing font file: %FONT_FILE%
    echo The app can fall back to Arial at runtime, but the packaged build expects this file.
    pause
    exit /b 1
)

echo [4/7] Running syntax preflight...
call %PYTHON_CMD% -m py_compile ^
    ".\release_metadata.py" ^
    ".\%SCRIPT_NAME%" ^
    ".\advanced_clause_ui.py" ^
    ".\compact_card_runtime.py" ^
    ".\compact_model_cache.py" ^
    ".\compact_ui_runtime.py" ^
    ".\editor_dialogs.py" ^
    ".\nip_parser.py" ^
    ".\paged_cache_runtime.py" ^
    ".\paged_core.py" ^
    ".\paged_validation.py" ^
    ".\profile_runtime.py" ^
    ".\rule_model_runtime.py" ^
    ".\runtime_controller.py" ^
    ".\runtime_mutations.py" ^
    ".\runtime_wiring.py" ^
    ".\sidebar_filters.py" ^
    ".\widget_cards.py"
if errorlevel 1 (
    echo [ERROR] Syntax preflight failed.
    pause
    exit /b 1
)

echo [5/7] Cleaning old build artifacts...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist "%EXE_NAME%.spec" del /f /q "%EXE_NAME%.spec"

echo [6/7] Building app folder...
call %PYTHON_CMD% -m PyInstaller ^
    --noconfirm ^
    --clean ^
    --onedir ^
    --windowed ^
    --collect-data customtkinter ^
    --icon="%ICON_FILE%" ^
    --add-data "%ICON_FILE%;." ^
    --add-data "%FONT_FILE%;." ^
    --name "%EXE_NAME%" ^
    "%SCRIPT_NAME%"
if errorlevel 1 (
    echo.
    echo [ERROR] Build failed.
    pause
    exit /b 1
)

if not exist "%DIST_DIR%\%EXE_NAME%.exe" (
    echo [ERROR] Build finished but expected output was not found:
    echo %CD%\%DIST_DIR%\%EXE_NAME%.exe
    pause
    exit /b 1
)

echo [7/7] Build complete.
echo.
echo ==========================================
echo App folder created at:
echo %CD%\%DIST_DIR%
echo Main EXE:
echo %CD%\%DIST_DIR%\%EXE_NAME%.exe
echo ==========================================
echo.

pause
exit /b 0

:resolve_python
for /f "delims=" %%P in ('dir /b /ad "%LocalAppData%\Programs\Python\Python*" 2^>nul ^| findstr /v /i /c:"-32" ^| sort /r') do (
    if exist "%LocalAppData%\Programs\Python\%%P\python.exe" (
        set "PYTHON_CMD="%LocalAppData%\Programs\Python\%%P\python.exe""
        goto :python_ready
    )
)

for /f "delims=" %%P in ('dir /b /ad "%LocalAppData%\Programs\Python\Python*" 2^>nul ^| sort /r') do (
    if exist "%LocalAppData%\Programs\Python\%%P\python.exe" (
        set "PYTHON_CMD="%LocalAppData%\Programs\Python\%%P\python.exe""
        goto :python_ready
    )
)

python -c "import sys" >nul 2>nul
if not errorlevel 1 (
    set "PYTHON_CMD=python"
    goto :python_ready
)

py -3.12 -c "import sys" >nul 2>nul
if not errorlevel 1 (
    set "PYTHON_CMD=py -3.12"
    goto :python_ready
)

py -3 -c "import sys" >nul 2>nul
if not errorlevel 1 (
    set "PYTHON_CMD=py -3"
    goto :python_ready
)

py -c "import sys" >nul 2>nul
if not errorlevel 1 (
    set "PYTHON_CMD=py"
    goto :python_ready
)

echo [ERROR] Could not find a usable Python interpreter.
echo Install Python 3 and make sure either:
echo   1. python.exe is on PATH, or
echo   2. py launcher works, or
echo   3. Python is installed under %%LocalAppData%%\Programs\Python
exit /b 1

:python_ready
exit /b 0

:load_release_metadata
if not exist ".\release_metadata.py" (
    echo [ERROR] Missing release metadata file: .\release_metadata.py
    exit /b 1
)

call %PYTHON_CMD% ".\release_metadata.py" env-cmd > ".\.release_metadata.cmd"
if errorlevel 1 (
    echo [ERROR] Could not export release metadata from release_metadata.py
    exit /b 1
)

call ".\.release_metadata.cmd"
if not defined RELEASE_ENTRY_SCRIPT (
    echo [ERROR] Could not load release metadata from release_metadata.py
    exit /b 1
)

call %PYTHON_CMD% ".\release_metadata.py" write-issinc ".\.version_auto.issinc"
if errorlevel 1 (
    echo [ERROR] Could not refresh .version_auto.issinc from release metadata.
    exit /b 1
)

call %PYTHON_CMD% ".\release_metadata.py" sync-release-notes ".\%RELEASE_NOTES_FILE%"
if errorlevel 1 (
    echo [ERROR] Could not sync the build date into %RELEASE_NOTES_FILE%.
    exit /b 1
)

del /f /q ".\.release_metadata.cmd" >nul 2>nul

exit /b 0
