# Xiaomi Router Manager (XRM)

[![Version](https://img.shields.io/badge/version-v1.0.1-blue.svg)](version.py)
[![Platform](https://img.shields.io/badge/platform-Windows%2010%20%7C%2011-blue.svg)](https://microsoft.com/windows)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![UI](https://img.shields.io/badge/UI-CustomTkinter%20Fluent%20Design-darkgreen.svg)](https://github.com/TomSchimansky/CustomTkinter)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Xiaomi Router Manager (XRM)** is a native, modern Windows desktop application and diagnostic toolkit designed for managing, configuring, and recovering Xiaomi & Redmi Wi-Fi routers running official MiWiFi / OpenWrt LuCI firmware. 

Originally built and optimized for the flagship **Xiaomi Router BE7000 (4x 2.5 Gbps)**, it also provides full compatibility with **BE6500 Pro, AX3600, AX6000, AX9000**, and related models.

<p align="center">
  <img src="screenshots/01_dashboard_live.png" alt="Xiaomi Router Manager Dashboard" width="850">
</p>

---

## Why Xiaomi Router Manager?

Many high-performance Xiaomi routers (such as Chinese models with high-power RF frontends and multi-gigabit ports) ship with a Chinese-only web administrative interface. Even global firmware versions often restrict advanced features, lack proper port editing, and hide crucial diagnostics.

**Xiaomi Router Manager** bypasses these limitations completely:
- **No Chinese Interface:** 100% bilingual user interface (**English** and **Polish**) with real-time on-the-fly language switching.
- **Hardware-Level Control:** Visual management of 2.5 Gbps ports, Dual WAN, Link Aggregation (LAG LACP), IPTV VLAN tags, and Gaming Port priority.
- **Enhanced Safety:** Active DMZ collision prevention (blocks enabling DMZ when port forwarding rules exist to avoid Xiaomi firmware error 1609).
- **Fast Disaster Recovery:** Single-click selective JSON backup/restore and ultra-fast headless CLI scripts (recovering 40+ DHCP reservations and NAT rules in under 3 seconds).
- **Setup Wizard:** Complete first-time configuration of a fresh or factory-reset router step-by-step in English or Polish without opening a browser.

---

## Verified Hardware Support

| Model | Architecture | Ports | Wi-Fi Standard | Status |
|---|---|---|---|---|
| **Xiaomi Router BE7000** | Qualcomm IPQ9554 (Quad-Core) | 4x 2.5 Gbps RJ45 + USB 3.0 | Wi-Fi 7 (Tri-Band / MLO) | **Primary Target (Full Support)** |
| **Xiaomi Router BE6500 Pro** | Qualcomm IPQ5322 | 4x 2.5 Gbps RJ45 | Wi-Fi 7 | Fully Supported |
| **Xiaomi AIoT Router AX3600** | Qualcomm IPQ8071A | 1x 1G WAN + 3x 1G LAN | Wi-Fi 6 | Fully Supported |
| **Xiaomi Router AX6000 / AX9000** | Qualcomm IPQ5018 / IPQ8072 | 1x 2.5G + 1G LAN | Wi-Fi 6 | Fully Supported |
| **Redmi Gaming Router AX5400** | Qualcomm IPQ5018 | 1x 2.5G + 4x 1G | Wi-Fi 6 | Supported |

*Any Xiaomi/Redmi router using the standard `/cgi-bin/luci/;stok=.../api/xqnetwork/` API endpoints is compatible.*

---

## Key Features

### 1. Live Dashboard & Telemetry
- Real-time CPU and RAM utilization gauge meters.
- Real-time WAN bandwidth speed monitoring (download/upload throughput).
- Hardware details: uptime, firmware ROM version, router hardware ID, external WAN IP, and active DNS servers.
- Live active client device counter and system LED control.

### 2. Physical Port Visualization & Hardware Switching (4x 2.5 Gbps)
- Visual RJ45 jack status diagram with active link detection, negotiation speed (2.5G / 1G), and assigned network role.
- **Dual WAN:** Secondary WAN port selection with **Bandwidth Aggregation (Load Balancing)** or **Failover (Backup Link)**.
- **Link Aggregation (LAG):** Combine two LAN ports into a trunk channel using **Dynamic LACP (802.3ad)** or **Static LAG**.
- **IPTV / STB Isolation:** Dedicated port assignment for ISP set-top boxes with custom VLAN VID tagging.
- **Dedicated Gaming Port:** Hardware-prioritized transmission for gaming consoles or PC.

### 3. Comprehensive NAT, Port Forwarding & DMZ
- **Single Port Forwarding:** Add, delete, and **in-place edit** existing port redirection rules.
- **Port Range Forwarding:** Add, delete, and **in-place edit** port range rules.
- **Collision-Safe DMZ:** Visual warning and automatic lock preventing DMZ activation when active port forwarding rules exist, guarding against Xiaomi's native error 1609.
- **UPnP Monitor:** Real-time list of dynamic UPnP port mappings opened by consoles and applications with an instant global killswitch.

### 4. Advanced Wireless (Wi-Fi 7 / 6) Configuration
- Dual-band controls for 2.4 GHz and 5 GHz radios.
- **Smart Connect (Wi-Fi 双频合一):** Combined SSID with automated band steering.
- Security modes: WPA2-PSK AES, WPA3-Personal SAE, mixed WPA2/WPA3, and open.
- Channel selection and bandwidth switching up to **160 MHz**.
- Global and per-band Transmission Power (TX Power) selection: **Maximum (Boosted)**, **Medium (Standard)**, and **Low (Power Save)**.
- Wi-Fi Access Card with one-click Wi-Fi credentials display.

### 5. LAN & Static DHCP Leases
- Router LAN IP, subnet mask, DHCP server range limits, and lease time.
- Static DHCP reservation table with real-time search and filter.
- Smart device hint dropdown: automatically populates MAC and IP from active network clients.

### 6. Network Services (QoS, DDNS, VPN)
- **Smart QoS:** Bandwidth allocation priority modes (Smart, Gaming, Web, Video) and host limits.
- **Dynamic DNS (DDNS):** Cloudflare, No-IP, DynDNS, Oray, PubYun support with status indicators.
- **VPN Client:** PPTP and L2TP client profiles with Smart VPN split-tunneling (domain- or MAC-based).

### 7. Maintenance, Backup & Audit Reports
- **Selective JSON Restore:** Export and import router configuration; restore static DHCP or port forwarding selectively without router reboot.
- **Encrypted Admin Password Management:** Updates router password using native Xiaomi AES-CBC and SHA-256 client-side encryption.
- **Full Markdown Audit Report:** One-click generation of a formatted `.md` report documenting the entire router configuration, WAN parameters, and client inventory.
- **Official Backup:** Direct download of official Xiaomi `.tar.gz` configuration archives.

### 8. Disaster Recovery Headless CLI (`CLI/`)
Lightweight, zero-dependency Python 3 scripts for rapid headless disaster recovery:
- `CLI/restore_router_config.py`: Primary emergency script injecting DHCP reservations and NAT rules in 3 seconds via session token.
- `CLI/apply_dhcp.py`: Automated Excel/CSV parser and DHCP reservation injector.
- `CLI/apply_portforward.py`: Automated port forwarding rule injector.

---

## Security & Architecture

- **100% Local Communication:** All API calls are made directly between your computer and the router via local HTTP/JSON API (`http://192.168.31.1/cgi-bin/luci/;stok=.../api/`).
- **Zero Cloud / Telemetry:** No data is sent to external servers or third-party analytical endpoints.
- **Encrypted Authentication:** Native password authentication uses client-side SHA-256 hashing combined with router-provided nonce and router key calculation.

---

## Screenshots & UI Walkthrough

<details open>
<summary><b>1. Physical Ports Visualization (4x 2.5 Gbps) & Hardware Roles</b></summary>
<br>
<img src="screenshots/08_physical_ports_2.5g.png" alt="Physical Ports 2.5G" width="850">
</details>

<details>
<summary><b>2. Wi-Fi & Radio Bands (Wi-Fi 7/6, 160MHz, WPA2/WPA3 Mixed)</b></summary>
<br>
<img src="screenshots/06_wifi_settings.png" alt="Wi-Fi Settings" width="850">
</details>

<details>
<summary><b>3. Connected Network Devices & Band Telemetry</b></summary>
<br>
<img src="screenshots/02_network_devices.png" alt="Network Devices" width="850">
</details>

<details>
<summary><b>4. LAN & Static DHCP Reservation Management</b></summary>
<br>
<img src="screenshots/05_lan_dhcp_reservations.png" alt="Static DHCP Leases" width="850">
</details>

<details>
<summary><b>5. Port Forwarding, NAT & Protected DMZ</b></summary>
<br>
<img src="screenshots/07_port_forwarding_nat.png" alt="Port Forwarding" width="850">
</details>

<details>
<summary><b>6. Mesh Topology & Nodes</b></summary>
<br>
<img src="screenshots/03_mesh_topology.png" alt="Mesh Topology" width="850">
</details>

<details>
<summary><b>7. Selective JSON Configuration Restore</b></summary>
<br>
<img src="screenshots/11_selective_restore_dialog.png" alt="Selective Restore Dialog" width="850">
</details>

<details>
<summary><b>8. First-Time Router Setup Wizard</b></summary>
<br>
<img src="screenshots/12_setup_wizard.png" alt="Setup Wizard" width="850">
</details>

<details>
<summary><b>9. WAN Settings & PPPoE</b></summary>
<br>
<img src="screenshots/04_wan_settings.png" alt="WAN Settings" width="850">
</details>

<details>
<summary><b>10. Smart QoS Bandwidth Management</b></summary>
<br>
<img src="screenshots/09_smart_qos.png" alt="Smart QoS" width="850">
</details>

<details>
<summary><b>11. System Maintenance & Diagnostics</b></summary>
<br>
<img src="screenshots/10_system_tools.png" alt="System Tools" width="850">
</details>

---

## Installation & Usage

### Option A: Standalone Executable (No Python Required)
1. Download `Xiaomi_Router_Manager_v1.0.1.exe` from the [Releases](https://github.com/hookmt/xiaomi-router-manager/releases) page.
2. Launch `Xiaomi_Router_Manager_v1.0.1.exe`.
3. Enter your router gateway IP (`192.168.31.1` by default) and administrator password (or paste a browser URL containing `;stok=...`).
4. Click **Connect**.

### Option B: Running from Source (Python 3.10+)
Clone the repository and run with `uv` (recommended) or standard Python:

```bash
# Clone repository
git clone https://github.com/hookmt/xiaomi-router-manager.git
cd xiaomi-router-manager

# Run using uv (installs dependencies automatically)
uv run --with customtkinter --with cryptography python gui.py

# Or using standard pip / venv
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install customtkinter cryptography openpyxl
python gui.py
```

### Building the Single-File Executable
To package the application into a standalone `.exe`:

```bash
uv run --with pyinstaller --with customtkinter --with cryptography pyinstaller `
    --name "Xiaomi_Router_Manager" `
    --noconsole `
    --onefile `
    --icon "app_icon.ico" `
    --version-file "file_version_info.txt" `
    --collect-all customtkinter `
    --add-data "app_icon.ico;." `
    --clean `
    gui.py
```

---

## Polish Summary / Podsumowanie po polsku

**Xiaomi Router Manager (XRM)** to natywna, wielojęzyczna (PL / EN) aplikacja okienkowa dla systemu Windows do zarządzania, konfiguracji i diagnostyki routerów Xiaomi i Redmi (ze szczególnym uwzględnieniem flagowego modelu **Xiaomi Router BE7000 4x 2.5G**, a także **BE6500 Pro, AX3600, AX6000, AX9000**).

Aplikacja całkowicie eliminuje konieczność korzystania z chińskiego panelu webowego LuCI routera, oferując elegancki interfejs w stylu Windows 11 Fluent Design oraz:
- Pełną obsługę języka polskiego i angielskiego.
- Wizualizację i zarządzanie 4 portami 2.5 Gbps (Dual WAN, LAG LACP, IPTV, Port Gry).
- Bezpieczną edycję reguł NAT i zabezpieczenie DMZ przed błędem kolizji 1609.
- Zaawansowane opcje Wi-Fi (Smart Connect, moc nadawania, optymalizacja pasm).
- Selektywny backup/restore konfiguracji (.json) oraz generator kompletnych raportów Markdown.
- Lekkie narzędzia konsolowe CLI do odzyskiwania po awarii w folderze `CLI/`.

---

## Acknowledgements / Podziękowania

- Co-developed with **Antigravity** (Google DeepMind) as AI engineering assistant & technical partner.
- Projekt współtworzony z cyfrowym asystentem inżynieryjnym **Antigravity** (Google DeepMind).

---

## License

Distributed under the MIT License. See [`LICENSE`](LICENSE) for details.
