# ZBIORÓWKA ZADAŃ I PLANÓW ROZWOJU

---

## Planowane wydanie (Zbiorówka: Linux, Android)

### 1. Wersja linuksowa (AppImage / Standalone binary)
- **Koncepcja:**
  - Standaryzacja uruchamiania `customtkinter` pod środowiskami X11 i Wayland.
  - Przygotowanie automatycznego buildu AppImage / pojedynczego pliku binarnego dla dystrybucji Debian/Ubuntu/Fedora/Arch.

### 2. Dedykowana aplikacja mobilna (Android)
- **Koncepcja:**
  - Opcja A (preferowana): integracja HAOS i dedykowana karta Lovelace w aplikacji mobilnej HA.
  - Opcja B (niezależna): lekki interfejs webowy PWA (Responsive Web Dashboard) serwowany lokalnie przez router/mikroserwer.

### 3. Rozszerzona diagnostyka i wykresy per-port LAN
- **Koncepcja:**
  - Dynamiczne wykresy transferu na żywo dla każdego portu fizycznego RJ45 (wykresy MB/s w czasie rzeczywistym).
  - Statystyki błędów CRC / pakietów utraconych na portach ethernetowych.
  - Wykrywanie podłączonych klientów per port fizyczny LAN (mapowanie MAC/IP do numeru gniazda).

### 4. Integracja z Home Assistant OS (HAOS / HACS)
- **Koncepcja:**
  - Wykorzystanie silnika `api.py` jako biblioteki bazowej dla `custom_components/xiaomi_router`.
  - Sensory: prędkości WAN upload/download, obciążenie CPU/RAM, temperatura, stan linku portów 2.5G.
  - Śledzenie obecności (Device Tracker) na podstawie powiązań Wi-Fi (2.4G/5G/LAN) i siły sygnału RSSI.
  - Przełączniki i akcje: sieć dla gości on/off, diody LED nocne on/off, optymalizacja kanałów, restart routera.
  - Korzyść poboczna: darmowy, natywny dostęp z poziomu aplikacji Home Assistant na smartfonach z Androidem i iOS!

### 5. Wybór strefy czasowej i regionu w aplikacji mobilnej oraz kreatorze (Zrealizowane w v1.0.6)
- **Status:** Zrealizowane 2026-11-22 w v1.0.6 (mobile PWA / Android APK oraz kreator Windows setup_wizard.py).

### 6. Region Wi-Fi (set_country_code) (Usunięte z UI w v1.0.7)
- **Status:** Zamknięte 2026-11-26 w v1.0.7. Test na żywym BE7000 potwierdził, że oryginalny firmware Xiaomi blokuje zmianę `CountryCode` przez HTTP API (`code: 1606`, fabryczna blokada w partycji `bdata`). Usunięto bezcelową edycję regionu Wi-Fi z UI Windows i Android (oraz Kreatora).

### 7. Prezentacja minimalnego obciążenia CPU (Zrealizowane w v1.0.7)
- **Status:** Zrealizowane 2026-11-26 w v1.0.7 (Windows i Android). Obciążenie `< 1.0%` wyświetlane jako `< 1%` z minimalnym paskiem 1%.

### 8. Selektor strefy czasowej w głównym oknie Windows Desktop (Zrealizowane w v1.0.7)
- **Status:** Zrealizowane 2026-11-26 w v1.0.7. Dodano listę strefy czasowej w zakładce Narzędzia i Konserwacja (`gui.py`) z zapisem i synchronizacją ze snapshotem routera.

### 9. Widoczny numer wersji w interfejsie mobilnym (XRM Mobile / Android APK) (Zrealizowane w v1.0.7)
- **Status:** Zrealizowane 2026-11-26 w v1.0.7. Dodano badge `v1.0.7` w nagłówku oraz stopkę `XRM Mobile v1.0.7` w drawerze nawigacyjnym.

---

## Archiwum wdrożeń

### v1.0.7 (Zrealizowane 2026-11-26)
- **Usunięcie nieaktywnej zmiany regionu Wi-Fi (`set_country_code`) z Windows i Android:** nowsze fabryczne firmware Xiaomi blokuje zmianę `CountryCode` w `bdata` (kod `1606`), więc edycję usunięto z Wi-Fi, System i Narzędzia oraz Kreatora.
- **Minimalne obciążenie CPU `< 1%` (Windows i Android):** brak mylącego `0%` w stanie bezczynności.
- **Selektor strefy czasowej w głównym oknie Windows (`gui.py`):** zakładka Narzędzia i Konserwacja, zsynchronizowana z odczytem z routera i synchronizacją czasu z PC.
- **Widoczny numer wersji w UI mobilnym (Android):** badge `v1.0.7` przy tytule w nagłówku oraz stopka `XRM Mobile v1.0.7` w menu nawigacyjnym.

