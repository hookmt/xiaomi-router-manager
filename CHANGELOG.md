# Changelog

All notable changes to **Xiaomi Router Manager (XRM)** will be documented in this file.

## [1.1.0] - 2026-11-28

### Added & Improved
- **Feature-Driven Hardware UI (`init_info.features`, Windows & Android):**
  - Audited complete sanitized LuCI dumps of **Xiaomi BE7000 (`RC06 1.1.38`)** and **Xiaomi BE6500 (`RN02 1.0.64`)**.
  - UI now adapts automatically per router model: hides NFC controls when `apps.nfc != "1"`, hides Wi-Fi Silence when `wifi.silence_switch != "1"`, shows Tri-Band 5G Split only when `wifi.split5g == "1"`, and reveals Master/Ethernet/Effect LED controls when `apps.LED_control == "3"`.
- **New Verified Router Controls (Windows & Android):**
  - **Wi-Fi 7 MLO:** Real `xqnetwork/get_hostap_mlo` & `set_hostap_mlo` toggle.
  - **Tri-Band 5G Split:** `xqsystem/set_wifi_split` switch (5G-1 + 5G-2) with reboot confirmation on supported routers.
  - **Multi-LED Controls:** `misystem/allled`, `misystem/ethled`, and conditional `misystem/effect_light`.
  - **Router Name & Location:** In-app rename dialog using `misystem/set_router_name`.
  - **One-Click Mesh Node Switching:** Added a `Switch to this node` button on every Mesh satellite card (Windows & Android) that switches the gateway IP and logs in automatically with the current session password.
- **Full 14-Section Selective JSON Backup & Restore (Windows & Android):**
  - Expanded snapshot backup (`all_led`, `eth_led`, `effect_light`, `nfc`, `mlo`, `smartvpn`) and unlocked full selective restore across 14 router sections in safe execution order (ending with WAN, Wi-Fi, and LAN IP).
- **Official Xiaomi `.tar.gz` Archive Restore (Windows):**
  - Added `misystem/c_upload` + `misystem/c_restore` workflow allowing users to upload and selectively restore native Xiaomi `.tar.gz` backup archives directly from XRM.
- **Factory Reset Pre-Confirmation Warning (Windows & Android):**
  - Added an explicit reminder inside the red Factory Reset modal (before confirming `RESET`) that the administrator password will be restored to default `admin`.

### Fixed
- **10 Verified 1:1 LuCI API Fixes (Windows & Android):**
  - `misystem/led`: fixed payload to `POST {on: 0|1}` (was `state`).
  - `xqnetwork/set_nfc_status`: fixed payload to `POST {nfc_enable: 0|1}` (was `status`).
  - `xqnetwork/get_miotrelay_switch` & `get_wifi_silence`: fixed status reads to `enabled` / `on` (was `switch` / `status`) and toggle payloads to `POST {on: 0|1}`.
  - `xqsystem/vpn_switch` & `vpn_status`: fixed connect/disconnect endpoints (`?conn=1&id=...` / `?conn=0`), added required `oname` in `set_vpn`, and fixed `vpn_status` code mapping (`0`=Connected, `1`=Connecting, `2`=Failed, `3`=Disconnected).
  - `xqnetwork/ddns_add` & `ddns_reload`: mapped provider names to numeric IDs (`1..9`, adding Cloudflare `id=8` with `Bearer` token support), added required DDNS fields, and fixed `ddns_reload`.
  - `misystem/set_band`: switched to `POST` with `manual=1`.
  - `misystem/c_backup` & `c_download`: fixed `GET` query string parameters on Windows and allowed safe relative `/` paths in returned backup filenames on Android & Windows.
