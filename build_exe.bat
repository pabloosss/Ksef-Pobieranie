@echo off
cd /d "%~dp0"

echo =====================================
echo KSeF - build EXE
echo =====================================

color 0A >nul 2>nul

python --version >nul 2>nul
if errorlevel 1 (
    py --version >nul 2>nul
    if errorlevel 1 (
        echo [BLAD] Python nie jest zainstalowany albo nie ma go w PATH.
        pause
        exit /b 1
    ) else (
        set PY_CMD=py
    )
) else (
    set PY_CMD=python
)

%PY_CMD% -m pip install --upgrade pip
if errorlevel 1 goto :err

%PY_CMD% -m pip install -r requirements.txt
if errorlevel 1 goto :err

if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

%PY_CMD% -m PyInstaller ^
  --noconfirm ^
  --onefile ^
  --windowed ^
  --name Ksef-Pobieranie ^
  ksef_app_selenium_edge_fix.py
if errorlevel 1 goto :err

echo.
echo [OK] Gotowe.
echo FINALNY PROGRAM jest tutaj:
echo %cd%\dist\Ksef-Pobieranie.exe
echo.
echo Ten plik BAT tylko buduje EXE.
echo Teraz otworze folder dist i uruchomie gotowy program.
echo.

if exist "%cd%\dist\Ksef-Pobieranie.exe" (
    start "" explorer "%cd%\dist"
    start "" "%cd%\dist\Ksef-Pobieranie.exe"
) else (
    echo [BLAD] Nie znaleziono gotowego EXE w folderze dist.
)

pause
exit /b 0

:err
echo.
echo [BLAD] Build EXE nie powiodl sie.
pause
exit /b 1
