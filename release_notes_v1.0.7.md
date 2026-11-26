# Xiaomi Router Manager (XRM) v1.0.7

### Wydanie v1.0.7 - Strefa czasowa w oknie głównym Windows, CPU < 1%, znacznik wersji Android i usunięcie zablokowanej zmiany regionu Wi-Fi

Wydanie v1.0.7 wprowadza usprawnienia po testach terenowych na routerze Xiaomi BE7000 dla wersji Windows Desktop (`.exe`) oraz mobilnej (Android APK / PWA).

#### 1. Selektor strefy czasowej w głównym oknie Windows (`gui.py`)
- W zakładce **System i Narzędzia -> Narzędzia i Konserwacja** (tuż pod synchronizacją czasu z PC) dodano rozwijaną listę **Strefy czasowej** z przyciskiem **Zapisz** (pełna tabela IANA -> POSIX).
- Przycisk synchronizacji czasu z PC korzysta teraz z wybranej strefy czasowej zamiast wartości wpisanej na sztywno, a selektor synchronizuje się automatycznie przy odświeżaniu danych z routera.

#### 2. Prezentacja minimalnego obciążenia CPU (`< 1%`) - Windows i Android
- Wskazanie obciążenia procesora poniżej `1.0%` w stanie bezczynności jest teraz formatowane jako `< 1%` (z minimalnym wypełnieniem paska 1%) zamiast `0%` / `0.0%`.

#### 3. Usprawnienia aplikacji mobilnej (Android APK / PWA)
- Dodano dyskretny znacznik `v1.0.7` obok tytułu aplikacji w górnym nagłówku oraz stopkę `XRM Mobile v1.0.7` na dole menu nawigacyjnego (drawera).
- Wyłączono pamięć podręczną zasobów WebView (`LOAD_NO_CACHE` + `clearCache`), dzięki czemu aktualizacje APK „na starą wersję” od razu ładują nowe UI bez konieczności odinstalowywania aplikacji.
- Przeniesiono przycisk `+ Nowa rezerwacja` bezpośrednio do sekcji **Statyczne Rezerwacje Adresów IP (Static DHCP)** i przebudowano listę rezerwacji z tabeli na karty w dwóch wierszach (bez przewijania na boki na telefonie).
- Dodano fallback na `xqnetwork/wifi_check` oraz wydłużono timeout odczytu do 30 s dla optymalizacji kanałów Wi-Fi (zgodnie z wersją Windows).

#### 4. Usunięcie nieaktywnej zmiany regionu Wi-Fi (`set_country_code`) - Windows i Android
- Usunięto edycję kodu regionu Wi-Fi z zakładek Wi-Fi, System i Narzędzia oraz Kreatora w obu aplikacjach, ponieważ nowsze fabryczne firmware Xiaomi (m.in. seria BE) blokuje zmianę `CountryCode` w partycji `bdata` i odrzuca żądania HTTP API (kod `1606`). Aktualny kod regionu routera pozostaje widoczny do odczytu przy wersji ROM na Pulpicie.
