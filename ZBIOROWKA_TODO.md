# ZBIORÓWKA ZADAŃ I PLANÓW ROZWOJU

---

## Planowane funkcje do wydania v1.1.0 (Minor Release)

### 1. Wizualizacja fizycznych portów routera (Physical Ports RJ45 Status)
- **Koncepcja:**
  - Panel graficzny prezentujący fizyczne porty routera (np. 4x 2.5 Gbps dla Xiaomi BE6500 Pro / BE7000).
  - Wyświetlanie aktualnego stanu każdego portu:
    - Numer portu i typ (np. `1(2.5G)`, `2.5G RJ45`).
    - Wynegocjowana prędkość połączenia i stan wpięcia kabla:
      - `Connected (2.5G)` (zielona kontrolka).
      - `Ready (Auto MDI-X)` (szara kontrolka - port oczekujący / brak kabla).
      - Ewentualne niższe prędkości (1000M, 100M).
    - Przypisana rola i usługa:
      - `Primary Internet (WAN1)` (wyróżniona niebieska etykieta).
      - `Secondary Internet (WAN2)`.
      - `Local Network (LAN)`.
      - `Link Aggregation (LAG)`.
      - `IPTV / VoIP`.
      - `Gaming Port`.
- **Źródło danych w API routera:**
  - Endpoint `misystem/status` oraz `xqnetwork/ps_status` / `xqnetwork/port_service`.

---

## Archiwum wdrożeń

### v1.0.1 (Zrealizowane 2026-11-16)
- **Kompletna lokalizacja okien dialogowych (i18n):**
  - Spolszczenie i zangielszczenie okien: Dodawanie/edycja rezerwacji DHCP, Przekierowanie pojedynczego portu, Zakresy portów, Dodawanie DDNS, Dodawanie VPN, Zmiana hasła administratora, Karta dostępu Wi-Fi, Selektywne przywracanie konfiguracji.
  - Zaawansowane ustawienia Wi-Fi: Kompatybilność Wi-Fi 5, TWT, MU-MIMO, Mi Connect, Tryb cichy, Progi roamingu Mesh, Region regulacyjny, Moc nadawania.
  - Kreator pierwszej konfiguracji: pełna dwujęzyczność kroków 1-4.
  - Naprawienie etykiety "Czas routera:" w karcie narzędziowej.
- **Wersjonowanie pliku wykonywalnego:**
  - Nazwa pliku wydania zawiera wersję: `Xiaomi_Router_Manager_v1.0.1.exe`.

### v1.0.0 (Zrealizowane 2026-11-16)
- **Inicjalne wydanie:**
  - Pełna aplikacja desktopowa w CustomTkinter dla routerów Xiaomi BE6500 Pro / BE7000 / BE3600 / AX.
  - Pulpit, Topologia Mesh, DHCP, NAT, QoS, Narzędzia, Eksport Markdown.
  - SemVer v1.0.0, moduł `version.py` oraz `file_version_info.txt`.
