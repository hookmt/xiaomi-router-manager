# Xiaomi Router Manager (XRM) v1.0.9

### Wydanie v1.0.9 - Pełna obsługa inicjalizacji fabrycznej (inited=0), poprawne strefy czasowe POST + index, pełny reset fabryczny (?format=1) i poprawki Mesh/WAN (Windows i Android)

Wydanie v1.0.9 domyka wszystkie błędy wykryte podczas pełnych testów na żywo na routerach **Xiaomi BE7000 (RC06)** oraz **Xiaomi BE6500 (RN02)** w konfiguracji standalone oraz 2-węzłowej sieci Mesh.

#### 1. Pełna obsługa fabrycznej inicjalizacji routera (`inited == 0`, Windows i Android)
- Wdrożono oficjalny protokół pierwszego uruchomienia Xiaomi (`xqsystem/login` z `init=1`, `xqnetwork/set_wan_new`, `misystem/set_router_normal` z szyfrowaniem AES-CBC PKCS7 + SHA-256).
- Nowy lub fabrycznie zresetowany router można skonfigurować od zera bezpośrednio z Kreatora XRM po polsku lub angielsku, bez używania chińskiego panelu w przeglądarce.
- Naprawiono kroki 4 i 5 Kreatora Windows (strefa czasowa, statyczne IP, PPPoE, przełącznik Smart Connect, usunięto nieistniejącą opcję MLO).

#### 2. Oficjalny mechanizm zmiany strefy czasowej (`POST misystem/set_sys_time`, Windows i Android)
- Zmiana strefy czasowej wysyła teraz `POST` z parametrami `timezone` oraz oficjalnym indeksem `index` z tabeli V2 Xiaomi (`2.54` dla Polski CET/CEST, `2.84` dla Chin CST-8 itd.), a synchronizacja zegara osobny `POST` z `time`.
- Zmiany są natychmiast widoczne i spójne z oficjalnym panelem Web UI Xiaomi.

#### 3. Pełny reset fabryczny (`?format=1`) i czerwone okna bezpieczeństwa (Windows i Android)
- Reset fabryczny wywołuje teraz `xqsystem/reset?format=1` (zweryfikowane na żywo na BE6500: pełny powrót do `inited=0` i domyślnego hasła `admin`).
- Dodano czerwony modal potwierdzenia z wyraźną rolą routera (`MASTER (MESH)` / `MASTER / STANDALONE` / `SATELITA / AP`), modelem, nazwą i IP przed wpisaniem `RESET`.
- Wyróżniono na czerwono przycisk zapisu adresu IP bramy LAN.

#### 4. Poprawki telemetrii WAN, Mesh i interfejsu (Windows i Android)
- **Prędkość wysyłania WAN:** naprawiono błąd odczytu skumulowanego licznika bajtów `wan.upload` zamiast bieżącej prędkości `wan.upspeed`.
- **Serwery DNS przy WAN DHCP:** dodano odczyt `dnsAddrs` / `dnsAddrs1` / `dnsAddrs2`.
- **Android Dashboard:** uzupełniono żywe odczyty `Diody LED` oraz `Tryb sieci` (Master Mesh / Standalone / Satelita AP) na dolnej belce pulpitu.
- **Topologia Mesh i lista urządzeń:** naprawiono ochronę satelitów (`isap > 0` jako `[Stacja Admina / AP]`), dodano fallback MAC dla Mastera i Satelitów, listę podłączonych klientów przy każdym węźle oraz oznaczenie węzła Mesh na kartach urządzeń w Androidzie.
- **Czyste przełączanie routerów i UI:** czyszczenie stanu przy rozłączeniu, oczyszczona nazwa `Xiaomi路由器` -> `Xiaomi Router `, kompaktowy uptime na liście urządzeń, poszerzone listy wyboru i brak sztywnego wpisywania MTU `1472`.
