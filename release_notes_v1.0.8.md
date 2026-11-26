# Xiaomi Router Manager (XRM) v1.0.8

### Wydanie v1.0.8 - Prawdziwy skan i optymalizacja kanałów Wi-Fi, stały klucz podpisu APK oraz poprawki układu telefonu (pion/poziom)

Wydanie v1.0.8 wprowadza prawdziwą optymalizację kanałów Wi-Fi na BE7000 oraz komplet poprawek mobilnych po testach w pionie i poziomie na telefonie.

#### 1. Krytyczna poprawka mapowania szyfrowania Wi-Fi na BE7000 (Windows i Android)
- Dopasowano kody szyfrowania wysyłane do API routera 1:1 do oficjalnych wartości MiWiFi BE7000: `psk2+ccmp` (WPA2/WPA3 Personal Mixed), `ccmp` (WPA3 Personal), `psk2` (WPA2 Personal), `mixed-psk` (WPA/WPA2 Mixed), `none` (Otwarta).
- Poprzednio wysyłanie standardowego `sae-mixed` przełączało BE7000 w tryb czystego WPA3 (`超强加密`), co mogło rozłączać starsze urządzenia (np. karty Wi-Fi w NAS i sprzęt IoT).
- Optymalizacja kanałów Wi-Fi zachowuje teraz bezpośrednio surowy kod szyfrowania odczytany z bieżącej migawki routera, dzięki czemu zmiana kanału nigdy nie modyfikuje szyfrowania.

#### 2. Prawdziwy skan eteru i optymalizacja kanałów Wi-Fi (Windows i Android)
- Zastąpiono nieistniejące na BE7000 endpointy (`wifi_channel_optimize` / `wifi_check`, zwracające HTTP 404) oficjalnym mechanizmem routera: `api/misystem/channel_scan_start` + odczyt `api/misystem/channel_scan_result` aż do zakończenia skanu (`status == 0`).
- Aplikacja prezentuje realny wynik pomiaru z routera (bieżący kanał i wynik vs zalecany kanał) i pyta o potwierdzenie przed jego ustawieniem (z pełnym zachowaniem SSID, hasła, szyfrowania i mocy TX).

#### 3. Stały klucz podpisu Android APK (GitHub Secrets)
- Skonfigurowano stały certyfikat podpisu release (PKCS12) w `build.gradle` i GitHub Actions. Po zainstalowaniu `v1.0.8` każda kolejna wersja (`v1.0.9+`) będzie instalować się jako aktualizacja „na starą” bez odinstalowywania i utraty zapamiętanego hasła.
- Uwaga: przejście z `v1.0.7` (podpisanego jednorazowym kluczem debug) na `v1.0.8` wymaga ostatni raz odinstalowania starej paczki.

#### 4. Poprawki interfejsu mobilnego (pion i poziom na telefonie)
- **Przewijane menu boczne (drawer) w poziomie:** poprawiony układ Flexbox (`flex-shrink: 0`, `min-height: 0`, `100dvh`), dzięki czemu wszystkie pozycje są dostępne również w układzie poziomym.
- **Spłaszczone `System i Narzędzia`:** bezpośredni przycisk w menu zamiast zbędnej grupy z jedną podpozycją.
- **QoS na wąskim ekranie:** siatka 2x2 dla profili priorytetu (wszystkie 4 profile, w tym `Streaming`, w pełni widoczne).
- **Porty 2.5G i przełączniki:** poprawiony selektor `Wybierz funkcję` (brak wystawania poza kartę) oraz ukryty natywny checkbox w `.toggle-switch` (LAG, Dual WAN, IPTV, Gaming, LED).
- **Nagłówek i formularze 2-kolumnowe w poziomie:** zawijanie górnej belki do `960px` (brak ucinania `PL/EN`) oraz globalne `minmax(0, 1fr)` / `min-width: 0` w `.form-row-2` (brak ucinania pól w NAT/LAN/Portach).