### v1.0.6 (Zrealizowane 2026-11-22)
- **Selektor strefy czasowej i kodu regionu (Mobile & Windows):**
  - Mobile (app.js / index.html): nowa karta strefy czasowej (44 strefy IANA mapowane do POSIX), nowa karta regionu Wi-Fi (CE/FCC/CN) z odczytem i zapisem, integracja z kreatorem mobilnym oraz dynamiczna strefa przy synchronizacji czasu.
  - Windows (setup_wizard.py): rozszerzenie kreatora do 5 krokow, dedykowany krok 4 wyboru strefy i regionu, automatyczny zapis do routera w watku wykonawczym (`_apply_all`).
  - Podbicie wersji do v1.0.6 we wszystkich komponentach (Python, Gradle, Windows PE, PWA).

### v1.0.5 (Zrealizowane 2026-11-20)
- **Natywny klient Android i optymalizacja tabletowa (mobile/):**
  - Pelny projekt Android z Gradle, WebView i Android Keystore.
  - Płynny interfejs dla smartfonow i tabletow (OPPO Pad 3 Pro), drawer nawigacyjny.
  - Rozwijane menu CTkOptionMenu na Windowsie, dynamiczny ukad Smart Connect, dwukierunkowe sortowanie urzadzen i rezerwacji DHCP, konfiguracja DNS w DHCP.

### v1.0.2 (Zrealizowane 2026-11-20)
- **Szybka rezerwacja DHCP z listy urządzeń (Network Devices):**
  - Aktywny zielony przycisk `+ Rezerwuj` / `+ Reserve` przy urządzeniach na dzierżawie dynamicznej w `Dashboard & devices -> Network Devices`.
  - Dedykowane okno modalne z automatycznie uzupełnioną nazwą, zablokowanym do edycji adresem MAC oraz aktualnym adresem IP.
  - Natychmiastowe związanie przez API routera (`mac_bind`), odświeżenie danych i automatyczne usunięcie przycisku po nadaniu rezerwacji.
- **Kompilacja i wersjonowanie:**
  - Samodzielny plik binarny `Xiaomi_Router_Manager_v1.0.2.exe` skompilowany przez PyInstaller.
  - Uzupełniony słownik `i18n.py` (PL i EN) oraz zaktualizowany `version.py` i `file_version_info.txt`.

### v1.0.1 (Zrealizowane 2026-11-16)
- **Wizualizacja fizycznych portów routera (Physical Ports RJ45 4x 2.5 Gbps):**
  - Aktywna detekcja linku WAN/LAN z tablicy `lan_info.linkList` i `wan_info.link`.
  - Wizualne kontrolki stanu (`● Połączony (2.5G)` / `○ Gotowy (Auto MDI-X)`).
- **Naprawa szyfrowania Wi-Fi i zapobieganie rozłączaniu IoT:**
  - Prawidłowa interpretacja fabrycznego `psk2+ccmp` jako `WPA2/WPA3 Personal (sae-mixed)`.
  - Bezpieczne ostrzeżenie przed wymuszeniem czystego WPA3-SAE (ochrona urządzeń Tuya, ESP, gniazdek).
  - Oficjalne szerokości pasma (`40/20 MHz` oraz `160/80/40/20 MHz`).
- **Pasek postępu optymalizacji kanałów Wi-Fi:**
  - Animowany `CTkProgressBar` oraz dynamiczne powiadomienie o trwającym pomiarze zakłóceń RF.
- **Kompletna lokalizacja okien dialogowych (i18n):**
  - Wyczyszczenie wszystkich chińskich znaków z ustawień zaawansowanych Wi-Fi.
  - Dynamiczne etykiety suwaków (`Włączone`/`Wyłączone`, `Ukryta`/`Rozgłaszana`).
  - Spolszczenie i zangielszczenie okien: Dodawanie/edycja rezerwacji DHCP, Przekierowanie pojedynczego portu, Zakresy portów, Dodawanie DDNS, Dodawanie VPN, Zmiana hasła administratora, Karta dostępu Wi-Fi, Selektywne przywracanie konfiguracji.
  - Kreator pierwszej konfiguracji: pełna dwujęzyczność kroków 1-4.
- **Wersjonowanie pliku wykonywalnego:**
  - Nazwa pliku wydania zawiera wersję: `Xiaomi_Router_Manager_v1.0.1.exe`.

### v1.0.0 (Zrealizowane 2026-11-16)
- **Inicjalne wydanie:**
  - Pełna aplikacja desktopowa w CustomTkinter dla routerów Xiaomi BE6500 Pro / BE7000 / BE3600 / AX.
  - Pulpit, Topologia Mesh, DHCP, NAT, QoS, Narzędzia, Eksport Markdown.
  - SemVer v1.0.0, moduł `version.py` oraz `file_version_info.txt`.
