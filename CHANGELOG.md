# Changelog

All notable changes to **Xiaomi Router Manager (XRM)** will be documented in this file.

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
