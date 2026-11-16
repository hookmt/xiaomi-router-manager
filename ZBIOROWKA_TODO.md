# ZBIORÓWKA ZADAŃ I PLANÓW ROZWOJU

---

## Planowane funkcje do wydania v1.1.0 (Minor Release)

### 1. Rozszerzona diagnostyka i wykresy per-port LAN
- **Koncepcja:**
  - Dynamiczne wykresy transferu na żywo dla każdego portu fizycznego RJ45 (wykresy MB/s w czasie rzeczywistym).
  - Statystyki błędów CRC / pakietów utraconych na portach ethernetowych.
  - Wykrywanie podłączonych klientów per port fizyczny LAN (mapowanie MAC/IP do numeru gniazda).

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
