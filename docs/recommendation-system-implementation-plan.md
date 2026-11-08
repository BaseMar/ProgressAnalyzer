# Plan wdrożenia systemu rekomendacji

Data: 8 listopada 2026. Status: wszystkie osiem etapów ukończone i opublikowane.
Podstawa: [zatwierdzone zasady v1.0](progression-redesign-rules.md).
Poniższy plan dokumentuje wykonany zakres i kryteria odbioru. Zatwierdzone reguły
działają w publicznej aplikacji; szczegóły sprawdzeń zawiera raport walidacji.

## Stan realizacji

| Etap | Stan | Rezultat |
| --- | --- | --- |
| 1. Zasady | Ukończony | Zatwierdzony schemat wyrównywania, 10% / 4 wykonania / 21 dni, pełny deload 30–40%, czas i ręczne obciążenie masy ciała. |
| 2. Model | Ukończony | Wersjonowany wynik, cele per seria, migracja 007 zastosowana; skróty sześciu istniejących tabel pozostały identyczne. |
| 3. Historia | Ukończony | Trwałe klucze pozycji, jawne źródło wnioskowania, wykrycie niejednoznacznego dopasowania kilku zapisów. |
| 4. Zwykły silnik | Ukończony | +1 powtórzenie, wyrównywanie w krokach, jeden sukces i nowy wspólny ciężar. |
| 5. Wyjątki | Ukończony w uzgodnionym zakresie | Korekty, zastój, długa przerwa, deload/powrót, czas i ręczny ciężar/asysta. |
| 6. Interfejs | Ukończony | Spójne cele i komunikaty, źródła i eksport; przeglądarka 1440 px oraz 390 px. |
| 7. Plan i historia | Ukończony | Zatwierdzona wersja 6 (ID 15) od 10 listopada, 36 pozycji; porównanie 72 przyszłych decyzji na zapisanej historii. |
| 8. Publikacja | Ukończony | Wydanie `a543c83` wysłane na main; CI zakończone sukcesem, nowe reguły i cztery widoki sprawdzone w publicznej aplikacji na komputerze i telefonie. |

Weryfikacja: 504 testy lokalne i 5 osobnych testów PostgreSQL przeszło.
PostgreSQL używał wydzielonych schematów wycofanych po każdym teście. Kompilacja
oraz kontrola zmian przeszły. Test przeglądarki przeszedł dla czterech stron,
otwierania importu i pełnego treningu, bez wyjątków JS i bez poziomego przepełnienia
Overview przy szerokości 390 px. Szczegóły: [raport walidacji](recommendation-system-validation.md).

## Cel i zakres

System proponuje następny trening dla celu hipertrofia + budowa siły. Uwzględnia
ciężar startowy, dobieranie obciążenia, redukcje wskutek zmęczenia, RIR w każdej
serii oraz nieznaną lub zmienną długość przerw. Zwykła progresja działa bez
obowiązkowej konfiguracji bloków. Cele pozostają propozycjami oddzielonymi od
zapisanego planu i faktycznych wyników.

Kolejność: zasady → model danych → interpretacja historii → zwykły silnik →
wyjątki → interfejs → konfiguracja planu i ocena na historii → publikacja.
Różne ciężary serii należą do podstawowego zakresu, a nie dodatku po publikacji.

Każdy etap kończy się konkretnym rezultatem, sprawdzeniem właściwym dla zmian
i krótkim raportem: co działa, jak to zweryfikowano, co pozostaje do zrobienia.
Testy dodajemy wraz z implementacją zachowań, nie dopiero przed publikacją.

## 1. Zamknięcie zasad i przykładów decyzji

**Rezultat:** jedna wersja specyfikacji oraz tabela przypadków z oczekiwanymi wynikami.

Użytkownik odpowiedział na osiem pytań: **1B, 2A, 3B, 4A, 5A, 6B,
7 — istniejące zapiski, 8B**. Oznacza to:

