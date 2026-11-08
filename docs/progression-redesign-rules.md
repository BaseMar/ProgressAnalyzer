# Rekomendacje i progresja — zatwierdzone zasady v1.0

Data: 8 listopada 2026. Etap 1 zamknięty; poniższe reguły są wdrożone w nowym silniku.
Wersja obliczeń: `double-progression-2026-11-v1`.

## Cel i potwierdzone preferencje

Cel: hipertrofia i budowa siły. Użytkownik zapisuje RIR w seriach roboczych
i rozgrzewce, dopuszczając błąd oszacowania. Zwykle odpoczywa około 3 minut;
w końcowych izolacjach dobiera przerwy na wyczucie. Nie traktujemy tego jako
pomiaru długości każdej historycznej przerwy.

Różne ciężary wynikają z dobierania startu lub zmęczenia. Domyślnym modelem
nie jest zaplanowana piramida ani ciężka seria z odrębną progresją serii lżejszych.
Zapisany plan, faktyczne wyniki i rekomendacja pozostają oddzielnymi informacjami.

Uzgodniono odpowiedzi 1B, 2A, 3B, 4A, 5A, 6B, 7 — istniejące zapiski, 8B,
a następnie wyrównywanie ciężarów i parametry uzupełniające opisane poniżej.
Wszystkie konkretne progi są regułami aplikacji, a nie prawami fizjologii.

## Podwójna progresja z wyrównywaniem ciężarów

1. Przy pełnym wykonaniu w zakresie i z wymaganym zapasem próbujemy dodać
   jedno powtórzenie łącznie do pierwszej serii poniżej górnej granicy.
2. Wyrównanie lub podwyżka wymagają górnej granicy we wszystkich planowanych
   seriach na ich obecnych ciężarach, z RIR co najmniej docelowym.
3. Wystarcza jedno takie pełne porównywalne wykonanie. Nie wymagamy drugiego.
4. Jeśli ciężary są różne, najpierw podnosimy lżejsze serie do ustalonego ciężaru
   pierwszej serii. Cel powtórzeń w podnoszonych seriach wraca do minimum;
   serie już na ciężarze odniesienia zachowują cel na suficie.
5. Każdy wzrost, również wyrównywanie, ma limit 10% dotychczasowego ciężaru danej
   serii. Wybieramy największą liczbę rzeczywistych kroków mieszczącą się
   w limicie i nieprzekraczającą ciężaru odniesienia. Większe różnice pokonujemy etapami.
6. Dopiero pełny sukces na wspólnym ciężarze prowadzi do następnego wspólnego
   obciążenia: jeden dostępny krok, z minimum powtórzeń jako celem wszystkich serii.
7. Nie zwiększamy równocześnie ciężaru, docelowych powtórzeń i liczby serii.
   Zapas i technika mają pierwszeństwo przed próbą osiągnięcia liczby z karty.

Punkt odniesienia jest ustalonym ciężarem pierwszej serii roboczej, nie maksimum
znalezionym w całej historii ani późniejszej próbie kalibracji.
Gdy nie mieści się żaden dostępny krok, wyjaśniamy ograniczenie i pozostawiamy
decyzję o sprzęcie/zakresie/obciążeniu użytkownikowi. Nie wymyślamy mikroobciążenia.

## Macierz zwykłych decyzji

Przykładowy zakres 8–12, cel RIR 2, krok sprzętu 2,5 kg. Wiersze wzrostu
zakładają wymagany zapas we wszystkich seriach. Cele nie przewidują faktycznego wyniku.

