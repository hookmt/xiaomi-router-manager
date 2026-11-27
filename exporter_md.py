import datetime
import os
from typing import Any, Dict

try:
    from version import APP_VERSION
except ImportError:
    APP_VERSION = "1.0.0"


def safe_int(val: Any, default: int = 0) -> int:
    try:
        return int(float(str(val)))
    except (ValueError, TypeError):
        return default


def format_bytes(bytes_num: float) -> str:
    """Formatowanie bajtów na czytelne KB/MB/GB."""
    if not bytes_num or bytes_num <= 0:
        return "0 B"
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if abs(bytes_num) < 1024.0:
            return f"{bytes_num:.1f} {unit}"
        bytes_num /= 1024.0
    return f"{bytes_num:.1f} PB"


def format_speed(bps: float) -> str:
    """Formatowanie prędkości transferu (B/s -> KB/s, MB/s)."""
    if not bps or bps <= 0:
        return "0 KB/s"
    kb = bps / 1024.0
    if kb < 1024:
        return f"{kb:.1f} KB/s"
    mb = kb / 1024.0
    return f"{mb:.2f} MB/s"


def format_uptime(seconds: int, lang: str = "pl") -> str:
    """Formatowanie sekund do postaci dni, godzin, minut."""
    if not seconds:
        return "no data" if lang == "en" else "brak danych"
    days = seconds // 86400
    hours = (seconds % 86400) // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    parts = []
    if days > 0:
        parts.append(f"{days}d" if lang == "en" else f"{days} dni")
    if hours > 0:
        parts.append(f"{hours}h" if lang == "en" else f"{hours} godz.")
    if minutes > 0:
        parts.append(f"{minutes}m" if lang == "en" else f"{minutes} min.")
    if not parts:
        parts.append(f"{secs}s" if lang == "en" else f"{secs} sek.")
    return " ".join(parts)