- podwyżkę dopiero po sukcesie wszystkich planowanych serii na ich własnych ciężarach;
- próbę dodania jednego powtórzenia łącznie;
- jeden pełny sukces jako warunek podwyżki, bez drugiego potwierdzenia;
- brak podwyżki przy RIR poniżej celu, z rozróżnieniem potrzeby redukcji;
- korektę po pierwszym niepowodzeniu przy dolnej granicy, dotyczącą problematycznej serii;
- ręczny wybór nieustalonego ciężaru startowego przy wglądzie w historię;
- korzystanie z istniejących oznaczeń rozgrzewki i serii roboczych;
- automatyczny deload według kalendarza.

Użytkownik doprecyzował progresję różnych ciężarów: najpierw wyrównanie lżejszych
serii do ustalonego ciężaru pierwszej serii. Przykład dla 8–12:
`60 × 12 / 55 × 12 / 55 × 12` → cel `60 × 12 / 60 × 8 / 60 × 8`.
Dopiero po osiągnięciu sufitu przez wszystkie serie na wspólnym ciężarze
zwiększamy go o dostępny krok, z minimum zakresu jako celem każdej serii.
Pytania uzupełniające są zamknięte: limit 10% także dla wyrównywania, zastój po
4 wykonaniach, przerwa ponad 21 dni, czas +5 s, ręczna zmiana obciążenia/asysty
w ćwiczeniach masy ciała oraz jawne zachowanie dotychczasowego wnioskowania serii.
Deload zachowuje wszystkie serie i powtórzenia, obniża ciężar o 30–40% i wyznacza
cel RIR 3–4. Zasady poniżej opisują zakres odbioru zrealizowanych prac.

- Oddzielić potwierdzone preferencje użytkownika od propozycji parametrów.
- Rozpisać ustaloną progresję różnych ciężarów w tabeli: powtórzenia na obecnych
  obciążeniach → wyrównanie po pełnym sukcesie → powtórzenia na wspólnym ciężarze
  → nowy wspólny ciężar. Uwzględnić wpływ wcześniejszej pracy na późniejsze serie.
- Ustalić wybór serii dla dodatkowego powtórzenia i zachowanie po zmianie pierwszej serii.
- Zamknąć zasady kalibracji, wymaganego RIR, powtórzeń poniżej minimum i korekt obciążenia.
- Liczba sukcesów jest ustalona: jeden. Progi 4/10%/21 dni oraz potwierdzanie
  poprawy RIR opisuje zamknięta specyfikacja v1.0.
- Ustalić, jak jednoznacznie odróżniamy rozgrzewkę, serię roboczą i próbę doboru
  ciężaru przy imporcie oraz co robimy, jeśli brakuje takiej informacji.
- Określić dokładnie zakres automatyki dla czasu, masy ciała, asysty i deloadu.
  Każdy wariant otrzymuje regułę liczbową albo jawną decyzję o kalibracji ręcznej.

**Odbiór:** każda pozycja macierzy na końcu dokumentu ma określone działanie,
cel lub powód braku celu oraz warunki potwierdzania. Przed etapem 4 nie pozostają
otwarte decyzje zmieniające wynik zwykłej progresji. Parametry konkretnego planu
użytkownika mogą poczekać do etapu 7; silnik operuje na konfiguracji ćwiczenia.

## 2. Model konfiguracji i wyniku rekomendacji

**Rezultat:** modele obsługujące uzgodnione zasady, zgodne z historycznymi zapisami.

- Oddzielić politykę rekomendacji od kalendarza bloków i deloadu.
- Utrzymać konfigurację ćwiczenia: serie, zakres, RIR i rzeczywiste kroki sprzętu;
  dodać tylko pola potrzebne do rozstrzygniętych reguł.
- Zaprojektować stabilną tożsamość pozycji ćwiczenia między wersjami planu;
  zmiana nazwy lub dnia nie może sama kasować przydatnej historii.
- Oddzielić przeznaczenie serii od oceny wysiłku. Nie wymagać nowych ręcznych
  etykiet, jeśli dane już pozwalają jednoznacznie odtworzyć przeznaczenie.
