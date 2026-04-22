# KSeF Pobieranie

Program w Pythonie do pobierania faktur z KSeF przez GUI.

## Co robi
- otwiera KSeF w Microsoft Edge
- pozwala sprawdzić ilość FV na liście
- pobiera FV partiami
- może pomijać już wcześniej pobrane pozycje
- zapisuje pliki do folderu `pobrane_fv`
- zapisuje rejestr pobrań w `rejestr_pobran.sqlite`

## Wymagania
- Windows
- Microsoft Edge
- Python 3.10+

## Uruchomienie z Pythona
W katalogu projektu uruchom:

```bat
python -m pip install -r requirements.txt
python ksef_app_selenium_edge_fix.py
```

Jeżeli komenda `python` nie działa, użyj:

```bat
py -m pip install -r requirements.txt
py ksef_app_selenium_edge_fix.py
```

## Jak zrobić EXE
Najprościej uruchom:

```bat
build_exe.bat
```

Po buildzie plik będzie tutaj:

```text
dist\Ksef-Pobieranie.exe
```

## Jak używać
1. Kliknij `Start / Otwórz KSeF`
2. Zaloguj się ręcznie
3. Ustaw filtry w KSeF
4. Kliknij `Sprawdź ilość FV`
5. Wpisz ile FV chcesz pobrać
6. Kliknij `Pobierz`

## Ważne
- program działa na aktualnie widocznej liście w KSeF
- Edge musi być zainstalowany
- na innym komputerze najwygodniej odpalać gotowy EXE z folderu `dist`
