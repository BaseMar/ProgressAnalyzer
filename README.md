# Analizator progresu na siłowni

Aplikacja napisana w **Python + Streamlit + MS SQL + Plotly**, służąca do **analizy progresu treningowego**.  
Projekt ma na celu wizualizację danych z treningów, pomiarów ciała i składu ciała, a także automatyczne wczytywanie treningów z plików `.txt`.

---

## Technologie

- 🐍 **Python 3.11+**
- 🧠 **Streamlit** – interaktywny dashboard
- 🗃️ **MS SQL Server** – baza danych
- 📊 **Plotly** – wizualizacje danych
- 📈 **Pandas** – analiza danych
- 🔗 **pyodbc** – połączenie z bazą danych

---

## Funkcjonalności

### Parser plików treningowych
- Automatyczne rozpoznawanie formatu:
    27.10.2025
    1. Incline Dumbbell Press
    8x22/8x22/8x22/8x22

    2. Dipy
    7/7/7

- Obsługa wzorców serii (`reps x weight` lub tylko `reps`)
- Tryb **testowy** (bez zapisu do bazy)
- Automatyczne dodawanie nowych ćwiczeń do bazy danych

### Analiza treningu *(w przygotowaniu)*
- Progres siłowy w czasie  
- Objętość treningowa (reps × ciężar)  
- Szacowany 1RM  
- Heatmapa partii mięśniowych  
- Analiza intensywności i częstotliwości treningów  

### Pomiar ciała *(rozszerzalny)*
- **Body Measurements**: klatka, talia, brzuch, biodra, udo, łydka, ramię/biceps  
- **Body Composition**: waga, masa mięśniowa, masa tłuszczowa, masa wody, % tkanki tłuszczowej  

---

## Architektura projektu
    project/
    │
    ├── app.py # Główny plik Streamlit
    │
    ├── db/
    │ ├── connection.py # Połączenie z MS SQL
    │ ├── queries.py # zapytania do bazy SQL
    │
    ├── components/
    │ ├── parser.py # Parser plików .txt
    │ ├── charts.py # (Wkrótce) Wizualizacje Plotly
    │
    ├── services/
    │ ├── chart_services.py # Parser plików .txt
    │ ├── kpi_services.py
    │
    ├── README.md
    └── schema.md

---

## Struktura bazy danych

Baza danych została zaprojektowana w **3NF (Trzeciej Formie Normalnej)** i obejmuje następujące tabele:

| Tabela | Opis |
|--------|------|
| **Exercises** | Lista ćwiczeń |
| **TrainingSessions** | Sesje treningowe (z datą) |
| **TrainingSets** | Serie wykonane w ramach sesji |
| **BodyMeasurements** | Pomiary obwodów ciała |
| **BodyComposition** | Skład ciała (waga, tłuszcz, mięśnie, woda) |

---

## Uruchomienie projektu
    streamlit run app.py

---

## Autor
Martino Sebastiani / BaseMar
Cel: projekt portfolio – aplikacja do analizy progresu treningowego.