- Wynik rekomendacji ma zawierać cele per seria, działanie, kod przyczyny,
  wskazane sesje źródłowe, potwierdzenia, ograniczenia danych i wersję zasad.
- Rozróżnić kalibrację, utrzymanie, dodatkowe powtórzenie, wyrównanie ciężarów, nowy wspólny ciężar,
  korektę obciążenia, deload/powrót i brak wystarczających danych.
- Gdy potrzebne są nowe pola bazy, przygotować kolejną wolną migrację i zgodny
  odczyt starszych planów. Nie przepisywać historycznych RIR ani wyników.
- Około 3 minut pozostaje deklarowanym zwyczajem; nie uzupełniać tym historycznych
  przerw. Ich rejestrowanie pozostaje opcjonalne.

**Główne miejsca:** `models/progression.py`, `models/training_plan.py`,
`models/set_interpretation.py`, `models/workout_set.py`, `db/training_plans.py`,
`db/progression.py`, ewentualnie nowa migracja i `db/migrate.py`.

**Odbiór:** nowe i stare konfiguracje są poprawnie odczytywane; zapis i odczyt
zachowują ustawienia, a migracja nie zmienia dotychczasowych wyników. Testy bazy
działają na danych testowych. Plan wycofania uwzględnia, że stare wydanie aplikacji
może odrzucać nieznany numer migracji.

## 3. Wspólna interpretacja serii i dobór historii

**Rezultat:** jeden zestaw obserwacji używany przez analizę i rekomendacje.

- Odróżniać serię roboczą, rozgrzewkę, czas i deload bez przypisywania przeznaczenia
  wyłącznie na podstawie RIR; zachować jawne korekty użytkownika i ich pierwszeństwo.
- Zachować pozycje, obciążenia i RIR każdej serii; nie uśredniać różnych ciężarów.
- Odróżnić zapisane fakty, przypuszczenie o kalibracji i zadeklarowaną przyczynę zmiany.
- Rozdzielić historię pokazywaną przy ręcznym doborze nieustalonego startu od
  historii nadającej się do zwykłej progresji już ustalonej bazy. Nie generować
  nowego kandydata na start w trybie kalibracji.
- Uwzględnić rzeczywiste daty, przesunięte treningi, zmiany wersji planu,
  powtórzone ćwiczenia oraz jawnie wybrane zamienniki.
- Trening bez jednoznacznego przypisania do pozycji planu nie daje automatycznego
  potwierdzenia tej pozycji. Ewentualna baza wymaga zgodności faktycznego ćwiczenia.
- Nie pomijać ostatniego słabego lub niepełnego wykonania, by znaleźć starszy sukces.
- Zmiana samego filtra historycznej analizy nie zmienia celu przyszłego treningu.

**Główne miejsca:** `metrics/set_interpretation.py`, `metrics/plan_performance.py`,
`metrics/recommendation_history.py`, `metrics/load_metrics.py`,
`metrics/utils/set_values.py`, `db/plan_adherence.py`.

**Odbiór:** identyczna seria ma spójną interpretację w historii, analizie i danych
silnika; porównania nie korzystają z przyszłych wyników ani z kilogramów innego
ćwiczenia. Niejednoznaczność jest jawna i nie zamienia się w sukces lub regres.

## 4. Podstawowy silnik progresji, w tym różne ciężary serii

**Rezultat:** deterministyczny silnik zwykłego treningu zgodny z tabelą z etapu 1.

- Obsłużyć brak bazy: historia do wglądu, a nieustalony start wybiera użytkownik.
- Generować cele per seria dla wspólnego ciężaru i redukcji wskutek zmęczenia.
- Po pełnym sukcesie różnych ciężarów wyrównywać lżejsze do ustalonego startu:
  zachować cele już na ciężarze odniesienia, a w podnoszonych seriach ustawić minimum.
