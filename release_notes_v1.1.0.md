# Xiaomi Router Manager (XRM) v1.1.0

Release `v1.1.0` brings 10 verified 1:1 LuCI API fixes audited directly against real **Xiaomi BE7000 (`RC06 1.1.38`)** and **Xiaomi BE6500 (`RN02 1.0.64`)** router firmware, feature-driven hardware UI adaptation, Wi-Fi 7 MLO and Tri-Band controls, full 14-section selective JSON backup & restore, official Xiaomi `.tar.gz` backup/restore support, and complete English localization across Android.

## Highlights

### 10 Verified 1:1 LuCI API Fixes (Windows & Android)
- **LED Control (`misystem/led`, `allled`, `ethled`, `effect_light`):** Fixed payload key to `POST {on: 0|1}` (previously sent invalid `state`). Added multi-LED controls (Master All LEDs, Ethernet Port LEDs, and optional Effect Light) automatically shown on models with `LED_control == 3` (such as BE7000).
- **NFC Control (`xqnetwork/get_nfc_info`, `set_nfc_status`):** Fixed payload key to `POST {nfc_enable: 0|1}` (previously sent invalid `status`) and gated NFC controls by `init_info.features.apps.nfc == "1"` (automatically hidden on models without NFC hardware like BE6500).
- **Mi Connect & Wi-Fi Silence (`get_miotrelay_switch`, `get_wifi_silence`):** Fixed state reads to use LuCI's real fields (`rsp.enabled` and `rsp.on`) and exact `POST {on: 0|1}` payloads. Wi-Fi Silence is now hidden on routers without `wifi.silence_switch == "1"` (such as BE6500).
- **VPN Client (`xqsystem/vpn_switch`, `set_vpn`, `vpn_status`):** Fixed connect/disconnect endpoints to `vpn_switch?conn=1&id=...` and `vpn_switch?conn=0`, added required `oname` profile name field in `set_vpn`, added `set_vpnauto`, and fixed `vpn_status` code mapping (`0` = Connected, `1` = Connecting, `2` = Failed, `3` = Disconnected).
- **DDNS (`xqnetwork/ddns_add`, `ddns_reload`):** Added numeric provider ID mapping (`1..9`) including **Cloudflare** (`id=8` with `Bearer` token support), complete required fields (`wanindex`, `iptype`, `checkinterval`, `forceinterval`, `enable`), and fixed `ddns_reload` call.
- **QoS Bandwidth (`misystem/set_band` & `qos_limits`):** Fixed `set_band` to send `POST` with `manual=1` and added `qos_limits` JSON payload helper.
- **Official Xiaomi `.tar.gz` Backup & Restore (`c_backup`, `c_upload`, `c_restore`):** Fixed `c_backup` query-string invocation, allowed safe `/` subpaths in `rsp.file` on Android & Windows, and added official `.tar.gz` archive upload & selective restore on Windows.

### New Controls & Full Selective Recovery
- **Wi-Fi 7 MLO (Multi-Link Operation):** Real `get_hostap_mlo` / `set_hostap_mlo` toggle on both Windows and Android (gated by `features.wifi.mlo`).
- **Tri-Band 5G Split (5G-1 + 5G-2):** Dedicated `set_wifi_split` switch with reboot confirmation on Tri-Band routers (`features.wifi.split5g == "1"`, e.g. BE7000).
- **Router Name & Location Editor:** Direct `set_router_name` dialog in System & Tools on both Windows and Android.
- **One-Click Mesh Node Switching:** Added a `Switch to this node` button on Mesh satellite cards (Windows & Android) to connect directly to a satellite IP using the current session password (ideal for inspecting or factory-resetting a Mesh satellite).
- **Full 14-Section Selective JSON Backup & Restore (Windows & Android):** Restores Router Name, Timezone, LED & NFC, DHCP Reservations, NAT Port Forwarding, DMZ, UPnP, 2.5G Port Functions, QoS, DDNS, VPN & SmartVPN, LAN DHCP Server, WAN, Wi-Fi (including Tri-Band, MLO, TWT, Mi Connect, Roaming), and LAN Gateway IP (applied last) with per-section checkboxes and Select All / Deselect All.
- **Factory Reset Safety Modal:** Added an explicit pre-confirmation reminder that the administrator password will be restored to default `admin`.

### Android & Desktop UI / Translation Polish
- **100% English Localization on Android:** Audited and translated over 100 remaining UI labels, placeholders, tooltips, modals, timezone names, and alert/confirm prompts, with instant live re-rendering when switching `PL` / `EN`.
- **Clean Wi-Fi Smart Connect Alignment & Unified Windows Scrolling:** Removed the duplicate Smart Connect sync banner inside the right 5 GHz card so 2.4 GHz and 5 GHz radio cards align evenly, and unified Windows tab scrolling across `WAN`, `Ports 2.5G`, `QoS / DDNS / VPN`, `Tools & Maintenance`, and `Setup Wizard` so no buttons or panels clip at default window height.
- **Generic Model & UI Hygiene:** Removed leftover Chinese `(Wi-Fi 双频合一)` text from Smart Connect labels, removed hardcoded `(Xiaomi BE7000)` from the Android Ports header, and replaced personal example placeholder text with generic `e.g. NAS Server`.

## Downloads
- **Windows:** `Xiaomi_Router_Manager_v1.1.0.exe` (standalone, no Python required)
- **Android:** `Xiaomi_Router_Manager_v1.1.0.apk` (signed with the permanent release key; installs cleanly over v1.0.8 / v1.0.9)
