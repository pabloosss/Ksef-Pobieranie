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

set ICON_ARGS=
if exist grafika\ikona.ico (
    set ICON_ARGS=--icon grafika\ikona.ico
) else (
    if exist grafika\ikona.png (
        %PY_CMD% -m pip install pillow
        %PY_CMD% -c "from PIL import Image; img=Image.open('grafika/ikona.png').convert('RGBA'); img.save('grafika/ikona.ico', sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])"
        if exist grafika\ikona.ico set ICON_ARGS=--icon grafika\ikona.ico
    )
)

if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

%PY_CMD% -m PyInstaller ^
  --noconfirm ^
  --onefile ^
  --windowed ^
  --collect-submodules selenium ^
  --hidden-import selenium.webdriver.edge.webdriver ^
  --hidden-import selenium.webdriver.edge.service ^
  --hidden-import selenium.webdriver.edge.options ^
  --hidden-import selenium.webdriver.common.selenium_manager ^
  %ICON_ARGS% ^
  --name Ksef-Pobieranie ^
  ksef_app_selenium_edge_fix.py
if errorlevel 1 goto :err

if not exist dist\grafika mkdir dist\grafika

REM Grafiki są w osobnym folderze, żeby nie myliły się z programem.
if exist grafika\logo.png copy /Y grafika\logo.png dist\grafika\logo.png >nul
if exist grafika\ikona.png copy /Y grafika\ikona.png dist\grafika\ikona.png >nul
if exist grafika\ikona.ico copy /Y grafika\ikona.ico dist\grafika\ikona.ico >nul

echo.
echo [OK] Gotowe.
echo FINALNY PROGRAM jest tutaj:
echo %cd%\dist\Ksef-Pobieranie.exe
echo.
echo Grafiki sa schowane tutaj:
echo %cd%\dist\grafika
echo.

if exist "%cd%\dist\Ksef-Pobieranie.exe" (
    start "" explorer "%cd%\dist"
)

pause
exit /b 0

:err
echo.
echo [BLAD] Build EXE nie powiodl sie.
pause
exit /b 1