| Zapisane wykonanie lub sytuacja | Następna decyzja |
| --- | --- |
| 60 × 10 / 60 × 9 / 60 × 8 | 60 × 11 / 60 × 9 / 60 × 8. |
| 60 × 12 / 55 × 11 / 55 × 12 | 60 × 12 / 55 × 12 / 55 × 12. |
| 60 × 12 / 55 × 12 / 55 × 12 | 60 × 12 / 60 × 8 / 60 × 8. |
| 60 × 12 / 60 × 12 / 55 × 12 | 60 × 12 / 60 × 12 / 60 × 8. |
| 60 × 12 / 50 × 12 / 50 × 12 | 60 × 12 / 55 × 8 / 55 × 8; etap pośredni z limitem 10%. |
| 60 × 12 / 60 × 8 / 60 × 8 | 60 × 12 / 60 × 9 / 60 × 8. |
| 60 × 12 / 60 × 12 / 60 × 12 | 62,5 × 8 / 62,5 × 8 / 62,5 × 8. |
| Jedna seria z RIR 1 powyżej minimum, cel RIR 2 | Bez podwyżki i bez automatycznej redukcji; zakres wykonujemy z wymaganym zapasem. |
| RIR 0 przy 12 powtórzeniach | Najpierw wcześniejsze zakończenie serii w zakresie; nie przeliczamy dokładnie „−2 powtórzenia = +2 RIR”. |
| RIR poniżej celu już przy 8 powtórzeniach | Po pierwszym takim wykonaniu zmniejszamy obciążenie tej serii o jeden dostępny krok, o ile pozostaje dodatnie. |
| Poniżej 8 powtórzeń, zapas nie większy niż docelowy | Korekta ciężaru tej serii po pierwszym wykonaniu. |
| Poniżej minimum, ale duży zapas | Najpierw wykonanie zakresu z zapasem, bez automatycznego dodawania ciężaru. |
| Niepowodzenie wyłącznie późniejszej serii | Korekta tej serii; nie obniżamy automatycznie startu całego ćwiczenia. |
| Brak dodatniego niższego ustawienia sprzętu | Ręczny dobór obciążenia problematycznej serii. |
| Przekroczenie sufitu części serii | Cele ograniczamy do sufitu; nie zachęcamy do dalszego przekraczania zakresu. |
| Brakujące serie lub RIR | Brak liczbowej podwyżki, konkretny opis brakujących danych. |
| Kilka osobnych zapisów pasuje do jednej pozycji planu | Potrzebne jawne przypisanie w Historii; nie wybieramy dowolnego sukcesu. |

## Kalibracja i porównywalność

Nieustalony start użytkownik wybiera ręcznie przy wglądzie w historię. Dotyczy to
braku bazy, rosnących ciężarów po pierwszej serii wskazujących na szukanie startu,
istotnie zmienionej kolejności, zakresu, RIR lub struktury serii. Pokazujemy sesje
źródłowe, ale nie przepisujemy późniejszej cięższej próby jako nowego startu.

Zwykła progresja już ustalonej bazy nadal może automatycznie zmieniać cele zgodnie
z regułami. Brak kalendarza bloków nie wyłącza zwykłych rekomendacji.

Porównania wymagają tego samego faktycznego ćwiczenia, pozycji/roli, jednostki,
struktury serii i celu. W bazie pozycja ma trwały klucz historii. Zmiana nazwy
treningu lub samego dnia tygodnia nie odcina historii. Powtórzone pozycje tego
samego ćwiczenia zachowują odrębne klucze. Starsze klucze inicjalizujemy na
podstawie planu, pozycji treningu i kolejnego wystąpienia ćwiczenia; nie jest to
odtworzenie nieistniejących historycznych oznaczeń roli.

Chronologia opiera się na faktycznych datach wykonania. Nie używamy wyników po
`as_of`, nie pomijamy ostatniego niepełnego wykonania na rzecz starszego sukcesu
i nie uznajemy braku powiązania treningu za dowód pominięcia treningu.
Zamienniki wymagają jawnego wyboru i własnego kroku sprzętu. Filtr Analysis
nie zmienia przyszłego celu. Różne konwencje kilogramów nie są zamienne.

## RIR, przeznaczenie serii i przerwy

RIR pozostaje oszacowaniem. Nie poprawiamy go automatycznie i nie zakładamy
uniwersalnego błędu ±1. RIR 0 jest poprawną obserwacją; brak RIR pozostaje nieznany.
Gotowość do podwyżki i potrzeba redukcji są odrębnymi decyzjami.