- Podwyższać wspólny ciężar dopiero po pełnym sukcesie na jednakowym obciążeniu.
- Wprowadzić dodatkowe powtórzenie, potwierdzanie górnej granicy i zwiększenie
  o rzeczywiście dostępny krok obciążenia zgodnie z ustaloną jednostką progresji.
- Po większej pracy we wcześniejszych seriach traktować późniejsze cele zgodnie
  z uzgodnioną regułą; nie wymagać automatycznie poprawy wszystkich wyników naraz.
- Obsłużyć zbyt duży skok sprzętu z konkretnym wyjaśnieniem dalszego działania.
- Oddzielić brak gotowości do podwyżki od potrzeby redukcji; pojedyncze RIR niższe
  od celu nie powoduje automatycznej obniżki całego ćwiczenia.
- Zwykła progresja działa także przy braku kalendarza bloków.

**Główne miejsca:** `metrics/progression.py`, `models/progression.py`,
`db/progression.py`, `tests/test_progression.py`, `tests/test_recommendation_history.py`.

**Odbiór:** macierz zwykłych przypadków przechodzi testy; różne ciężary nie kończą
się ogólnym „nieobsługiwane”. Powtórne wyliczenie dla tych samych danych, daty
i wersji zasad daje ten sam wynik. Obliczenie nie zmienia planu ani historii.

## 5. Niepowodzenia, zastój, deload i pozostałe warianty

**Rezultat:** spójne zachowanie poza zwykłym udanym wykonaniem.

- Niepowodzenie: odróżnić zły start od trudności późniejszych serii; korekta po
  pierwszym problemie przy minimum, natomiast przy większej liczbie powtórzeń
  najpierw rozpatrywać wcześniejsze zakończenie serii w zakresie.
- Możliwy zastój oceniać na porównywalnej pracy i zapasie, nie na samym tonażu.
- Braki danych i nieukończone wykonania nie uruchamiają automatycznej diagnozy regresu.
- Przerwa w historii powoduje uzgodniony tryb ponownego ustalenia bazy.
- Deload jest oddzielnym trybem uruchamianym automatycznie według kalendarza. Po nim wraca baza zwykłego treningu,
  a lżejszy tydzień nie staje się punktem odniesienia dla nowej podwyżki.
- Masa ciała, dodatkowy ciężar i asysta pozostają oddzielnymi wielkościami;
  mniejsza asysta zwiększa trudność. Nie zakładać przyszłej masy ciała.
- Czas ma własną jednostkę progresji. Ćwiczenia jednostronne mają jasną konwencję
  stron, a techniki specjalne nie potwierdzają zwykłych serii.
- Zgłoszony ból/uraz wpływa na decyzję tylko jako rzeczywiście dostępna informacja;
  nie diagnozujemy go z wyników i nie wymagamy nowego obowiązkowego formularza.

**Główne miejsca:** `metrics/progression.py`, `metrics/training_block.py`,
`metrics/progress_metrics.py`, `metrics/training_insights.py`,
`tests/test_deload.py`, `tests/test_set_loads.py`, `tests/test_training_insights.py`.

**Odbiór:** każdy wariant ma właściwy cel albo jasną, uzgodnioną granicę automatyki.
Brak danych nie prowadzi do wymyślonego obciążenia, a deload nie generuje regresu.

## 6. Podłączenie do interfejsu i wspólne komunikaty

**Rezultat:** użytkownik widzi jeden spójny następny krok i jego podstawę.

- Overview pokazuje ciężar i cel każdej serii, RIR, główny powód decyzji
  oraz możliwość obejrzenia ostatniego wykonania i potwierdzeń.
- Plan pozwala ustawić parametry ćwiczenia i niezależny tryb deloadu.
- History umożliwia opcjonalną korektę przeznaczenia serii i danych źródłowych;
  nie dodajemy obowiązku ręcznego opisywania każdej zmiany ciężaru.
- Analysis odróżnia obserwację wyniku, ograniczenia porównania i rekomendację.
  Usunąć sprzeczne oceny pochodzące ze starych reguł.
