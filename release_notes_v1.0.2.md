# Xiaomi Router Manager (XRM) v1.0.2

### 🇵🇱 Wydanie v1.0.2 - Szybka rezerwacja DHCP oraz Klient Mobilny i Tabletowy (Android APK)

Wydanie v1.0.2 wprowadza dwie kluczowe nowości: szybkie przypisywanie stałych adresów IP (Static DHCP) bezpośrednio z listy urządzeń oraz w pełni adaptacyjną aplikację na smartfony i tablety (Android APK & PWA).

#### 1. Szybka rezerwacja DHCP (`+ Rezerwuj` / `+ Reserve`)
- W zakładce `Pulpit i Urządzenia -> Urządzenia w sieci` przy wszystkich aktywnych klientach nieposiadających jeszcze rezerwacji stałego IP wyświetlany jest zielony przycisk akcji **`+ Rezerwuj`**.
- Kliknięcie przycisku otwiera dedykowane okno dialogowe z automatycznie wypełnionymi danymi:
  - **Nazwa urządzenia:** bieżąca nazwa wykryta w sieci (z możliwością modyfikacji),
  - **Adres MAC:** sprzętowy adres MAC urządzenia (zablokowany do edycji - readonly),
  - **Adres IP:** aktualnie przydzielony dynamiczny adres IP (z możliwością zmiany),
  - **Przyciski:** Zapisz Rezerwację / Anuluj.
- Po zatwierdzeniu aplikacja natychmiast wywołuje API routera (`mac_bind`), rejestruje rezerwację, odświeża stan sieci i usuwa przycisk (urządzenie ma już stałą dzierżawę).

#### 2. Nowa aplikacja mobilna i tabletowa (Android APK & Offline Web)
- **Adaptacyjny interfejs (Smart Layout):**
  - **Tryb telefonu (pion):** dolny pasek nawigacyjny, jednokolumnowy układ pod kciuk, szybkie akcje.
  - **Tryb tabletu (poziom):** lewy boczny panel nawigacyjny, wielokolumnowy pulpit o wysokiej czytelności, komfort zbliżony do wersji na komputer.
  - **Trójpozycyjny przełącznik w nagłówku:** `[Auto]` (automatyczna zmiana wg orientacji ekranu), `[Telefon]`, `[Tablet]`.
- **Działanie 100% offline:** aplikacja łączy się bezpośrednio z adresem `192.168.31.1` routera Xiaomi (np. świeżo zresetowanego, rozgłaszającego otwartą sieć `Xiaomi_XXXX`), bez konieczności połączenia ze światem czy chmurą.
- **Kreator pierwszej konfiguracji (Setup Wizard):** błyskawiczna konfiguracja hasła admina, sieci Wi-Fi i trybu WAN bezpośrednio ze smartfona.
- **Dystrybucja:** samodzielna paczka instalacyjna `Xiaomi_Router_Manager_v1.0.2.apk`.

---

### 🇬🇧 Release v1.0.2 - Quick DHCP Reservation & Adaptive Mobile/Tablet App (Android APK)

#### Key Enhancements:
- **Quick DHCP Reservation (`+ Reserve`):** Active network devices without static DHCP reservations now display a direct green `+ Reserve` action button in `Network Devices`.
- **Pre-populated Modal Dialog:** Automatically fills in device name, locks the hardware MAC to read-only, and pre-fills current dynamic IP.
- **New Adaptive Mobile & Tablet App (Android APK):**
  - **Phone Mode (Portrait):** Bottom navigation, single-column thumb-friendly layout.
  - **Tablet Mode (Landscape):** Left navigation sidebar, multi-column dashboard mirroring desktop UX without black bars.
  - **Manual Layout Switcher:** Header toggle for `[Auto]`, `[Phone]`, and `[Tablet]`.
  - **100% Offline Capability:** Works straight out of the box with factory-reset routers at `192.168.31.1`.
- **Distribution Packages:** Single-file desktop executable `Xiaomi_Router_Manager_v1.0.2.exe` and Android installation package `Xiaomi_Router_Manager_v1.0.2.apk`.
