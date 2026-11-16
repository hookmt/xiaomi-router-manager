# Xiaomi Router Manager (XRM) v1.0.1

### 🇵🇱 Wydanie v1.0.1 - Pełna lokalizacja, fizyczne porty 2.5G, naprawa szyfrowania Wi-Fi i wskaźnik optymalizacji

Wydanie v1.0.1 przynosi kluczowe usprawnienia wykryte podczas testów poligonowych na routerze **Xiaomi BE7000 / BE6500 Pro**:

#### 1. Wizualizacja fizycznych portów routera (4x 2.5 Gbps)
- Aktywna detekcja linku WAN oraz LAN w czasie rzeczywistym (odczyt ze struktur `lan_info.linkList` oraz `wan_info.link`).
- Podłączone kable sieciowe (WAN1, LAN2, LAN4) sygnalizowane są zielonym wskaźnikiem `● Połączony (2.5G)` / `● Connected (2.5G)`.
- Wolne gniazda (LAN3) prezentują stan gotowości `○ Gotowy (Auto MDI-X)` / `○ Ready (Auto MDI-X)`.

#### 2. Naprawa szyfrowania Wi-Fi i ochrona urządzeń IoT (Tuya / ESP)
- Fabryczny tryb Xiaomi `强混合加密(WPA3/WPA2个人版)` (`"encryption": "psk2+ccmp"`) jest teraz prawidłowo mapowany jako **`WPA2/WPA3 Personal (sae-mixed)`**, a nie czyste WPA2.
- Dodano okno dialogowe z ostrzeżeniem przed wymuszeniem czystego trybu WPA3-SAE, który powoduje rozłączanie urządzeń domowych Smart Home (Tuya, moduły ESP, gniazdka Wi-Fi).
- Zaktualizowano opcje szerokości pasma do wartości fabrycznych: `40 / 20 MHz` dla 2.4 GHz oraz `160 / 80 / 40 / 20 MHz (Wi-Fi 6/7)` dla 5 GHz.

#### 3. Animowany pasek postępu (ProgressBar) przy optymalizacji kanałów
- Dodano animowany pasek `CTkProgressBar` oraz dynamiczny komunikat podczas skanowania zakłóceń otoczenia w tle.
- Przycisk optymalizacji jest blokowany na czas pomiaru, a po zakończeniu router wyświetla raport o dobranych kanałach.

#### 4. Całkowite usunięcie chińskich znaków i pełna symetria językowa (i18n)
- Wyczyszczono pozostałości języka chińskiego w Zaawansowanych Ustawieniach Wi-Fi: Wi-Fi 5 Kompatybilność, TWT, MU-MIMO, Szybkie parowanie Xiaomi (Mi Connect), Cichy tryb Wi-Fi oraz Roaming Mesh 802.11k/v.
- Przełączniki suwakowe dynamicznie odzwierciedlają stan: `Włączone` / `Wyłączone` oraz `Ukryta` / `Rozgłaszana`.
- W pełni dwujęzyczne formularze: Edycja i Dodawanie Rezerwacji IP (Static DHCP), Przekierowanie Portów, Karta Dostępowa Wi-Fi oraz okno Stok.

---

### 🇬🇧 Release v1.0.1 - Full Localization, 2.5G Physical Ports, Wi-Fi Encryption Fix & Progress Bar

#### Key Enhancements:
- **Physical 2.5 Gbps Port Status:** Real-time link state inspection for WAN/LAN ports via `lan_info.linkList` and `wan_info.link` (`● Connected (2.5G)` / `○ Ready (Auto MDI-X)`).
- **Wi-Fi Mixed Mode Bugfix:** Correctly identifies Xiaomi `"psk2+ccmp"` as `WPA2/WPA3 Personal (sae-mixed)` to prevent smart home IoT devices (Tuya, ESP) from disconnecting. Includes pure WPA3-SAE warning dialog.
- **Wi-Fi Optimization Progress Indicator:** Added real-time animated `CTkProgressBar` while scanning RF interference in the background.
- **Chinese String Cleanup & i18n Symmetry:** Removed all residual Chinese labels from Advanced Wi-Fi settings; dynamic `Enabled`/`Disabled` switch states; fully localized DHCP, Port Forwarding and Wi-Fi Access Card dialogs (534 symmetric keys in Polish and English).
- **Standalone Windows Binary:** Pre-compiled single-file executable `Xiaomi_Router_Manager_v1.0.1.exe`.
