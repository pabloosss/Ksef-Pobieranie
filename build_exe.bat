@echo off
setlocal
cd /d "%~dp0"

echo =====================================
echo KSeF - kompilacja stabilnej wersji EXE
echo =====================================

python --version >nul 2>nul
if errorlevel 1 (
    py --version >nul 2>nul
    if errorlevel 1 (
        echo [BLAD] Brak Pythona w PATH.
        pause
        exit /b 1
    ) else (
        set "PY_CMD=py"
    )
) else (
    set "PY_CMD=python"
)

%PY_CMD% -m pip install -r requirements.txt
if errorlevel 1 goto :err

echo.
echo [INFO] Kontrola bibliotek Edge / Selenium...
%PY_CMD% -c "from selenium.webdriver.edge.webdriver import WebDriver; import ksef_stable; print('[OK] Importy dzialaja')"
if errorlevel 1 goto :err

echo.
echo [INFO] Uruchamiam testy regresji...
%PY_CMD% -m unittest discover -s tests -p "test_*.py" -v
if errorlevel 1 goto :err

if exist dist\Ksef-Pobieranie.exe del /f /q dist\Ksef-Pobieranie.exe

%PY_CMD% -m PyInstaller --noconfirm --clean Ksef-Pobieranie.spec
if errorlevel 1 goto :err
if not exist "dist\Ksef-Pobieranie.exe" goto :err

echo [INFO] Sprawdzam zaleznosci wewnatrz EXE...
powershell -NoProfile -Command "$p = Start-Process -FilePath '%cd%\dist\Ksef-Pobieranie.exe' -ArgumentList '--self-test' -Wait -PassThru; if ($p.ExitCode -ne 0) { exit 1 }"
if errorlevel 1 (
    if exist ksef_selftest_error.txt type ksef_selftest_error.txt
    goto :err
)

echo.
echo [OK] Kompilacja zakonczona poprawnie.
echo %cd%\dist\Ksef-Pobieranie.exe
start "" explorer "%cd%\dist"
pause
exit /b 0

:err
echo.
echo [BLAD] Zatrzymano kompilacje - sprawdz komunikat powyzej.
echo Nie uruchamiaj starszego EXE.
pause
exit /b 1