- **Android 100% English Localization & UI Alignment:**
  - Translated all remaining Polish static labels, placeholders, tooltips, timezone options, and dynamic alert/confirm dialogs on Android, with immediate re-rendering on `PL`/`EN` switch.
  - Removed duplicate Smart Connect banner inside the right 5 GHz card on both Windows and Android so 2.4 GHz and 5 GHz radio cards align evenly.
  - Unified Windows desktop scrolling across `WAN`, `Ports 2.5G`, `QoS / DDNS / VPN`, `Tools & Maintenance`, and `Setup Wizard` tabs (one clean full-tab vertical scrollbar without cramped nested scroll frames or clipped buttons).
  - Removed leftover Chinese `(Wi-Fi 双频合一)` label from Smart Connect banners and wizard text, hardcoded `(Xiaomi BE7000)` in the Android Ports header, and personal placeholder text.

## [1.0.9] - 2026-11-27

### Added & Improved
- **Native Factory-Reset Router Initialization Protocol (`inited == 0`, Windows & Android):**
  - Implemented the official Xiaomi first-time setup sequence (`xqsystem/login` with `init=1`, `xqnetwork/set_wan_new`, and `misystem/set_router_normal` with AES-CBC PKCS7 + SHA-256 password encryption).
  - Fresh or factory-reset routers (verified live on BE6500 `RN02`) can now be initialized end-to-end directly from XRM without opening the Chinese web browser interface.
- **Official LuCI Timezone API (`POST misystem/set_sys_time`, Windows & Android):**
  - Aligned timezone & clock updates with official MiWiFi LuCI (`POST` with `{timezone, index}` using V2 `TIMEZONEMAP` indices such as `2.54` for Poland/CET and `2.84` for China/CST-8, plus separate `POST` with `{time}`).
  - Router timezone changes now persist cleanly and match the official Xiaomi Web UI immediately.
- **Full Software Factory Reset (`?format=1`) & Red Safety Modal (Windows & Android):**
  - Updated factory reset to call `xqsystem/reset?format=1` (verified live on BE6500: restores full `inited=0` factory state with default password `admin`).
  - Added a custom red confirmation modal displaying the router's active role (`MASTER (MESH)` / `MASTER / STANDALONE` / `SATELITA / AP`), model, name, and IP before requiring `RESET` confirmation.
  - Highlighted LAN Gateway IP Save button in red (`#dc2626`) to warn against accidental subnet changes.
- **Mesh Topology & Multi-Router Hardening (Windows & Android):**
  - Added Master & Satellite MAC fallbacks, per-node client mapping (showing connected devices under Master and each Satellite), and Mesh node badges on Android device cards.
  - Fixed Mesh satellite protection (`isap > 0` instead of `isap == 1`) so satellites are protected as `[Stacja Admina / AP]` instead of showing `Blokuj Net`.
  - Cleared stale router cache (`init_info`, `device_id`, `snapshot`, WAN inputs) on disconnect and router switching.

### Fixed
- **WAN Upload Speed Bug (Windows & Android):** Fixed Dashboard upload rate reading cumulative byte counter `wan.upload` (which showed hundreds of `MB/s`) instead of real-time `wan.upspeed`.
- **DHCP WAN DNS Display (Windows & Android):** Added `dnsAddrs` / `dnsAddrs1` / `dnsAddrs2` extraction so routers connected via DHCP WAN show active DNS servers instead of `-`.
- **Android Dashboard Summary Badges:** Populated `#dash-led-status` (`Diody LED`) and `#dash-net-mode` (`Tryb sieci`) on the mobile dashboard.
- **Windows Setup Wizard Steps 4 & 5:** Fixed missing Step 4 (Timezone) frame builder, Static IP WAN fields, `set_wan` PPPoE parameter names (`pppoeName`/`pppoePwd`), `set_twt` argument signature, Smart Connect toggle handling, and removed dead MLO option and double colons (`::`).
- **UI Polish (Windows & Android):** Cleaned Chinese `Xiaomi路由器` prefix to `Xiaomi Router `, fixed 5 GHz bandwidth label mapping in Wi-Fi confirmation dialog, widened TX/Bandwidth/Timezone comboboxes, shortened displayed POSIX timezone string, compacted device uptime (`59s`, `4m`, `6h 48m`) to prevent clipping, removed hardcoded `1472` MTU pre-fill, and updated 5 GHz scan fallback text.

