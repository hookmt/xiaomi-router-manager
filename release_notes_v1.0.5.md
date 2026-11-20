# Xiaomi Router Manager (XRM) v1.0.5

### 🇵🇱 Wydanie v1.0.5 - Ujednolicony Klient Android (Smartfony i Tablety) oraz Nowoczesne Rozwijane Listy w Aplikacji Windows

Wydanie v1.0.5 to duża aktualizacja integrująca pełnego, natywnego klienta Android (smartfony i tablety) z odświeżoną wersją Windows Desktop. Cały ekosystem XRM zyskał ujednolicone kontrolki wyboru (rozwijane listy dropdown), zoptymalizowany układ Smart Connect Wi-Fi oraz dwukierunkowe sortowanie urządzeń i rezerwacji.

#### 1. Ujednolicony klient mobilny i tabletowy (Android APK & PWA)
- **Architektura zgodna z wersją desktopową:** bezpośrednia komunikacja HTTP z routerem Xiaomi (192.168.31.1), działanie w 100% offline, brak zależności od chmury.
- **Bezpieczeństwo poświadczeń:** opcjonalne bezpieczne przechowywanie hasła administratora z wykorzystaniem sprzętowego Android Keystore.
- **Adaptacyjny interfejs (Smart Layout):**
  - **Tryb telefonu (pion):** dolny pasek nawigacyjny, jednokolumnowy układ pod kciuk.
  - **Tryb tabletu (poziom):** lewy boczny drawer nawigacyjny, wielokolumnowy pulpit.
- **Adaptacyjny widok Wi-Fi (Smart Connect):**
  - Gdy funkcja Smart Connect jest aktywna: górna wspólna karta dla wspólnego SSID, hasła i szyfrowania. Poniżej dedykowane karty parametrów radiowych pasm 2.4 GHz oraz 5 GHz.
  - Gdy funkcja Smart Connect jest wyłączona: pełne, niezależne formularze konfiguracji dla obu pasm.
- **Naprawione formatowanie parametrów routera:**
  - Prawidłowe parsowanie pamięci RAM (np. 1024MB na bajty i formatowanie do czytelnych jednostek MB / GB).
  - Poprawne formatowanie znacznika czasu systemowego routera.
- **Zarządzanie siecią i zaawansowane narzędzia:**
  - Pełna obsługa NAT (przekierowania pojedyncze, zakresy portów, DMZ, stan UPnP).
  - Statyczna rezerwacja DHCP z zielonym wskaźnikiem statusu.
  - Szybkie sortowanie urządzeń (numerycznie po IPv4, alfabetycznie po nazwie, po stanie aktywności).
  - Podwójny system kopii: pobieranie fabrycznej kopii binarnej Xiaomi oraz selektywny eksport/import JSON.
  - Zero zakodowanych na stałe identyfikatorów urządzeń czy adresów fizycznych w kodzie źródłowym.

#### 2. Udoskonalenia w aplikacji Windows Desktop
- **Nowoczesne rozwijane menu (CTkOptionMenu):**
  - **Tryb WAN:** zastąpienie przycisków segmentowych czytelną listą wyboru (PPPoE, DHCP, Statyczny IP) z dynamicznym odsłanianiem właściwych pól formularza.
  - **Zaawansowane role portów 2.5G:** rozwijana lista wyboru trybów (Dual WAN, Agregacja LAN - LAG, Telewizja IP - IPTV, Port Gry - Gaming VIP).
  - **Moduły zaawansowane:** rozwijane menu wyboru podwidoków QoS, DDNS oraz VPN.
- **Adaptacyjny układ Wi-Fi:** zsynchronizowany z wersją Android, automatycznie dostosowujący widok przy włączeniu/wyłączeniu Smart Connect.
- **Dwukierunkowe sortowanie listy urządzeń i rezerwacji DHCP:**
  - Sortowanie po adresie IPv4 (rosnąco / malejąco), nazwie urządzenia (A-Z / Z-A), czasie połączenia oraz statusie aktywności.
  - Wskaźnik "● Zarezerwowany" oraz przyciski szybkiej akcji (+ Rezerwuj IP, Edytuj, Usuń).
- **Formatowanie RAM i higiena kodu:** bezpieczne parsowanie jednostek pamięci z API routera oraz usunięcie awaryjnych identyfikatorów MAC.

---

### 🇬🇧 Release v1.0.5 - Unified Android Client (Phone & Tablet) & Modernized Desktop UI Dropdowns

Release v1.0.5 brings unified mobile and desktop parity, introducing the complete Android client alongside streamlined dropdown selection controls on Windows Desktop.

#### Key Enhancements:
- **Unified Android Client (Android APK & PWA):**
  - Direct offline HTTP communication with Xiaomi routers at 192.168.31.1.
  - Hardware-backed credential security via Android Keystore.
  - Responsive layouts for phones (bottom navigation) and tablets (left navigation drawer).
  - Adaptive Smart Connect Wi-Fi view (unified top card when enabled, independent dual-band cards when disabled).
  - Accurate RAM unit parsing and system timestamp formatting.
  - NAT controls (port forwarding, port ranges, DMZ, UPnP status), static DHCP leases, and QoS/DDNS/VPN.
  - Dual backup mechanism: factory Xiaomi binary download + granular JSON backup and selective restore.
  - Clean codebase with zero hardcoded hardware MAC identifiers.
- **Windows Desktop Improvements:**
  - Upgraded configuration controls: segmented buttons replaced with sleek dropdown menus (`CTkOptionMenu`) for WAN modes, 2.5G port roles, and QoS/DDNS/VPN tabs.
  - Adaptive Smart Connect Wi-Fi layout matching mobile client ergonomics.
  - Two-way numeric IPv4 and alphabetical sorting for Network Devices and DHCP reservations.
  - Visual static lease badges ("● Reserved") with inline quick action buttons (+ Reserve IP, Edit, Delete).
  - Bulletproof memory capacity parsing from router status.
- **Distribution Packages:**
  - Windows single-file executable: `Xiaomi_Router_Manager_v1.0.5.exe`
  - Android package: `Xiaomi_Router_Manager_v1.0.5.apk`
