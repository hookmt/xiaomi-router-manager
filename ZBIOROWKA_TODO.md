# ZBIORÓWKA ZADAŃ I PLANÓW ROZWOJU

---

## Planowane funkcje do wydania v1.1.0 (Minor Release)

### 1. Rozszerzona diagnostyka i wykresy per-port LAN
- **Koncepcja:**
  - Dynamiczne wykresy transferu na żywo dla każdego portu fizycznego RJ45 (wykresy MB/s w czasie rzeczywistym).
  - Statystyki błędów CRC / pakietów utraconych na portach ethernetowych.
  - Wykrywanie podłączonych klientów per port fizyczny LAN (mapowanie MAC/IP do numeru gniazda).

### 2. Integracja z Home Assistant OS (HAOS / HACS)
- **Koncepcja:**
  - Wykorzystanie silnika `api.py` jako biblioteki bazowej dla `custom_components/xiaomi_router`.
  - Sensory: prędkości WAN upload/download, obciążenie CPU/RAM, temperatura, stan linku portów 2.5G.
  - Śledzenie obecności (Device Tracker) na podstawie powiązań Wi-Fi (2.4G/5G/LAN) i siły sygnału RSSI.
  - Przełączniki i akcje: sieć dla gości on/off, diody LED nocne on/off, optymalizacja kanałów, restart routera.
  - Korzyść poboczna: darmowy, natywny dostęp z poziomu aplikacji Home Assistant na smartfonach z Androidem i iOS!

### 3. Wersja linuksowa (AppImage / Standalone binary)
- **Koncepcja:**
  - Standaryzacja uruchamiania `customtkinter` pod środowiskami X11 i Wayland.
  - Przygotowanie automatycznego buildu AppImage / pojedynczego pliku binarnego dla dystrybucji Debian/Ubuntu/Fedora/Arch.

### 4. Dedykowana aplikacja mobilna (Android)
- **Koncepcja:**
  - Opcja A (preferowana): integracja HAOS i dedykowana karta Lovelace w aplikacji mobilnej HA.
  - Opcja B (niezależna): lekki interfejs webowy PWA (Responsive Web Dashboard) serwowany lokalnie przez router/mikroserwer.

---

## Archiwum wdrożeń

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