## [1.0.8] - 2026-11-26

### Added & Improved
- **Critical Fix: Xiaomi BE7000 Wi-Fi Encryption API Mapping (Windows & Android):**
  - Aligned Wi-Fi encryption codes directly with stock MiWiFi LuCI `<select name="encryption">` values (`psk2+ccmp` = WPA2/WPA3 Personal Mixed, `ccmp` = WPA3 Personal, `psk2` = WPA2 Personal, `mixed-psk` = WPA/WPA2 Mixed, `none` = Open).
  - Previously, sending OpenWrt's `sae-mixed` caused BE7000 to switch to pure WPA3 (`ccmp`), disconnecting WPA2-only clients (e.g. NAS/IoT devices).
  - Channel optimization now preserves the exact raw `encryption` code reported by the router snapshot so optimizing Wi-Fi channels never alters security settings.
- **Real Wi-Fi Spectrum Scan & Channel Optimization (Windows & Android):**
  - Replaced legacy non-existent endpoints (`xqnetwork/wifi_channel_optimize` / `wifi_check`, which returned HTTP 404 on BE7000) with the official MiWiFi LuCI scan flow: `api/misystem/channel_scan_start` followed by polling `api/misystem/channel_scan_result` until `status == 0`.
  - Displays real current vs recommended channel(s) and interference scores from the router, and asks for user confirmation before applying the recommended channel(s) via `set_all_wifi` (preserving SSID, password, encryption, bandwidth, and TX power).
- **Permanent Android APK Release Signing Key (CI / GitHub Secrets):**
  - Configured persistent PKCS12 release signing in `mobile/android/app/build.gradle` and `.github/workflows/build-and-release.yml` using encrypted GitHub Secrets (with debug fallback for local builds). Future APK releases from v1.0.8 onward install cleanly in-place without uninstalling.
- **Mobile Phone Portrait & Landscape Layout Overhaul (`mobile/www/`):**
  - Fixed navigation drawer vertical scrolling on phones in landscape orientation (`height: 100dvh`, `min-height: 0`, `flex-shrink: 0`).
  - Flattened `System i Narzędzia` in the navigation drawer from a 1-item collapsible group into a direct single-tap button.
  - Fixed 4th QoS profile button (`Streaming`) clipping on narrow phones by switching `#qos-mode-selector` to a 2x2 grid below `700px`.
  - Fixed Port 2.5G advanced role selector overflow (`.select-role-wrapper`) and hidden native checkbox rendering on `.toggle-switch` controls (LAG, Dual WAN, IPTV, Gaming, LED).
  - Extended `#main-header` wrapping to `max-width: 960px` (landscape phones) and applied `minmax(0, 1fr)` + `min-width: 0; width: 100%` globally to `.form-row-2` / inputs / selects to eliminate right-edge card overflow (NAT, LAN, Ports, Wi-Fi).

## [1.0.7] - 2026-11-26

### Added & Improved
- **Minimal CPU Load Display (Windows & Android):**
  - Idle CPU load below `1.0%` is now formatted as `< 1%` (with minimum 1% progress bar fill) instead of `0%` / `0.0%` on both desktop and mobile dashboards.
- **Timezone Selector in Windows Main Window (`gui.py`):**
  - Added a Timezone dropdown with a dedicated Save button directly inside the Tools & Diagnostics tab (next to PC time sync), reusing the full IANA-to-POSIX table from `setup_wizard.py`.
  - PC time synchronization now uses the currently selected timezone instead of a hardcoded value, and the selector syncs automatically with router snapshots.
- **Visible Version Badge in Android / Mobile UI (`v1.0.7`):**
  - Added a subtle `v1.0.7` badge next to the app title in the top header and an `XRM Mobile v1.0.7` footer inside the navigation drawer.
