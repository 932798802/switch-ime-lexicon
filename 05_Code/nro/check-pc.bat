@echo off
rem ---------------------------------------------------------------------------
rem PC-side checks that do NOT need devkitPro (ASCII only - keep it ASCII):
rem   1) syntax-check source/main.cpp against a minimal libnx stub
rem   2) build and run the NJDC validator regression on real dictionaries
rem ---------------------------------------------------------------------------
setlocal
cd /d "%~dp0"

set "GXX=g++"
where g++ >nul 2>nul
if errorlevel 1 (
    if exist "C:\Qt\Tools\mingw1310_64\bin\g++.exe" (
        set "GXX=C:\Qt\Tools\mingw1310_64\bin\g++.exe"
    ) else (
        echo [ERROR] no g++ found. Install MinGW-w64 or MSYS2, or edit this script.
        exit /b 1
    )
)
echo Using compiler: %GXX%
echo.

echo [1/2] Syntax check: source\main.cpp
"%GXX%" -fsyntax-only -std=gnu++20 -Wall -Wextra -Wno-unused-parameter -I tools\stub source\main.cpp
if errorlevel 1 (
    echo [FAIL] syntax errors in source\main.cpp
    exit /b 1
)
echo [OK]   source\main.cpp parses cleanly.
echo.

echo [2/2] Build + run NJDC validator regression
"%GXX%" -O2 -Wall -o tools\host_test.exe tools\host_test.cpp
if errorlevel 1 (
    echo [FAIL] could not build tools\host_test.cpp
    exit /b 1
)

set "ORIG=..\..\01_Inputs\firmware\dat0805\files\Iwnn\ZH\CN\pinyin\GB18030"
if not exist "%ORIG%\njubase3.a" (
    echo [SKIP] original dictionaries not found at %ORIG%
    echo        Pass your own paths to tools\host_test.exe instead.
    exit /b 0
)

tools\host_test.exe ^
    ..\..\04_Outputs\njubase3.a ^
    ..\..\04_Outputs\njubase1.a ^
    ..\..\04_Outputs\njubase2.a ^
    "%ORIG%\njtan.a" ^
    "%ORIG%\njubase1.a" ^
    "%ORIG%\njubase2.a" ^
    "%ORIG%\njubase3.a" ^
    "%ORIG%\njcode.a" ^
    "%ORIG%\njexyomi.a"
if errorlevel 1 (
    echo [FAIL] validator regression failed
    exit /b 1
)

endlocal