- Eksport notatki treningowej zachowuje różne ciężary i cele serii oraz miejsce
  na faktyczny wynik. Skopiowany cel nie jest zapisanym wykonaniem.
- Wszystkie komunikaty korzystają ze wspólnego wyniku silnika; widoki nie
  implementują dodatkowych reguł zwiększania lub obniżania ciężaru.
- Zmiana ustawień odświeża obliczenia; cache nie może mieszać wersji zasad.

**Główne miejsca:** `ui/next_workout_view.py`, `ui/overview_view.py`,
`ui/training_plan_view.py`, `ui/utils/plan_editor.py`, `ui/set_classification_view.py`,
`metrics/training_insights.py`, `metrics/overview_summary.py`,
`metrics/utils/recommendation_text.py`, `metrics/workout_template.py`.

**Odbiór:** karta następnego treningu, analiza i eksport są zgodne; brak konieczności
czytania technicznych kodów przyczyn. Przejście Plan → History → Overview i widok
telefonu działają dla pełnej historii oraz dla brakujących danych.

## 7. Dopasowanie Twojego planu i weryfikacja na historii

**Rezultat:** propozycja konfiguracji ćwiczeń i raport przykładowych rekomendacji.

- Odczytać aktywny plan i historię; przygotować per ćwiczenie liczbę serii,
  zakres, cel RIR, skok sprzętu oraz przerwę odniesienia dla hipertrofii i siły.
- Dla ustalonej bazy pokazać ostatnie adekwatne obciążenia. Przy nieustalonym
  starcie pokazać historię i pozostawić ręczny wybór, zgodnie z decyzją 6B.
  Odróżnić tę sytuację od normalnej podwyżki już ustalonej bazy.
- Najpierw przedstawić propozycję konfiguracji; zapis do aktywnego planu jest
  osobnym działaniem i tworzy nową wersję, bez zmieniania dawnych wykonań.
- Odtworzyć wybrane historyczne sytuacje nowym silnikiem. Dla daty odtworzenia
  dostępne są wyłącznie wyniki i ustawienia znane najpóźniej w tym momencie.
- Porównać stary i nowy wynik: decyzja, dane źródłowe, potwierdzenia, przyczyna różnicy.
  Różnice są oczekiwane, ale każda istotna musi wynikać z konkretnej nowej reguły.
- Osobno sprawdzić zaktualizowany plan jako przyszłą konfigurację; nie prezentować
  nowego zakresu/RIR jako ustawień obowiązujących historycznie.
- Sprawdzić pełny zestaw testów, integrację bazy na danych testowych oraz scenariusze
  interfejsu. Uzupełniać testy wyłącznie o nowo ujawnione przypadki lub błędy.

**Odbiór:** nie ma niewyjaśnionych decyzji ani sprzecznych ekranów. Powstaje lista
wybranych sytuacji wraz z wynikiem i uzasadnieniem oraz propozycja parametrów planu.
Odtworzenie historii jest oceną zgodności reguł, nie dowodem przyszłej skuteczności treningu.

## 8. Uruchomienie i wyłączenie starego mechanizmu

**Rezultat:** jedno aktywne wydanie systemu z możliwością odtworzenia decyzji.

- Przed przełączeniem ustalić docelowy commit, stan migracji i zgodny sposób
  powrotu do wcześniejszego działania bez usuwania nowych danych.
- Do porównań można zachować stary silnik, ale po przełączeniu wszystkie ekrany
  korzystają z tej samej aktywnej wersji zasad i konfiguracji.
- Publikować dopiero po wykonaniu wymaganych testów i przeglądzie raportu z etapu 7;
  techniczna publikacja jest osobną czynnością względem przygotowania tego planu.
- Zweryfikować uruchomione wydanie, datę następnego treningu, cele serii, eksport,
  odświeżanie po zmianie ustawień oraz obsługę istniejącego planu.
- Zaktualizować README i dokumentację wydania. Dokumentu poprzedniej publikacji
  nie przedstawiać jako walidacji nowego systemu.

