# Analizator progresu na siłowni

Aplikacja napisana w **Python + Streamlit + MS SQL + Plotly**, służąca do **analizy progresu treningowego**.  
Projekt ma na celu wizualizację danych z treningów, pomiarów ciała i składu ciała, a także automatyczne wczytywanie treningów z plików `.txt`.

---

## Technologie

- **Python 3.11+**
- **Streamlit** – interaktywny dashboard
- **MS SQL Server** – baza danych
- **Plotly** – wizualizacje danych
- **Pandas** – analiza danych
- **pyodbc** – połączenie z bazą danych

---

## Funkcjonalności

### Parser plików treningowych
- Automatyczne rozpoznawanie formatu:
27.10.2025
    1. Incline Dumbbell Press
    8x22/8x22/8x22/8x22
    
    2. Dipy
    7/7/7

- Obsługa różnych wzorców serii (`reps x weight` lub tylko `reps`)
- Tryb **testowy** (bez zapisu do bazy)
- Automatyczne dodawanie nowych ćwiczeń do bazy

### Analiza treningu *(w przygotowaniu)*
- Progres siłowy
- Objętość treningowa
- Szacowany 1RM
- Heatmapa partii mięśniowych
- Analiza intensywności i częstotliwości treningu

### Pomiar ciała *(rozszerzalny)*
- **Body Measurements**: klatka, talia, brzuch, biodra, udo, łydka, ramię/biceps  
- **Body Composition**: waga, masa mięśniowa, masa tłuszczowa, masa wody, % tkanki tłuszczowej  

---

## Architektura projektu
project/
│
├── app.py # Główny plik Streamlit
├── db/
│ ├── connection.py # Połączenie z MS SQL
│ ├── schema.sql # Skrypt tworzący bazę
│
├── components/
│ ├── parser.py # Parser plików .txt
│ ├── charts.py # (Wkrótce) Wizualizacje Plotly
│
├── assets/ # Pliki pomocnicze (np. przykładowe treningi)
│
├── README.md
└── schema.md

---

## Struktura bazy danych

Zaprojektowana w **3NF (Trzeciej Formie Normalnej)**:

| Tabela | Opis |
|--------|------|
| **Exercises** | Lista ćwiczeń |
| **TrainingSessions** | Sesje treningowe z datą |
| **TrainingSets** | Serie wykonane w ramach sesji |
| **BodyMeasurements** | Pomiary obwodów ciała |
| **BodyComposition** | Skład ciała (waga, tłuszcz, mięśnie, itp.) |

---

## Przykład działania parsera

Wgranie pliku:
28.10.2025
1. Leg Press
10x110/10x120/10x130/10x140

2. Rumuński martwy ciąg
8x100/8x100/8x100/8x100

Zwróci DataFrame:
| Data sesji | Ćwiczenie | Powtórzenia | Ciężar (kg) |
|-------------|------------|--------------|--------------|
| 28.10.2025 | Leg Press | 10 | 110 |
| 28.10.2025 | Leg Press | 10 | 120 |
| ... | ... | ... | ... |

---

## Tryb testowy

W aplikacji dostępny jest **checkbox „🧪 Tryb testowy (bez zapisu)”** –  
umożliwia testowanie parsera bez modyfikowania danych w bazie SQL.

---

Autor
Martino Sebastiani / BaseMar

Cel: projekt portfolio – aplikacja do analizy progresu treningowego.