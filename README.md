# KSeF Pobieranie — EMERLOG

Aplikacja Windows (Python / Selenium / Microsoft Edge) do pobierania faktur PDF z listy KSeF po ręcznym zalogowaniu.

**Wersja stabilizacyjna:** `ksef_stable.py` (gałąź `hardening/ksef-reliability-20261117`). Dotychczasowy `ksef_app_selenium_edge_fix.py` pozostaje zachowany jako silnik GUI i przeglądarki.

## Uruchomienie

Zainstaluj Pythona i Microsoft Edge, a następnie uruchom:

- `build_exe.bat` — biblioteki, testy i budowa EXE;
- gotowy program: `dist\Ksef-Pobieranie.exe`;
- do pracy z kodu: `python ksef_stable.py`.

W aplikacji kliknij „Start / Otwórz KSeF”, zaloguj się ręcznie, ustaw filtry w KSeF i kliknij „Pobierz FV”. Dane logowania nie są zbierane przez program.

## Poprawki niezawodności

- Skanowanie zaczyna się od strony 1, a na końcu wraca do strony 1 również po 50+ stronach.
- Nieudana zmiana strony zgłasza błąd zamiast cichego zakończenia.
- Każda paczka ma najwyżej 10 faktur.
- ZIP musi zawierać właściwą liczbę prawidłowych PDF-ów. Gdy nazwy zawierają identyfikatory KSeF, są dodatkowo porównywane z zaznaczeniem.
- Niekompletna paczka jest pobierana ponownie, a po niepowodzeniu dzielona na mniejsze: 10 → 5 → 1.
- Faktura nie jest zaliczana, dopóki pliki nie zostaną zweryfikowane.
- Po każdej prawidłowej paczce aktualizowany jest `potwierdzone_fv.json`.
- Sesja zapisuje `run_log.txt`, `info.txt` oraz listę braków przy niepowodzeniu.
- Okno aktualizuje się podczas oczekiwania; nie można uruchomić dwóch pobrań jednocześnie.
- Build EXE używa jednego pliku spec i uruchamia testy przed kompilacją.

## Testy

`python -m pip install -r requirements.txt`

`python -m unittest discover -s tests -p "test_*.py" -v`

Testy obejmują podstawowe scenariusze bez logowania do KSeF. **Pełne potwierdzenie działania wymaga testu na rzeczywistej sesji KSeF i Microsoft Edge.**

## Diagnostyka

W folderze `pobrane_fv\<data>__WSZYSTKIE_FV\`:

- `run_log.txt` — kolejne czynności i błędy;
- `potwierdzone_fv.json` — numery FV potwierdzone przez program;
- `brakujace_fv.txt` — lista niepobranych pozycji;
- `info.txt` — podsumowanie.

Nie umieszczaj dokumentów księgowych ani logów z danymi faktur w publicznym repozytorium.

Autor: Paweł Ruchlicki.
