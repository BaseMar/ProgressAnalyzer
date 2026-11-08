# Walidacja przebudowy rekomendacji — 8 listopada 2026

Status: wszystkie osiem etapów ukończone; implementacja, konfiguracja i publiczne wydanie zweryfikowane.

## Wynik implementacji

Jeden silnik realizuje zatwierdzoną progresję: powtórzenia → wyrównanie lżejszych
serii → powtórzenia na wspólnym ciężarze → nowy wspólny ciężar. Obowiązuje jeden
pełny sukces i limit zwiększenia 10% na serię. Deload zachowuje serie i powtórzenia,
obniża ciężary o 30–40% i wyznacza cel RIR 3–4. Szczegóły zawiera
[specyfikacja](progression-redesign-rules.md).

## Przeprowadzone sprawdzenia

| Sprawdzenie | Wynik |
| --- | --- |
| Pełny zestaw lokalny, Python 3.12.2 / Streamlit 1.66.1 | 504 przeszły, 5 PostgreSQL sprawdzono osobno; łącznie 509 przypadków. |
| PostgreSQL — izolowane schematy i rollback | 5 przeszło, wszystkie schematy testowe usunięte przez rollback. |
| Macierz nowych reguł | Wyrównanie 60/55/55 → 60/60/60, zachowanie powtórzeń, limit 10%, korekty, zastój, czas i legacy bodyweight przeszły. |
| Migracja 007 na rzeczywistej bazie | Dodano wyłącznie tożsamość pozycji; skróty danych 6 istniejących tabel przed/po są identyczne. |
| Zapis zatwierdzonego planu | Wersja 6, ID 15, od 10 listopada, 36 pozycji; źródłowa wersja ID 14 i zapisane treningi zachowane. |
| Kompilacja i kontrola formatowania zmian | Przeszły. |
| Chrome 1440 px: Overview, Analysis, Plan, History | Bez wyjątków aplikacji i błędów JS. |
| Otwarcie importu i pełnego treningu | Przeszło, bez zapisywania testowych danych do rzeczywistej historii. |
| Chrome 390 px: pełny trening Overview | Bez poziomego przepełnienia i wyjątków. |
| Publiczne wydanie i CI | Commit `a543c83` na main, CI zakończone sukcesem; nowe reguły potwierdzone w publicznej aplikacji. |

Wydanie aplikacji: [`a543c83`](https://github.com/BaseMar/ProgressAnalyzer/commit/a543c830704c103b70ad5d8b69dbd3a9575e70f4).
[CI wydania](https://github.com/BaseMar/ProgressAnalyzer/actions/runs/42472144063)
zakończyło się sukcesem. W [publicznej aplikacji](https://progressanalyzer-jysznkmwcjnejwamgmlfqd.streamlit.app/)
ponownie sprawdzono cztery widoki, otwarcie importu, pełny trening oraz szerokość
390 px, bez wyjątków aplikacji, błędów JavaScript i poziomego przepełnienia.
Rozwinięte wyjaśnienie celów potwierdziło nowe zasady: jeden pełny sukces,
wyrównywanie, limit 10% na serię oraz deload z zachowaniem serii/powtórzeń i RIR 3–4.

Migracja zachowała 127 sesji, 884 zapisane wystąpienia ćwiczeń, 2531 serii,
5 poprzednich wersji planu, 25 dni planu i 174 poprzednie pozycje planu.
Następnie, na wyraźną zgodę użytkownika, dopisano szóstą wersję planu.

## Porównanie na rzeczywistych zapisach

Odtworzono 72 decyzje na dwa tygodnie od 8 listopada. Poprzedni kod został
uruchomiony z osobnej kopii źródeł sprzed przebudowy. Porównania są retrospektywnym
sprawdzeniem zapisanej historii i konfiguracji, nie badaniem skuteczności treningu.

Osiem decyzji na 9 listopada dotyczy tej samej wersji ID 14. Cztery cele +1
powtórzenie pozostały takie same, jedno ćwiczenie nadal nie ma właściwej zwykłej
bazy, a trzy automatyczne propozycje startu stały się ręcznym doborem — zgodnie
z wybraną regułą 6B. Źródła pozostały dostępne.

Pozostałe 64 decyzje dotyczą zatwierdzonej nowej konfiguracji od 10 listopada.
Zmiany wyniku obejmują zarówno nowy silnik, jak i nowe zakresy/RIR, więc nie są
przedstawiane jako porównanie samego algorytmu przy niezmienionym planie.
Cały nowy raport zawiera: 61 ręcznych startów po zmianie kontekstu, 7 celów +1,
2 braki zwykłej bazy i 2 niekompletne wykonania. To liczby decyzji, nie liczby
odrębnych ćwiczeń. Pierwsze wykonania nowej konfiguracji ustalą nową bazę.

W starszych zapisach podciągania i dipów kilogramy mają nieokreśloną konwencję.
Nowy mechanizm nie zmienia surowych wartości i nie proponuje ich jako przyszłej
masy ciała lub dodatkowego obciążenia. Osobny test sprawdza również niejednoznaczne
powtórzone wystąpienie ćwiczenia w jednej sesji.

## Powrót do poprzedniego działania

Poprzedni kod aplikacji: `4039b72db4ebf7b46c9ba4434bfeac46db35d8ba`.
Migracja 007 dodaje osobną tabelę, więc starsza aplikacja może nadal czytać swoje
tabele. Starszy program `db.migrate` odrzuca jednak nieznaną rewizję 007; podczas
ewentualnego przywracania aplikacji trzeba zachować nowszy migrator.

Nie usuwać tabeli tożsamości ani nie nadpisywać treningów podczas cofania kodu.
Wersja planu od 10 listopada jest osobnym, zatwierdzonym zapisem: cofnięcie kodu
nie cofa automatycznie parametrów planu. Ewentualna kolejna zmiana planu powinna
utworzyć nowy snapshot zgodnie z mechanizmem wersji.
