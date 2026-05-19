# Analizator progresu na silowni

Dashboard analityczny do monitorowania treningu silowego, progresu cwiczen,
zmeczenia treningowego oraz zmian w skladzie i pomiarach ciala. Aplikacja jest
zbudowana w Streamlit, a logika obliczen jest wydzielona do testowalnej warstwy
metryk.

Wersja online: <https://progressanalyzer-jysznkmwcjnejwamgmlfqd.streamlit.app>

## Glowne funkcje

- przeglad sesji treningowych: objetosc, liczba serii, intensywnosc, czas trwania,
- metryki cwiczen: laczna objetosc, szacowane 1RM, trendy sily, ekspozycja,
- analiza partii miesniowych z uwzglednieniem mapowania cwiczenie-miesien,
- heatmapa partii miesniowych na podstawie tygodniowej objetosci,
- monitoring zmeczenia na podstawie RIR, serii do upadku i objetosci,
- analiza progresu: cwiczenia poprawiajace sie, stagnujace i regresujace,
- metryki ciala: masa, masa miesniowa, tkanka tluszczowa, obwody, proporcje,
- import treningow z plikow TXT przez panel boczny.

## Architektura

Projekt jest podzielony na warstwy:

```text
streamlit_app.py
  -> ui/                 # widoki Streamlit i helpery prezentacyjne
  -> metrics/            # czysta logika obliczania metryk
  -> data_loader.py      # mapowanie danych z bazy do modeli domenowych
  -> data_manager.py     # operacje wysokiego poziomu na danych
  -> db/                 # polaczenie i zapytania SQL
  -> models/             # niemutowalne modele domenowe
```

Najwazniejsza zasada: widoki nie licza metryk. Dane sa ladowane, mapowane do
`MetricsInput`, przetwarzane przez `metrics.metrics_engine.compute_all_metrics`,
a dopiero potem renderowane w UI.

## Struktura danych

Warstwa treningowa korzysta z tabel:

- `workout_sessions`
- `workout_exercises`
- `workout_sets`
- `exercises`
- `exercise_muscle_map`

Warstwa pomiarow ciala korzysta z tabel:

- `body_composition`
- `body_measurements`

Tabela `exercise_muscle_map` pozwala przypisac cwiczenie do wielu miesni:

- `exercise_id`
- `muscle_group`
- `muscle_name`
- `role` (`primary`, `secondary`, `stabilizer`)
- `set_factor`

Domyslne wagi uzywane w analizie objetosci:

- `primary`: `1.0`
- `secondary`: `0.5`
- `stabilizer`: `0.25`

Seed mapowania miesni:

```bash
python -m db.seed_exercise_muscle_map
```

## Wymagania

- Python 3.12 lub nowszy
- baza danych dostepna przez `DATABASE_URL`
- zaleznosci z `requirements.txt`

Minimalny plik `.env`:

```env
DATABASE_URL=postgresql+psycopg2://user:password@host:5432/database
```

## Instalacja

```bash
git clone https://github.com/BaseMar/ProgressAnalyzer.git
cd "Analizator progresu na silowni"
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Uruchomienie

```bash
streamlit run streamlit_app.py
```

Po starcie aplikacja laduje dane z bazy, buduje `MetricsInput`, liczy metryki i
udostepnia widoki:

- Main Dashboard
- Exercises
- Body Parts
- Analytics
- Body Metrics

## Testy

Testy sa oparte o `pytest` i pokrywaja modele, mappery, warstwe metryk,
filtrowanie danych oraz czyste helpery UI.

```bash
python -m pytest
python -m compileall -q db metrics models ui streamlit_app.py data_loader.py data_manager.py mapper.py
```

## Import treningu TXT

Importer oczekuje formatu:

```text
Godzina: 10:30 - 12:45

1. Bench Press
10x100 / 8x110 / 6x115
RIR: 2 / 1 / 0

2. Row
12x60 / 10x65
RIR: 3 / 2
```

Jezeli cwiczenie nie istnieje w bazie, aplikacja pokazuje podobne nazwy i pozwala
wybrac istniejace cwiczenie albo dodac nowe.

## Zasady projektowe

- metryki sa funkcjami bez zaleznosci od Streamlit,
- modele domenowe sa niemutowalne (`dataclass(frozen=True)`),
- dostep do bazy jest odseparowany od obliczen,
- UI renderuje gotowe dane i nie wykonuje logiki biznesowej,
- testy sprawdzaja zachowanie, a nie szczegoly implementacyjne.

## Zrzuty ekranu

### Main Dashboard

![Dashboard 1](screenshots/Dashboard_1.png)
![Dashboard 2](screenshots/Dashboard_2.png)
![Dashboard 3](screenshots/Dashboard_3.png)

### Exercises

![Exercise View 1](screenshots/Exercise_1.png)
![Exercise View 2](screenshots/Exercise_2.png)

### Body Parts

![Body Parts 1](screenshots/Body_Parts_1.png)
![Body Parts 2](screenshots/Body_Parts_2.png)

### Analytics

![Analytics 1](screenshots/Analytics_1.png)
![Analytics 2](screenshots/Analytics_2.png)
![Analytics 3](screenshots/Analytics_3.png)

### Body Metrics

![Body Metrics 1](screenshots/Body_Metrics_1.png)
![Body Metrics 2](screenshots/Body_Metrics_2.png)
![Body Metrics 3](screenshots/Body_Metrics_3.png)
![Body Metrics 4](screenshots/Body_Metrics_4.png)
![Body Metrics 5](screenshots/Body_Metrics_5.png)
