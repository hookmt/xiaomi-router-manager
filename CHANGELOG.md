# Changelog

All notable changes to **Xiaomi Router Manager (XRM)** will be documented in this file.

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
