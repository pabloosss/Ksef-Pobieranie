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

## Dodatkowe zabezpieczenia pobierania

- **Oddzielny folder na każdą próbę:** niedokończony plik `.crdownload` po wcześniejszym błędzie nie blokuje następnej paczki. Nieudane próby nie zwiększają licznika pobranych FV.
- **Bezpieczny zapis paczki:** pliki z ZIP są najpierw sprawdzane w folderze tymczasowym. Dopiero po przejściu kontroli trafiają do sesji. Przy błędzie zapisu program wycofuje pliki opublikowane przez tę próbę.
- **Dokładny licznik:** po zakończeniu liczba PDF w folderze musi odpowiadać liczbie faktur potwierdzonych przez program. Rozbieżność oznacza błąd do wyjaśnienia, a nie fałszywy komunikat „gotowe”.
- **Diagnostyka:** jeśli Windows blokuje usunięcie niedokończonego pobierania, jego osobny folder może pozostać w sesji; nie jest traktowany jako pobrana faktura.

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