Jawne oznaczenia i korekty przeznaczenia mają pierwszeństwo. Importer obsługuje
`warm-up`/`rozgrzewka` oraz `working`/`robocze`. Dla nieoznaczonej historii użytkownik
wybrał zachowanie istniejącej heurystyki: RIR 0–3 jako kandydat roboczy, 4–5 jako
lekka seria, >5 jako niski wysiłek. Rozgrzewka wnioskowana dodatkowo poprzedza serie
robocze i ma mniejsze obciążenie w tej samej konwencji. Brak RIR jest nieznany.
Źródło wnioskowania jest widoczne i nie nadpisuje surowych zapisów.

Jawna seria robocza z RIR 4 pozostaje roboczą. Jawna rozgrzewka z RIR 2 pozostaje
rozgrzewką. Samo zapisanie RIR nie określa przeznaczenia.

Nieznana długość odpoczynku nie blokuje całego systemu, ale ogranicza ocenę
przyczyny różnic. Nie rozpoznajemy skrócenia przerwy ani utraty siły z samego
spadku powtórzeń. Pomiar każdej przerwy nie jest obowiązkowym polem wejściowym.

## Zastój i dłuższa przerwa

Możliwy zastój to cztery pełne, porównywalne wykonania na tych samych obciążeniach
z wymaganym zapasem, bez wzrostu sumy powtórzeń ani potwierdzonej poprawy zapasu.
Wykonania muszą pochodzić z odrębnych dni, z odstępami nie większymi niż 21 dni.
Pełny sufit gotowy do podwyżki nie jest oznaczany jako zastój.

Potwierdzenie poprawy RIR w tym oknie wymaga dwóch kolejnych wykonań z takimi samymi
powtórzeniami per seria jak w bazie, zapasem nie mniejszym w żadnej serii i większym
w przynajmniej jednej. Nie stosujemy średniej maskującej pogorszenie części serii.
Pojedynczy wyższy odczyt nie wystarcza. Ocena zastoju jest dodatkową obserwacją;
nie dodaje serii, nie zmienia ćwiczeń i nie diagnozuje przetrenowania.

Ponad 21 dni od ostatniego porównywalnego wykonania oznacza ręczne ponowne
ustalenie startu, bez założenia określonego procentu utraty siły.

## Automatyczny deload i powrót

Deload przypada na ostatni tydzień ustawionego cyklu. Zachowujemy wszystkie serie
i faktycznie zapisane powtórzenia ostatniego porównywalnego zwykłego treningu.
Każdy ciężar obniżamy o co najmniej 30% w pełnych krokach sprzętu, do pierwszego
dostępnego poziomu dającego redukcję nie większą niż 40%. Brak takiego dodatniego
ustawienia oznacza ręczny dobór. Cel RIR wynosi 3–4, a faktyczny zapas użytkownik
zapisuje po serii; nie wyliczamy go z procentu obniżenia ciężaru.

Przykład: zwykłe 60 kg × 10/10/10, krok 2,5 kg → deload 40 kg × 10/10/10,
cel RIR 3–4. Zapisane 12/10/9 pozostaje 12/10/9, zamiast wracać do minimum zakresu.

Deload nie jest zwykłym sukcesem ani regresem. Nie kumuluje obniżek z kolejnych
lżejszych sesji. Przesunięta sesja deloadu nadal jest deloadem; zwykły trening
wykonany w okresie deloadu również nie stanowi potwierdzenia zwykłej progresji.
Po deloadzie wracamy do ostatniej zwykłej bazy z poprzedniego cyklu, bez natychmiastowej
podwyżki. Pierwsze zwykłe wykonanie weryfikuje bazę. Nadal obowiązują kompletność,
porównywalność i limit historii. Nowa wersja planu zachowuje kalendarz, o ile
użytkownik świadomie go nie zmieni.

## Czas, masa ciała i granice automatyki

- Czas: +5 s łącznie do pierwszej serii poniżej sufitu, z ograniczeniem do maksimum
  zakresu. Nie wymagamy RIR opartego na powtórzeniach. Po suficie nowy zakres lub
  obciążenie jest dobierane ręcznie. Deload czasu/ustawień również jest ręczny.