- **Android / Mobile UX & Stability Fixes (`MainActivity.java`, `mobile/www/`):**
  - Disabled WebView asset HTTP cache (`LOAD_NO_CACHE` + `clearCache(true)`) so in-place APK updates immediately load the new UI without reinstalling.
  - Moved the `+ Nowa rezerwacja` button directly into the Static DHCP Reservations card and converted DHCP reservations from a horizontally scrolling table to stacked `.device-card` rows matching Network Devices.
  - Added `xqnetwork/wifi_check` fallback and a 30-second read timeout for Wi-Fi channel optimization (matching desktop `miwifi_core.py`).

### Removed
- **Wi-Fi Regulatory Region (`set_country_code`) UI (Windows & Android):**
  - Removed Wi-Fi country code editing from Windows (`gui.py`, `setup_wizard.py`) and Android (`mobile/www/`), as modern stock Xiaomi firmware locks `CountryCode` in the `bdata` partition and rejects changes via HTTP API (code `1606`). The router's read-only region code remains visible in Dashboard ROM info.

## [1.0.6] - 2026-11-22

### Added
- **Timezone and Regulatory Region Selector (Mobile / Android / PWA):**
  - New "Router Timezone" card in System and Tools view with full IANA-to-POSIX timezone selector (44 timezones).
  - New "Wi-Fi Regulatory Region (RegDomain)" card with country code selector (CE/FCC/CN) and regulatory warnings.
  - Quick Setup Wizard extended with Timezone and Regulatory Region selectors before applying settings.
  - `btn-sync-time` now applies timezone directly from the selector instead of hardcoded Europe/Warsaw.
- **Timezone and Regulatory Region Selector (Windows Desktop Setup Wizard):**
  - Wizard expanded from 4 to 5 steps; Step 4 dedicated to Timezone (POSIX mapping) and Wi-Fi Country Code selection.
  - Execution thread (`_apply_all`) invokes `set_sys_time` with POSIX timezone string and `set_country_code` with selected country code.
  - Summary step updated to display chosen timezone and country code.

## [1.0.5] - 2026-11-20

### Added & Improved
- **Native Android App & Tablet-Optimized Client (`mobile/`):**
  - Built-in Android project with Gradle wrapper, hardware-accelerated WebView, and Android Keystore secure token storage.
  - Responsive, fluent interface designed specifically for tablets (OPPO Pad 3 Pro) and smartphones, featuring accordion drawer navigation and full offline UI test suite.
- **Modernized Dropdown Selection Menus (`CTkOptionMenu` on Windows & Android):**
  - Replaced horizontal segmented buttons with dropdown selectors for WAN connection modes (`PPPoE`, `DHCP`, `Static IP`) with dynamic form layout.
  - Replaced segmented switches in 2.5 Gbps hardware port features with intuitive dropdown: `Dual WAN`, `Link Aggregation (LAG LACP)`, `IPTV Bridge VLAN`, and `Gaming Port VIP QoS`.
  - Replaced segmented switches in QoS / DDNS / VPN modules with unified dropdown switcher.
- **Adaptive Wi-Fi & Smart Connect Layout:**
  - When Smart Connect is enabled: common full-width card manages unified SSID, password, and encryption, while band cards focus purely on RF parameters (TX power, channel, bandwidth, hidden SSID).
  - When Smart Connect is disabled: top card gracefully hides, presenting independent, full-fledged cards for 2.4 GHz and 5 GHz with separate save actions.
- **Bidirectional Sorting & Direct Reservation Badges:**
  - Network devices and static DHCP leases now support bidirectional sorting: numeric IPv4 octets (Ascending / Descending), Alphabetical (A-Z / Z-A), and Active First.
  - Real-time reservation status directly on device rows: green `● Reserved` badge and `Edit` button for bound devices, `+ Reserve IP` button for unbound devices, and `Edit`/`Delete` for offline leases.
- **Serwer DHCP DNS Configuration:**
  - Dedicated `DNS 1` and `DNS 2` configuration fields in LAN / DHCP settings.

### Fixed & Hardened
- **RAM Memory Gauge & Unit Calculation:**
  - Fixed RAM calculation on dashboard by properly parsing router string format (e.g. `"1024MB"`) to bytes, resolving the `440.32 B / 1 KB` display bug.