def export_snapshot_to_markdown(snapshot: Dict[str, Any], output_path: str, mask_passwords: bool = True) -> str:
    """Generuje czytelny, kompleksowy raport konfiguracji routera w formacie Markdown."""
    init = snapshot.get("init_info", {})
    status = snapshot.get("status", {})
    wan = snapshot.get("wan_info", {})
    wifi = snapshot.get("wifi_detail", {})
    dev_list = snapshot.get("device_list", {})
    mac_bind = snapshot.get("mac_bind", {})
    port_fwd = snapshot.get("port_forward", {})
    reboot = snapshot.get("reboot_task", {})
    led = snapshot.get("led_status", {})

    router_name = init.get("routername") or init.get("displayName") or "Xiaomi Router"
    model = init.get("displayName") or init.get("hardware") or "Nieznany"
    rom = init.get("romversion") or "brak danych"
    uptime_sec = status.get("upTime") or status.get("uptime") or 0
    try:
        uptime_val = int(float(uptime_sec))
    except Exception:
        uptime_val = 0

    lines = []
    lines.append(f"# Raport Konfiguracji Routera: {router_name}")
    lines.append(f"> Raport audytowy wygenerowany przez: **Xiaomi Router Manager (XRM) v{APP_VERSION}**\n")
    lines.append(f"**Data wygenerowania:** {snapshot.get('fetch_date', datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))}  ")
    lines.append(f"**Adres routera:** `{snapshot.get('router_ip', '192.168.31.1')}`  ")
    lines.append(f"**Model sprzętowy:** {model} (kod: `{init.get('hardware', 'brak')}`)  ")
    lines.append(f"**Wersja oprogramowania:** {rom} (kod kraju: `{init.get('countrycode', 'CN')}`)  ")
    lines.append(f"**Czas pracy (uptime):** {format_uptime(uptime_val)}")
    lines.append("")

    # 1. Status sprzętowy
    lines.append("## 1. Status Sprzętowy i Zasoby")
    cpu_load = status.get("cpu", {}).get("load")
    if cpu_load is not None:
        try:
            c_val = float(cpu_load)
            if c_val > 1.0:
                c_val = c_val / 100.0
            cpu_str = f"{c_val * 100:.1f}%"
        except Exception:
            cpu_str = str(cpu_load)
    else:
        cpu_str = "brak danych"

    mem = status.get("mem", {})
    mem_usage = mem.get("usage")
    mem_total = mem.get("total")
    if mem_usage and mem_total:
        try:
            m_u = float(mem_usage)
            m_t = float(mem_total)
            if m_u > 1.0:
                m_u = m_u / 100.0
            mem_str = f"{format_bytes(m_u * m_t)} / {format_bytes(m_t)} ({m_u*100:.1f}%)"
        except Exception:
            mem_str = f"{mem_usage} (total {mem_total})"
    else:
        mem_str = "brak danych"

    wan_speed = status.get("wan", {})
    try:
        up_speed = format_speed(float(wan_speed.get("upspeed", 0)))
    except Exception:
        up_speed = "0 KB/s"
    try:
        down_speed = format_speed(float(wan_speed.get("downspeed", 0)))
    except Exception:
        down_speed = "0 KB/s"

    lines.append("| Parametr | Wartość |")
    lines.append("|---|---|")
    lines.append(f"| Obciążenie CPU | {cpu_str} |")
    lines.append(f"| Pamięć RAM | {mem_str} |")
    lines.append(f"| Aktualna prędkość pobierania (WAN) | {down_speed} |")
    lines.append(f"| Aktualna prędkość wysyłania (WAN) | {up_speed} |")
    lines.append("")

    # 2. Konfiguracja łącza WAN
    lines.append("## 2. Konfiguracja Łącza WAN (Internet)")
    wan_details = wan.get("info", {}) if isinstance(wan.get("info"), dict) else wan
    if wan_details:
        lines.append("| Parametr | Wartość |")
        lines.append("|---|---|")
        lines.append(f"| Typ połączenia | `{wan_details.get('details', {}).get('wanType', 'DHCP')}` |")
        lines.append(f"| Adres IP WAN | `{wan_details.get('ipv4', [{}])[0].get('ip', 'brak') if isinstance(wan_details.get('ipv4'), list) else wan_details.get('ip', 'brak')}` |")
        lines.append(f"| Maska podsieci | `{wan_details.get('ipv4', [{}])[0].get('mask', 'brak') if isinstance(wan_details.get('ipv4'), list) else 'brak'}` |")
        lines.append(f"| Brama domyślna WAN | `{wan_details.get('gateWay', 'brak')}` |")
        dns_list = []
        d_raw = wan_details.get("details", {}).get("dns") or wan_details.get("dnsServer")
        if isinstance(d_raw, list):
            dns_list.extend(str(x).strip() for x in d_raw if str(x).strip())
        elif isinstance(d_raw, str) and d_raw.strip():
            dns_list.append(d_raw.strip())
        for k in ["dnsAddrs", "dnsAddrs1", "dnsAddrs2"]:
            val = wan_details.get(k)
            if val and isinstance(val, str) and val.strip() and val.strip() not in dns_list:
                dns_list.append(val.strip())
        if not dns_list:
            pp_status = snapshot.get("pppoe_status", {})
            pp_dns = pp_status.get("dns") or pp_status.get("dnsServer") or pp_status.get("dns1")
            if isinstance(pp_dns, list):
                dns_list.extend(str(x).strip() for x in pp_dns if str(x).strip())
            elif isinstance(pp_dns, str) and pp_dns.strip():
                dns_list.append(pp_dns.strip())
            if pp_status.get("dns2") and str(pp_status.get("dns2")).strip() not in dns_list:
                dns_list.append(str(pp_status.get("dns2")).strip())
        dns_str = ", ".join(dns_list) if dns_list else "brak"
        lines.append(f"| Serwery DNS | `{dns_str}` |")
        lines.append(f"| Adres fizyczny (MAC WAN) | `{wan_details.get('mac', 'brak')}` |")
        w_mtu = wan_details.get('details', {}).get('mtu') or wan_details.get('mtu') or 'brak danych'
        lines.append(f"| Rozmiar jednostki MTU | `{w_mtu}` |")
        lines.append("")
    else:
        lines.append("*Brak danych o konfiguracji WAN.*\n")

    # 2b. Konfiguracja sieci LAN i DHCP
    lines.append("## 2b. Konfiguracja Sieci Lokalnej (LAN i DHCP)")
    lan_info = snapshot.get("lan_info", {}).get("info", {})
    dhcp_info = snapshot.get("lan_dhcp", {}).get("info", {})
    l_ip = lan_info.get("ipv4", [{}])[0].get("ip", "192.168.31.1") if isinstance(lan_info.get("ipv4"), list) and lan_info.get("ipv4") else "192.168.31.1"
    l_mask = lan_info.get("ipv4", [{}])[0].get("mask", "255.255.255.0") if isinstance(lan_info.get("ipv4"), list) and lan_info.get("ipv4") else "255.255.255.0"
    lines.append("| Parametr | Wartość |")
    lines.append("|---|---|")
    lines.append(f"| Adres IP Routera (Brama LAN) | `{l_ip}` |")
    lines.append(f"| Maska podsieci LAN | `{l_mask}` |")
    if dhcp_info:
        d_start = dhcp_info.get("start", "5")
        d_limit = dhcp_info.get("limit", "250")
        lines.append(f"| Pula adresów serwera DHCP | `od . {d_start} (limit: {d_limit} adresów)` |")
        lines.append(f"| Czas dzierżawy DHCP | `{dhcp_info.get('leasetime', '720m')}` |")
        d_dns1 = dhcp_info.get("dns1", "")
        d_dns2 = dhcp_info.get("dns2", "")
        lines.append(f"| Rozgłaszane DNS (DHCP) | `{d_dns1}{', ' + d_dns2 if d_dns2 else ''}` |")
    lines.append("")

    # 3. Konfiguracja sieci Wi-Fi
    lines.append("## 3. Konfiguracja Sieci Bezprzewodowych (Wi-Fi)")
    wifi_list = wifi.get("info", [])
    if isinstance(wifi_list, list) and wifi_list:
        lines.append("| Pasmo | Nazwa sieci (SSID) | Status | Kanał | Szerokość | Zabezpieczenie | Hasło |")
        lines.append("|---|---|---|---|---|---|---|")
        for idx, w in enumerate(wifi_list):
            w_idx = w.get("wifiIndex", idx + 1)
            band_type = str(w.get("band", ""))
            if band_type == "2g" or str(w_idx) == "1":
                band_name = "2.4 GHz"
            elif band_type == "5g" or str(w_idx) == "2":
                band_name = "5 GHz"
            elif band_type == "game" or str(w_idx) == "3":
                band_name = "5 GHz Gaming / Wi-Fi 7"
            elif band_type == "mlo":
                band_name = "Wi-Fi 7 MLO"
            else:
                band_name = band_type or f"Pasmo {idx+1}"

            ssid = w.get("ssid", "brak")
            status_on = "Włączone" if str(w.get("status")) == "1" else "Wyłączone"
            
            ch_raw = str(w.get("channel", "0"))
            ch_info = w.get("channelInfo", {})
            cur_ch = ch_info.get("channel")
            if ch_raw in ("0", "Auto") and cur_ch:
                ch_str = f"Auto ({cur_ch})"
            else:
                ch_str = ch_raw

            b_list = ch_info.get("bandList", [])
            bw_cfg = str(w.get("bandwidth", "0"))
            if bw_cfg not in ("0", "Auto", ""):
                bw_str = f"{bw_cfg} MHz"
            elif "160" in b_list:
                bw_str = "Auto (do 160 MHz)"
            elif "40" in b_list:
                bw_str = "Auto (do 40 MHz)"
            else:
                bw_str = "Auto"

            security = str(w.get("encryption", "WPA2/WPA3"))
            pwd = w.get("password", "")
            if mask_passwords and pwd:
                pwd_display = f"`{'*' * len(pwd)}`"
            elif pwd:
                pwd_display = f"`{pwd}`"
            else:
                pwd_display = "*brak (otwarta)*"

            lines.append(f"| {band_name} | `{ssid}` | {status_on} | {ch_str} | {bw_str} | {security} | {pwd_display} |")
        lines.append("")

        # Zaawansowane opcje Wi-Fi
        lines.append("### Zaawansowane Opcje Wi-Fi")
        first_w = wifi_list[0] if wifi_list else {}
        w5_compat = "Włączony (Wi-Fi 6 wyłączone)" if str(first_w.get("ax", "1")) == "0" else "Wyłączony (Wi-Fi 6/7 aktywne)"
        lines.append(f"- **Tryb zgodności z Wi-Fi 5 (Wi-Fi 5 兼容模式):** {w5_compat}")

        twt_data = snapshot.get("twt", {})
        twt_on = "Włączony" if isinstance(twt_data, dict) and str(twt_data.get("status")) == "1" else "Wyłączony"
        lines.append(f"- **Oszczędzanie energii TWT (TWT节能模式):** {twt_on}")

        txbf_on = "Włączone" if str(first_w.get("txbf", "0")) in ("1", "3") else "Wyłączone"
        lines.append(f"- **MU-MIMO i Beamforming:** {txbf_on}")

        miot_data = snapshot.get("miotrelay", {})
        miot_on = "Włączone" if isinstance(miot_data, dict) and str(miot_data.get("switch")) == "1" else "Wyłączone"
        lines.append(f"- **Szybkie parowanie Xiaomi (畅快连 - Mi Connect):** {miot_on}")

        silence_data = snapshot.get("wifi_silence", {})
        silence_on = "Włączony (Wi-Fi wyłączone do restartu)" if isinstance(silence_data, dict) and str(silence_data.get("status")) == "1" else "Wyłączony"
        lines.append(f"- **Tryb cichy Wi-Fi (静默模式):** {silence_on}")

        aimesh_data = snapshot.get("aimesh", {})
        if isinstance(aimesh_data, dict):
            m_roam = "Ręczne progi" if str(aimesh_data.get("manual_roaming_setting")) == "1" else "Automatyczny"
            r1 = aimesh_data.get("roam_rssi_threshold1", "-65")
            r2 = aimesh_data.get("roam_rssi_threshold2", "-70")
            lines.append(f"- **Parametry roamingu Mesh (手动设置漫游参数):** {m_roam} (Próg 2.4G: {r1} dBm, Próg 5G: {r2} dBm)")
        lines.append("")
    else:
        lines.append("*Brak szczegółowych danych Wi-Fi.*\n")

    # 4. Podłączone urządzenia
    lines.append("## 4. Urządzenia Podłączone do Routera")
    devices = dev_list.get("list", [])
    if isinstance(devices, list) and devices:
        lines.append(f"Łącznie wykrytych urządzeń: **{len(devices)}**\n")
        lines.append("| Nazwa urządzenia | Adres IP | Adres MAC | Połączenie | Pasmo / Port | Transfer Down | Transfer Up |")
        lines.append("|---|---|---|---|---|---|---|")
        for dev in devices:
            d_name = dev.get("name") or dev.get("oname") or "Nieznane"
            d_ip = dev.get("ip", [{}])[0].get("ip") if isinstance(dev.get("ip"), list) and dev.get("ip") else dev.get("ip", "brak")
            d_mac = dev.get("mac", "brak")
            is_ap = safe_int(dev.get("isap", 0)) > 0
            is_type = safe_int(dev.get("type", 0))
            type_names = {
                0: "Kabel (LAN)",
                1: "Wi-Fi 2.4G",
                2: "Wi-Fi 5G",
                3: "Wi-Fi 5G Game",
                4: "Wi-Fi 5G-2",
                5: "Wi-Fi 6G",
                6: "Wi-Fi Gość",
                7: "Wi-Fi 7 MLO",
                8: "Wi-Fi IoT"
            }
            if is_ap:
                conn_type = "Mesh"
                carrier = dev.get("carrier") or "Węzeł Mesh"
            elif is_type == 0:
                conn_type = "Kabel (LAN)"
                carrier = dev.get("carrier") or "LAN"
            else:
                conn_type = "Wi-Fi"
                carrier = dev.get("carrier") or type_names.get(is_type, "Wi-Fi")
            stat = dev.get("statistics") or {}
            down_sp = format_speed(float(stat.get("downspeed", 0)))
            up_sp = format_speed(float(stat.get("upspeed", 0)))

            lines.append(f"| {d_name} | `{d_ip}` | `{d_mac}` | {conn_type} | {carrier} | {down_sp} | {up_sp} |")
        lines.append("")
    else:
        lines.append("*Brak podłączonych urządzeń lub brak danych.*\n")

    # 5. Rezerwacje adresów IP (DHCP Static / Mac Bind)
    lines.append("## 5. Rezerwacje Adresów IP (DHCP Static Leases)")
    binds = mac_bind.get("list", [])
    if isinstance(binds, list) and binds:
        lines.append("| Nazwa / Opis | Przypisany IP | Adres MAC |")
        lines.append("|---|---|---|")
        for b in binds:
            b_name = b.get("name") or "Brak opisu"
            b_ip = b.get("ip", "brak")
            b_mac = b.get("mac", "brak")
            lines.append(f"| {b_name} | `{b_ip}` | `{b_mac}` |")
        lines.append("")
    else:
        lines.append("*Brak skonfigurowanych statycznych rezerwacji DHCP w sekcji mac_bind.*\n")

    # 5b. Przekierowanie Portów i NAT
    lines.append("## 5b. Przekierowanie Portów i NAT")
    pf_single = port_fwd.get("single", []) if isinstance(port_fwd, dict) else []
    pf_range = port_fwd.get("range", []) if isinstance(port_fwd, dict) else []
    pf_dmz = port_fwd.get("dmz", {}) if isinstance(port_fwd, dict) else {}
    pf_upnp = port_fwd.get("upnp", {}) if isinstance(port_fwd, dict) else {}

    proto_map = {1: "TCP", 2: "UDP", 3: "TCP/UDP"}

    lines.append("### Przekierowania Pojedynczych Portów")
    if pf_single:
        lines.append("| Nazwa reguły | Protokół | Port zewnętrzny (WAN) | Docelowy adres LAN | Port wewnętrzny |")
        lines.append("|---|---|---|---|---|")
        for r in pf_single:
            r_name = r.get("name") or "Reguła"
            r_proto = proto_map.get(safe_int(r.get("proto", 1)), str(r.get("proto", 1)))
            r_sport = r.get("srcport", "brak")
            r_ip = r.get("destip", "brak")
            r_dport = r.get("destport", "brak")
            lines.append(f"| {r_name} | {r_proto} | `{r_sport}` | `{r_ip}` | `{r_dport}` |")
        lines.append("")
    else:
        lines.append("*Brak aktywnych przekierowań pojedynczych portów.*\n")

    lines.append("### Przekierowania Zakresów Portów")
    if pf_range:
        lines.append("| Nazwa zakresu | Protokół | Zakres portów (WAN) | Docelowy adres LAN |")
        lines.append("|---|---|---|---|")
        for r in pf_range:
            r_name = r.get("name") or "Zakres"
            r_proto = proto_map.get(safe_int(r.get("proto", 1)), str(r.get("proto", 1)))
            sport_obj = r.get("srcport", {})
            if isinstance(sport_obj, dict):
                r_range = f"{sport_obj.get('f', '?')} - {sport_obj.get('t', '?')}"
            else:
                r_range = str(sport_obj)
            r_ip = r.get("destip", "brak")
            lines.append(f"| {r_name} | {r_proto} | `{r_range}` | `{r_ip}` |")
        lines.append("")
    else:
        lines.append("*Brak aktywnych przekierowań zakresów portów.*\n")

    dmz_st = safe_int(pf_dmz.get("status", 2))
    dmz_ip = pf_dmz.get("ip") or pf_dmz.get("lanip") or "Brak"
    dmz_txt = f"WŁĄCZONY (Docelowy IP: `{dmz_ip}`)" if dmz_st == 1 else "Wyłączony"

    upnp_st = safe_int(pf_upnp.get("status", 0))
    upnp_txt = "WŁĄCZONY" if upnp_st == 1 else "Wyłączony"

    lines.append(f"- **Strefa zdemilitaryzowana (DMZ):** {dmz_txt}")
    lines.append(f"- **Protokół UPnP:** {upnp_txt}")
    lines.append("")

    # 5c. Usługi Sieciowe (QoS, DDNS, VPN)
    lines.append("## 5c. Zaawansowane Usługi Sieciowe (QoS, DDNS, VPN)")
    qos_data = snapshot.get("qos", {})
    qos_st = qos_data.get("status", {}) if isinstance(qos_data, dict) else {}
    qos_on = safe_int(qos_st.get("on", 0)) == 1
    qos_mode_map = {0: "Automatyczny (Smart)", 1: "Priorytet Gier", 2: "Przeglądanie Stron", 3: "Wideo / Streaming"}
    qos_mode_str = qos_mode_map.get(safe_int(qos_st.get("mode", 0)), "Standardowy")
    qos_band = qos_data.get("band", {}) if isinstance(qos_data, dict) else {}
    lines.append(f"- **Inteligentny QoS:** {'WŁĄCZONY' if qos_on else 'Wyłączony'} (Tryb: {qos_mode_str})")
    lines.append(f"  - Zadeklarowane pasmo WAN: Pobieranie `{qos_band.get('download', 0)} Mbps`, Wysyłanie `{qos_band.get('upload', 0)} Mbps`")

    ddns_data = snapshot.get("ddns", {})
    ddns_list = ddns_data.get("list", []) if isinstance(ddns_data, dict) else []
    lines.append(f"- **Dynamiczny DNS (DDNS):** Skonfigurowane usługi: {len(ddns_list)}")
    if ddns_list:
        for d in ddns_list:
            lines.append(f"  - Usługa: `{d.get('service')}`, Domena: `{d.get('domain')}`, Stan: {'Włączona' if d.get('on') == 1 else 'Wyłączona'}")

    vpn_status = snapshot.get("vpn_status", {})
    vpn_st_val = safe_int(vpn_status.get("status", 0))
    vpn_txt = "POŁĄCZONY" if vpn_st_val == 1 else "Rozłączony"
    lines.append(f"- **Klient VPN:** {vpn_txt}")
    lines.append("")

    # 5d. Sterowanie Portami Fizycznymi (2.5G)
    lines.append("## 5d. Porty Fizyczne i Funkcje Sprzętowe (4x 2.5 Gbps)")
    ps_map = snapshot.get("ps_map", {})
    ps_list = (ps_map.get("ports") or ps_map.get("list") or []) if isinstance(ps_map, dict) else []
    if ps_list:
        lines.append("| Port fizyczny | Rola sieciowa | Prędkość linku |")
        lines.append("|---|---|---|")
        for p in ps_list:
            p_id = p.get("label") or f"Port {p.get('port', '?')}"
            svc = str(p.get("service", "lan")).lower()
            p_role = "WAN (Główny Internet)" if svc == "wan" else ("LAN" if svc == "lan" else str(p.get("service")))
            p_speed = f"{p.get('speed', '2.5G')}"
            lines.append(f"| {p_id} (2.5G) | {p_role} | {p_speed} |")
        lines.append("")

    ps_services = snapshot.get("ps_services", {})
    if isinstance(ps_services, dict):
        mwan = ps_services.get("multiwan", {})
        mwan_on = mwan.get("wan2Switch") == "1" or mwan.get("enable") == "1"
        lag = ps_services.get("lag", {})
        lag_on = lag.get("enable") == "1" or lag.get("lagSwitch") == "1"
        iptv = ps_services.get("iptv", {})
        iptv_on = iptv.get("enable") == "1" or iptv.get("iptvSwitch") == "1"
        game = ps_services.get("game", {})
        game_on = game.get("enable") == "1" or game.get("gameSwitch") == "1"

        lines.append(f"- **Dual WAN (Drugi port WAN):** {'WŁĄCZONY' if mwan_on else 'Wyłączony'}")
        lines.append(f"- **Agregacja portów LAN (LAG):** {'WŁĄCZONA' if lag_on else 'Wyłączona'}")
        lines.append(f"- **Telewizja IP (IPTV STB):** {'WŁĄCZONA' if iptv_on else 'Wyłączona'}")
        lines.append(f"- **Dedykowany Port Gry (Gaming Port):** {'WŁĄCZONY' if game_on else 'Wyłączony'}")
        lines.append("")

    # 6. Usługi Systemowe i Magazyn USB
    lines.append("## 6. Pamięć Masowa USB i Usługi Dyskowe (Kopia Zapasowa)")
    stor = snapshot.get("storage_info", {})
    samba_enable = "Włączona" if str(stor.get("samba", {}).get("enable")) == "1" else "Wyłączona"
    usb3_u3 = "Włączona (tryb USB 2.0)" if str(stor.get("usb3", {}).get("enable")) == "1" else "Wyłączona (pełna prędkość USB 3.0)"
    swap_info = stor.get("swap", {})
    swap_str = f"Rozmiar: {swap_info.get('size', 0)} MB, Użyto: {swap_info.get('swapused', 0)} MB"
    usb_devs = stor.get("devices", [])

    lines.append(f"- **Serwer plików Samba:** {samba_enable}")
    lines.append(f"- **Redukcja zakłóceń USB 3.0 (ochrona Wi-Fi 2.4G):** {usb3_u3}")
    lines.append(f"- **Pamięć wymiany (SWAP):** {swap_str}")
    if usb_devs:
        lines.append(f"- **Wykryte napędy USB:** {len(usb_devs)} szt.")
        for d in usb_devs:
            lines.append(f"  * {d.get('name', 'Pamięć USB')} ({d.get('capacity', 'brak pojemności')})")
    else:
        lines.append("- **Wykryte napędy USB:** Brak podłączonych pamięci masowych")
    lines.append("")

    # 7. Usługi i narzędzia
    lines.append("## 7. Usługi Systemowe i Narzędzia")
    led_state = led.get("status") if isinstance(led, dict) else None
    led_str = "Włączone" if str(led_state) == "1" else ("Wyłączone" if str(led_state) == "0" else "brak danych")
    reboot_info = reboot.get("task", {}) if isinstance(reboot, dict) else {}
    reboot_str = reboot_info.get("desc") or ("Włączony" if reboot_info.get("enable") else "Brak harmonogramu")

    lines.append(f"- **Diody LED:** {led_str}")
    lines.append(f"- **Harmonogram restartu:** {reboot_str}")
    lines.append("")

    # Zapis do pliku
    content = "\n".join(lines)
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(content)

    return output_path


if __name__ == "__main__":
    import json
    base_dir = os.path.dirname(os.path.abspath(__file__))
    snap_path = os.path.join(base_dir, "last_snapshot.json")
    out_path = os.path.join(base_dir, "test_raport.md")
    if os.path.exists(snap_path):
        with open(snap_path, "r", encoding="utf-8") as f:
            snapshot_data = json.load(f)
        export_snapshot_to_markdown(snapshot_data, out_path)
        print(f"Pomyślnie wygenerowano raport: {out_path}")

