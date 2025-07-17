# Schemat bazy danych: Fitness Tracker

Opis struktury bazy danych wykorzystywanej w aplikacji do analizy progresu siłowego.

## Tabela: `Cwiczenie`
Zawiera listę ćwiczeń dostępnych w aplikacji.

| Kolumna          | Typ danych     | Opis                                           |
|------------------|----------------|------------------------------------------------|
| Id               | int            | Klucz główny                                   |
| Nazwa            | nvarchar(255)  | Nazwa ćwiczenia                                |
| PartieGlowne     | nvarchar(255)  | Główne grupy mięśniowe (np. "Klatka", "Nogi") |
| PartieSzczeg     | nvarchar(255)  | Szczegółowe partie (np. "Czworogłowe")         |

---

## Tabela: `PomiaryCiala`
Zapisuje pomiary ciała użytkownika w czasie.

| Kolumna           | Typ danych     | Opis                                  |
|-------------------|----------------|---------------------------------------|
| Id                | int            | Klucz główny                          |
| DataPomiaru       | date           | Data wykonania pomiaru               |
| Waga              | decimal        | Masa ciała (kg)                       |
| KlatkaPiersiowa   | decimal        | Obwód klatki piersiowej (cm)         |
| Talia             | decimal        | Obwód talii (cm)                      |
| Brzuch            | decimal        | Obwód brzucha (cm)                    |
| Biodra            | decimal        | Obwód bioder (cm)                     |
| Udo               | decimal        | Obwód uda (cm)                        |
| Lydka             | decimal        | Obwód łydki (cm)                      |
| Ramie             | decimal        | Obwód ramienia (cm)                  |
| MasaMiesniowa     | decimal        | Masa mięśniowa (kg / % zależnie od pomiaru) |
| MasaTluszczowa    | decimal        | Masa tłuszczowa (kg / %)             |
| TkankaTluszczowa  | decimal        | % tkanki tłuszczowej                 |
| WodaCiala         | decimal        | % wody w organizmie                  |
| Notatka           | nvarchar(255)  | Dowolna notatka do pomiaru          |

---

## Tabela: `Trening`
Reprezentuje pojedynczy dzień treningowy.

| Kolumna | Typ danych | Opis                    |
|---------|------------|-------------------------|
| Id      | int        | Klucz główny            |
| Data    | date       | Data wykonania treningu |

---

## Tabela: `TreningCwiczenie`
Łączy trening (`Trening`) z ćwiczeniem (`Cwiczenie`).

| Kolumna       | Typ danych | Opis                                             |
|---------------|------------|--------------------------------------------------|
| Id            | int        | Klucz główny                                     |
| TreningId     | int        | Klucz obcy do `Trening.Id`                       |
| CwiczenieId   | int        | Klucz obcy do `Cwiczenie.Id`                     |

---

## Tabela: `TreningSeria`
Zawiera dane każdej serii wykonanej w danym ćwiczeniu.

| Kolumna            | Typ danych | Opis                                   |
|--------------------|------------|----------------------------------------|
| Id                 | int        | Klucz główny                           |
| TreningCwiczenieId | int        | Klucz obcy do `TreningCwiczenie.Id`    |
| Powtorzenia        | int        | Liczba powtórzeń w serii               |
| Ciezar             | decimal    | Ciężar użyty w serii (kg)              |

---

## Relacje między tabelami

- `Trening (1) ⟶ (∞) TreningCwiczenie`: Jeden trening zawiera wiele ćwiczeń.
- `Cwiczenie (1) ⟶ (∞) TreningCwiczenie`: Jedno ćwiczenie może pojawić się w wielu treningach.
- `TreningCwiczenie (1) ⟶ (∞) TreningSeria`: Jedno ćwiczenie w treningu może mieć wiele serii.