- **Router Time Display:**
  - Fixed `[object Object]` bug in system tools by parsing nested router time dictionary `{year, month, day, hour, min, sec, timezone}` into standard formatted timestamp.
- **Security & Repository Hygiene:**
  - Removed hardcoded fallback MAC identifier from `miwifi_core.py` and `app.js` in favor of dynamic discovery.
  - Removed development HTTP proxy scripts (`mobile/run_preview.py` and `mobile/run_preview.bat`) from Git tracking.

### Added & Improved
- **Quick DHCP Reservation from Active Network Devices (`+ Rezerwuj` / `+ Reserve`):**
  - Active network devices without static DHCP reservations now display a direct quick-action button in `Dashboard & devices -> Network Devices`.
  - Automatically pre-populates Device Name, locked/readonly MAC address, and current dynamic IP address.
  - Instantly registers the static lease via router API (`mac_bind`), refreshes network status, and removes the button once bound.
- **Enhanced DHCP Dialog Prefill (`_dialog_add_mac_bind`):**
  - Added support for prefilled parameters with dedicated notification header and locked hardware MAC field.

---

## [1.0.1] - 2026-11-16

### Added & Improved
- **Physical Ports 2.5 Gbps Hardware Status:**
  - Real-time link status detection for WAN and LAN ports (reading `lan_info.linkList` and `wan_info.link`).
  - Active ports with connected cable display green `● Connected (2.5G)` / `● Połączony (2.5G)`, while vacant ports show `○ Ready (Auto MDI-X)` / `○ Gotowy (Auto MDI-X)`.
- **Wi-Fi Channel Optimization Progress Indicator:**
  - Added real-time animated `CTkProgressBar` and status indicator during Wi-Fi channel optimization and background interference measurement.
- **Dynamic Switch State Labels:**
  - Switch widgets in Advanced Wi-Fi and Radio cards dynamically toggle between `Enabled` / `Disabled` (`Włączone` / `Wyłączone`) and `Ukryta` / `Rozgłaszana` (`Hidden` / `Broadcasted`).

### Fixed
- **Wi-Fi WPA2/WPA3 Mixed Encryption & IoT Disconnect Prevention:**
  - Router API value `"encryption": "psk2+ccmp"` is now correctly recognized as `WPA2/WPA3 Personal (sae-mixed)` instead of pure WPA2.
  - Prevents breaking legacy smart home/IoT devices (Tuya, ESP, smart plugs).
  - Added safety confirmation dialog before applying pure WPA3-SAE.
- **Realistic Bandwidth Options:**
  - Standardized bandwidth selections to match Xiaomi Web UI (`40 / 20 MHz` on 2.4 GHz, `160 / 80 / 40 / 20 MHz` on 5 GHz).
- **Comprehensive Bilingual Localization & Chinese Text Cleanup:**
  - Cleaned up all Chinese leftover strings in Advanced Wi-Fi settings (`(Wi-Fi 5 兼容模式)`, `(TWT节能模式)`, `(畅快连)`, `(静默模式)`, `(手动设置漫游参数)`).
  - Expanded symmetric dictionary in `i18n.py` to **534 keys** across PL and EN.
  - Fully localized modal dialogs: Add/Edit DHCP Reservation, Single Port Forwarding, Port Range Forwarding, Add DDNS, Add VPN, Wi-Fi Access Card, Reboot, Factory Reset, and Stok help.
- **Binary Naming:**
  - Release executable is now named with explicit version: `Xiaomi_Router_Manager_v1.0.1.exe`.

---

## [1.0.0] - 2026-11-16

### Initial Release
- Desktop GUI for Xiaomi BE6500 Pro / BE7000 / BE3600 / AX routers running OpenWrt / MiWiFi.
- Automatic stok token extraction & SHA-256 / AES-CBC encrypted password authentication.
- Real-time Dashboard, Topology Mesh, DHCP IP reservation manager, Port forwarding, Smart QoS, Tools, and Markdown exporter.
- Windows PE standalone `.exe` compiled with PyInstaller.
