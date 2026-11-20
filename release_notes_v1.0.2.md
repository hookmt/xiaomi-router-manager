# Xiaomi Router Manager (XRM) v1.0.2

### 🇵🇱 Wydanie v1.0.2 - Szybka rezerwacja DHCP z listy urządzeń

Wydanie v1.0.2 wprowadza wygodną funkcjonalność szybkiego przypisywania stałych adresów IP (Static DHCP) bezpośrednio z listy aktywnych urządzeń w sieci:

#### 1. Szybka rezerwacja DHCP (`+ Rezerwuj`)
- W zakładce `Pulpit i Urządzenia -> Urządzenia w sieci` przy wszystkich aktywnych klientach nieposiadających jeszcze rezerwacji stałego IP wyświetlany jest zielony przycisk akcji **`+ Rezerwuj`**.
- Kliknięcie przycisku otwiera dedykowane okno dialogowe z automatycznie wypełnionymi danymi:
  - **Nazwa urządzenia:** bieżąca nazwa wykryta w sieci (z możliwością modyfikacji),
  - **Adres MAC:** sprzętowy adres MAC urządzenia (zablokowany do edycji - readonly),
  - **Adres IP:** aktualnie przydzielony dynamiczny adres IP (z możliwością zmiany),
  - **Przyciski:** Zapisz Rezerwację / Anuluj.
- Po zatwierdzeniu aplikacja natychmiast wywołuje API routera (`mac_bind`), rejestruje rezerwację, odświeża stan sieci i usuwa przycisk (urządzenie ma już stałą dzierżawę).

#### 2. Usprawnienia okna dodawania rezerwacji
- Dodano obsługę parametrów prefill dla formularza dodawania rezerwacji DHCP z dedykowanym nagłówkiem informacyjnym.
- Nowe klucze translacji symetrycznej w `i18n.py` (PL i EN).

---

### 🇬🇧 Release v1.0.2 - Quick DHCP Reservation from Active Devices

#### Key Enhancements:
- **Quick DHCP Reservation (`+ Reserve`):** Active network devices without static DHCP reservations now display a direct green `+ Reserve` action button in `Dashboard & devices -> Network Devices`.
- **Pre-populated Modal Dialog:** Clicking `+ Reserve` automatically fills in the device name, locks the hardware MAC address to read-only, and sets the current dynamic IP address.
- **Instant Binding:** Automatically applies `mac_bind` via the router API, refreshes the network list, and removes the button once the lease is permanently bound.
- **Standalone Windows Binary:** Pre-compiled single-file executable `Xiaomi_Router_Manager_v1.0.2.exe`.
