# ZBIORÓWKA ZADAŃ I POPRAWEK DO WDROŻENIA

Status: Zbieranie uwag i poprawek do wydania v1.1.0 (zgodnie z wytyczną użytkownika: nie poprawiać od razu, zbierać do zbiorówki na kolejną wersję).

---

## Zadania do wydania v1.1.0

### 1. Karta Konserwacja Sprzętowa (Hardware Maintenance / System Time)
- **Etykieta czasu routera (`lbl_sys_time`):**
  - Problem: w `gui.py` (linia 4986) string `"Czas routera: {t_str} ({tz_str})"` jest wpisany na sztywno po polsku. W trybie EN powoduje to asymetrię: etykieta wyświetla się po polsku (`Czas routera: ...`), podczas gdy przycisk obok po angielsku (`[🕒 Sync with PC]`).
  - Rozwiązanie: zamiana na `f"{t('tools_time_label', lg)} {t_str} ({tz_str})"`.

---

## Archiwum wdrożeń v1.0.0 (Zrealizowane 2026-11-16)
- **Karta DMZ:** Komunikat kolizji `nat_dmz_collision_warn` wdrożony dla PL i EN.
- **Porty fizyczne 2.5G:** Role portów (`port_role_*`) i stany połączeń (`port_link_*`) przetłumaczone dla PL i EN.
- **Menu rozwijane:** Dual WAN, LAG, Wi-Fi TX Power oraz hinty urządzeń (`hint_manual_entry`, `hint_select_known`) dynamicznie lokalizowane.
- **Raport Markdown:** Dodano bezpieczny fallback odczytu serwerów DNS dla połączeń PPPoE (`pppoe_status` / `wan_info`).
- **Wersjonowanie:** Wdrożono SemVer v1.0.0, centralny moduł `version.py` oraz metadane binarne Windows PE (`file_version_info.txt`).
