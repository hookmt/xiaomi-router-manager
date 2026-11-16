# Changelog

All notable changes to **Xiaomi Router Manager (XRM)** will be documented in this file.

## [1.0.1] - 2026-11-16

### Fixed
- **Comprehensive Bilingual Localization (i18n):**
  - Added 100+ translation keys for Polish (`pl`) and English (`en`), maintaining symmetric 452-key coverage across both languages.
  - Fully localized modal dialogs: Add/Edit DHCP Reservation, Single Port Forwarding, Port Range Forwarding, Add DDNS, Add VPN, Change Admin Password, Wi-Fi Access Card, and Selective Configuration Restore.
  - Localized Wi-Fi Advanced Settings: Wi-Fi 5 compatibility, TWT (Target Wake Time), MU-MIMO, Mi Connect, Silent mode, Mesh Roaming thresholds, Regulatory Region, and Wi-Fi TX Power.
  - Fixed hardcoded "Czas routera:" label in Hardware Maintenance tab to use dynamic `tools_time_label`.
  - Localized Initial Setup Wizard (step 1-4 hints, MTU presets, validation prompts, factory status checks).
- **Binary Naming:**
  - Release executable is now named with explicit version: `Xiaomi_Router_Manager_v1.0.1.exe`.

---

## [1.0.0] - 2026-11-16

### Initial Release
- Desktop GUI for Xiaomi BE6500 Pro / BE7000 / BE3600 / AX routers running OpenWrt / MiWiFi.
- Automatic stok token extraction & SHA-256 / AES-CBC encrypted password authentication.
- Real-time Dashboard, Topology Mesh, DHCP IP reservation manager, Port forwarding, Smart QoS, Tools, and Markdown exporter.
- Windows PE standalone `.exe` compiled with PyInstaller.
