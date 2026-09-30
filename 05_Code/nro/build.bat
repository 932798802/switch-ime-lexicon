@echo off
rem ---------------------------------------------------------------------------
rem HexDict .nro build script (ASCII only on purpose - keep this file ASCII)
rem
rem Requires: devkitPro with the libnx package.
rem           https://devkitpro.org/wiki/Getting_Started
rem           Default install path is C:/devkitPro
rem ---------------------------------------------------------------------------
setlocal
cd /d "%~dp0"

rem NOTE: this project installs devkitPro from the raw pacman packages
rem (see ../tools/install_devkitpro.py), which land under <root>/opt/devkitpro.
rem Override with DEVKITPRO if yours is elsewhere.
if "%DEVKITPRO%"=="" set "DEVKITPRO=C:/devkitPro/opt/devkitpro"

if not exist "%DEVKITPRO%\libnx\switch_rules" (
    echo [ERROR] devkitPro / libnx not found at "%DEVKITPRO%"
    echo         Install devkitPro with the libnx package, or set DEVKITPRO.
    exit /b 1
)

set "DEVKITA64=%DEVKITPRO%/devkitA64"
set "PATH=%DEVKITPRO%/tools/bin;%DEVKITA64%/bin;%PATH%"

echo [1/3] Embedding dictionaries ...
python tools\gen_embed.py
if errorlevel 1 (
    echo [ERROR] gen_embed.py failed. Is Python 3 on PATH?
    exit /b 1
)

echo.
echo [2/3] Building ...

rem find a make: prefer plain make, fall back to mingw32-make
set "MAKE_EXE=make"
where make >nul 2>nul
if errorlevel 1 (
    if exist "C:\Qt\Tools\mingw1310_64\bin\mingw32-make.exe" (
        set "MAKE_EXE=C:\Qt\Tools\mingw1310_64\bin\mingw32-make.exe"
    ) else (
        echo [ERROR] no make found. Expected make or mingw32-make on PATH.
        exit /b 1
    )
)
echo Using make: %MAKE_EXE%
"%MAKE_EXE%"
if errorlevel 1 (
    echo [ERROR] build failed.
    exit /b 1
)

echo.
echo [3/3] OK
if exist HexDict.nro (
    echo Output: %~dp0HexDict.nro
    for %%F in (HexDict.nro) do echo Size  : %%~zF bytes
    echo Copy it to the root of your SD card ^(or to /switch/^) and run it from hbmenu.
) else (
    echo [ERROR] HexDict.nro was not produced.
    exit /b 1
)

endlocal