- Masa ciała/asysta: podpowiadamy powtórzenia, ale dodatkowy ciężar lub asystę
  wybiera użytkownik. Mniejsza asysta zwiększa trudność. Nie zakładamy przyszłej
  masy ciała ani nie przeliczamy jej na kilogramy siły mięśni.
- Dla starszych wpisów podciągania, dipów i podobnych ćwiczeń o nieznanej konwencji
  pokazujemy cel powtórzeń/czasu z ręcznym ciężarem. Rozpoznanie typu ćwiczenia
  ogranicza automatykę, ale nie zmienia znaczenia zapisanych kilogramów.
- Nieznana masa/asysta w jawnej konwencji ogranicza porównania obciążenia.
- Serie jednostronne wymagają konsekwentnej konwencji „na stronę”. Model nie ma
  oddzielnego pomiaru strony; nie potwierdza niezapisanej drugiej strony.
- Drop sety, rest-pause i wymuszone powtórzenia wymagają osobnego wariantu/ręcznego
  doboru. Nie rozpoznajemy tych technik z samych kilogramów i powtórzeń.
- System nie ocenia techniki, bólu, choroby ani urazu z dziennika i nie jest
  algorytmem rehabilitacji lub diagnozy zmęczenia.

## Wspólny wynik i wdrożenie

Każda rekomendacja zawiera działanie, cele per seria, cel zapasu, główny powód,
sesje źródłowe, ograniczenia oraz wersję zasad. Overview, Analysis i notatka
treningowa używają tego samego wyniku. Cele nie są zapisanym wykonaniem.

Priorytet: deload/powrót → walidacja → kalibracja ręczna → korekta niepowodzenia
przy minimum → niedostateczny zapas → wyrównanie → nowy wspólny ciężar → dodatkowe
powtórzenie/czas → utrzymanie. Zastój jest dodatkową obserwacją.

Zatwierdzona [konfiguracja 36 pozycji planu](training-plan-recommendation-configuration.md)
została zapisana jako wersja 6 (ID 15) od 10 listopada 2026. Historyczne wersje
i wykonania pozostają zachowane. Etapy i odbiór opisuje
[plan wdrożenia](recommendation-system-implementation-plan.md).

## Podstawa źródłowa a wybrane reguły aplikacji

| Źródło | Wniosek i ograniczenie |
| --- | --- |
| [ACSM 2026](https://pmc.ncbi.nlm.nih.gov/articles/PMC12965823/) | Cel i indywidualizacja mają znaczenie; upadek nie jest konieczny. Nie wyznacza dokładnego algorytmu ani optymalnego RIR dla każdego ćwiczenia. |
| [ACSM 2009](https://pubmed.ncbi.nlm.nih.gov/19204579/) | Opisuje podwyżki 2–10% po przekraczaniu docelowych powtórzeń. Nie jest źródłem wybranej przez użytkownika reguły jednego sukcesu ani wyrównywania serii. |
| [Plotkin i wsp. 2022](https://pmc.ncbi.nlm.nih.gov/articles/PMC9528903/) | Badanie wspiera progresję powtórzeń i obciążenia; nie dowodzi przewagi naszego konkretnego schematu. |
| [Russo i wsp., online 2025](https://doi.org/10.1080/10833196.2025.2564026) | Trafność RIR zależy od warunków; brak uniwersalnej tolerancji ±1. |
| [Bell i wsp. 2023](https://pmc.ncbi.nlm.nih.gov/articles/PMC10511399/) | Konsensus wspiera indywidualizację deloadu. Zachowanie serii i redukcja 30–40% są świadomym wyborem użytkownika, a nie obowiązkowym schematem z tego źródła. |
| [Senna i wsp. 2011](https://pubmed.ncbi.nlm.nih.gov/21993029/) | Długość odpoczynku wpływała na powtórzenia; bez pomiaru nie ustalimy przyczyny konkretnego spadku. |
| [Singer i wsp. 2024](https://www.frontiersin.org/journals/sports-and-active-living/articles/10.3389/fspor.2024.1429789/full) | Hipertrofia występuje przy różnych przerwach; nie ustala jednej dokładnej długości dla wszystkich ćwiczeń. |
