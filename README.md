# EMERLOG Urlopy / Leave Manager

Aplikacja Flask do obsługi urlopów i nieobecności.

## Funkcje

- logowanie użytkowników,
- role: pracownik, menedżer, kadry, admin,
- składanie wniosków urlopowych,
- automatyczne liczenie dni roboczych,
- polskie święta,
- akceptacja / odrzucenie / cofnięcie do poprawy,
- wymagany komentarz przy odrzuceniu i cofnięciu,
- obecność na dany dzień,
- kalendarz miesięczny,
- lista pracowników,
- limity urlopowe,
- raport CSV,
- historia działań.

## Uruchomienie

```powershell
cd C:\Users\pawel.ruchlicki\Desktop\Urlopy-Aplikacja-main
py -m venv venv
venv\Scripts\activate
py -m pip install Flask Werkzeug
py app.py
```

Potem wejdź:

```text
http://127.0.0.1:5000
```

## Konta testowe

```text
jan / jan123
anna / anna123
pawel / pawel123
ewa / ewa123
kadry / kadry123
admin / admin123
```

## Logo

Wgraj logo jako:

```text
grafiki/logo.png
```

## Baza danych

Baza SQLite tworzy się automatycznie jako:

```text
database.db
```

Nie wrzucamy jej na GitHub.
