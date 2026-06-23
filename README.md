# EMERLOG Urlopy

Aplikacja Flask do obsługi urlopów, obecności i limitów urlopowych.

## Funkcje

- logowanie użytkowników,
- role: pracownik, menedżer, kadry, admin,
- składanie wniosków urlopowych,
- automatyczne liczenie dni roboczych,
- polskie święta,
- akceptacja, odrzucenie i cofnięcie do poprawy,
- wymagany komentarz przy odrzuceniu i cofnięciu,
- obecność na dany dzień,
- kalendarz miesięczny,
- lista pracowników,
- limity urlopowe,
- raport CSV,
- historia działań.

## Logo i ikona

Pliki graficzne wrzucamy do katalogu:

```text
grafiki/
```

Aplikacja sama szuka logo po nazwach typu:

```text
logo.png
logo.jpg
emerlog.png
emerlog-logo.png
```

Ikona strony jest szukana po nazwach typu:

```text
favicon.ico
icon.png
ikona.png
logo.png
```

Najlepiej trzymać tak:

```text
grafiki/logo.png
grafiki/ikona.png
```

## Uruchomienie lokalne Windows

```powershell
py -m venv venv
venv\Scripts\activate
py -m pip install -r requirements.txt
py app.py
```

Potem wejdź:

```text
http://127.0.0.1:5000
```

## Wdrożenie na VPS

```bash
cd /opt/Urlopy-Aplikacja
git pull
source venv/bin/activate
pip install -r requirements.txt
systemctl restart urlopy
systemctl restart nginx
```

Adres serwera:

```text
http://31.70.86.109
```

## Baza danych

Baza SQLite tworzy się automatycznie jako:

```text
database.db
```

Nie wrzucamy jej na GitHub.
