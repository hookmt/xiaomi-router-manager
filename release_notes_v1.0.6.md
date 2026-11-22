# Xiaomi Router Manager (XRM) v1.0.6

### Wydanie v1.0.6 - Selektor strefy czasowej (Timezone POSIX) oraz regionu regulacyjnego Wi-Fi (Country Code / RegDomain)

Wydanie v1.0.6 wprowadza pelna kontrole nad strefa czasowa routera oraz kodem regionu regulacyjnego Wi-Fi w aplikacji mobilnej (Android APK / PWA) oraz w kreatorze szybkiej konfiguracji na Windows Desktop.

#### 1. Klient mobilny i PWA (Android / mobile/www)
- **Karta "Strefa czasowa routera":**
  - Pelny selektor 44 stref czasowych (format IANA z mapowaniem do standardu POSIX wymaganego przez system OpenWrt/Xiaomi).
  - Mozliwosc niezaleznego zapisu strefy czasowej routera bez koniecznosci zmiany biezacej godziny.
  - Funkcja synchronizacji czasu urzadzenia (`btn-sync-time`) dynamicznie uwzglednia wybrana z listy strefe czasowa (zamiast dotychczasowej stalej Europe/Warsaw).
- **Karta "Region regulacyjny Wi-Fi (RegDomain)":**
  - Wybor kodu kraju (Polska/Europa CE, Niemcy, Francja, UK, USA FCC, Chiny CN, Japonia i inne).
  - Bezposredni odczyt aktualnego kodu z routera przez API `xqsystem/country_code`.
  - Zapis kodu przez API `xqsystem/set_country_code` wraz z ostrzezeniem o wplywie na dozwolone kanaly Wi-Fi, limity mocy TX oraz mozliwej koniecznosci restartu routera.
- **Kreator konfiguracji (Quick Setup Wizard):**
  - Odblokowany i aktywny przycisk zastosowania ustawien.
  - Zintegrowane pola wyboru strefy czasowej i regionu regulacyjnego przed uruchomieniem routera.

#### 2. Kreator Windows Desktop (setup_wizard.py)
- **Rozszerzenie procedury do 5 krokow:**
  - Dodany dedykowany krok 4: wybor strefy czasowej routera oraz kodu regionu Wi-Fi.
  - Krok 5: pelne podsumowanie konfiguracji z uwzglednieniem strefy czasowej oraz kodu kraju.
- **Automatyzacja zapisu w watku wykonawczym:**
  - Metoda `_apply_all` przesyla do routera zmapowany lancuch POSIX przez `misystem/set_sys_time` oraz kod kraju przez `xqsystem/set_country_code`.
  - Pelna obsluga wielojezycznosci (i18n: polski i angielski) dla nowych odznak i etykiet kreatora.