**Odbiór:** działa dokładnie sprawdzone wydanie; jeden mechanizm jest źródłem celów
i komunikatów. Zachowane są historyczne zapisy oraz instrukcja przywrócenia
zgodnego działania. Ocena zachowania po rzeczywistych treningach jest późniejszą
obserwacją, a nie warunkiem technicznego ukończenia implementacji.

## Minimalna macierz przypadków do doprecyzowania w etapie 1

| Przypadek | Co musi rozstrzygnąć specyfikacja |
| --- | --- |
| Brak historii ćwiczenia | Kalibracja bez wymyślania ciężaru. |
| Lżejsze serie początkowe, potem cięższe | Rodzaj serii i ręczny wybór startu przy wglądzie w historię. |
| Stały ciężar, wynik w zakresie | Dokładny wybór celu +1 powtórzenie. |
| Sufit we wszystkich seriach pierwszy raz | Gotowość do podwyżki po jednym pełnym sukcesie. |
| Różne ciężary, np. 60/60/55 | Wyrównanie po pełnym sukcesie; minimum powtórzeń tylko w podnoszonej serii. |
| 60 × 12 / 55 × 12 / 55 × 12 | Cel 60 × 12 / 60 × 8 / 60 × 8 przy wymaganym RIR. |
| 60 × 12 / 60 × 8 / 60 × 8 | Cel 60 × 12 / 60 × 9 / 60 × 8 przy wymaganym RIR. |
| Sufit wszystkich serii na wspólnym ciężarze | Następny wspólny ciężar i minimum zakresu we wszystkich seriach. |
| Zwiększona praca pierwszej serii | Porównywalność i cele późniejszych serii. |
| Jednorazowe RIR poniżej celu | Utrzymanie bez automatycznej redukcji. |
| Za mały zapas przy dużej liczbie powtórzeń | Wcześniejsze zakończenie serii w zakresie. |
| Za mały zapas już przy minimum | Warunki i zakres redukcji ciężaru. |
| Słabsze wyłącznie późniejsze serie | Oddzielenie ich korekty od startu. |
| Brak RIR, brak serii, błędny zapis | Inne ograniczenia danych i brak fałszywego sukcesu/regresu. |
| Jawna rozgrzewka z małym RIR / robocza z dużym RIR | Przeznaczenie niezależne od wysiłku. |
| Dodatkowe serie lub niejednoznaczny import | Wybór planowanych serii bez podwójnego liczenia. |
| Zmienny lub nieznany odpoczynek | Ograniczenie wniosków bez blokowania całego systemu. |
| Zbyt duży skok sprzętu | Dalsze działanie zamiast bezterminowego „utrzymaj”. |
| Zastój i jednorazowa zmiana RIR | Dokładne potwierdzenie trendu. |
| Dłuższa przerwa / powrót po deloadzie | Ponowne ustalenie bazy i potwierdzeń. |
| Zmiana nazwy, dnia, kolejności, zakresu lub RIR | Która historia pozostaje bazą, a która potwierdzeniem. |
| Zamiennik / inne urządzenie / powtórzona pozycja ćwiczenia | Oddzielna tożsamość i kroki sprzętu. |
| Czas, masa ciała, asysta, strony | Własne jednostki, kierunek progresji i granice automatyki. |
| Przesunięty trening, duplikat sesji, przyszłe dane | Chronologia bez podwójnych i przyszłych potwierdzeń. |
| Zmiana filtra Analysis, eksport, inny ekran | Ten sam przyszły cel z tego samego silnika. |

## Granice przebudowy

System nie układa automatycznie nowego zestawu ćwiczeń, nie dodaje sam serii
na zastój i nie rozpoznaje przetrenowania, techniki ani stanu zdrowia z dziennika.
Nie wymaga codziennej ankiety, pomiaru każdej przerwy ani ponownego opisywania
całej historii. Rozszerzenia ponad ustalony zakres dostają osobne reguły przed kodowaniem.
