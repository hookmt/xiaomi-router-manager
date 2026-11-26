import base64
import hashlib
import json
import random
import re
import subprocess
import time
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional

try:
    from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
    from cryptography.hazmat.primitives import padding
    HAVE_CRYPTO = True
except ImportError:
    HAVE_CRYPTO = False


class MiWiFiClient:
    PUBLIC_KEY = "a2ffa5c9be07488bbb04a3a47d3c5f6a"

    def __init__(self, ip: Optional[str] = None):
        self.ip = ip or self.discover_gateway()
        self.stok: Optional[str] = None
        self.init_info: Dict[str, Any] = {}
        self.device_id: Optional[str] = None
        self.new_encrypt_mode: int = 0
        self.connected: bool = False

    @staticmethod
    def discover_gateway() -> str:
        """Automatyczne wykrywanie IP routera (bramy domyślnej) w Windowsie."""
        try:
            res = subprocess.run(
                ["ipconfig"],
                capture_output=True,
                encoding="cp852",
                errors="ignore"
            )
            matches = re.findall(
                r"(?:Default Gateway|Brama domy[śs]lna)[ .]*:\s*([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)",
                res.stdout
            )
            for gw in matches:
                if gw != "0.0.0.0":
                    return gw
        except Exception:
            pass
        return "192.168.31.1"

    def probe(self) -> Dict[str, Any]:
        """Pobiera podstawowe informacje z routera (init_info) bez uwierzytelniania."""
        url = f"http://{self.ip}/cgi-bin/luci/api/xqsystem/init_info"
        req = urllib.request.Request(url, headers={"User-Agent": "MiWiFi-Manager/1.0"})
        with urllib.request.urlopen(req, timeout=4) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="ignore"))
            self.init_info = data
            self.new_encrypt_mode = int(data.get("newEncryptMode", 0))
            self.device_id = data.get("id") or data.get("routerId")
            return data

    def extract_stok(self, text: str) -> Optional[str]:
        """Wyciąga token stok z czystego tokena lub pełnego linku wklejonego z przeglądarki."""
        text = text.strip()
        match = re.search(r";stok=([a-zA-Z0-9_\-]+)", text)
        if match:
            return match.group(1)
        if re.fullmatch(r"[a-zA-Z0-9_\-]+", text) and len(text) >= 16:
            return text
        return None

    def login_with_stok(self, stok_or_url: str) -> bool:
        """Logowanie przez gotowy token stok lub link strony głównej."""
        token = self.extract_stok(stok_or_url)
        if not token:
            return False
        self.stok = token
        # Test czy token jest ważny
        try:
            res = self.get_status()
            if res.get("code") == 0:
                self.connected = True
                return True
        except Exception:
            pass
        self.stok = None
        self.connected = False
        return False

    def login_with_password(self, password: str, username: str = "admin") -> bool:
        """Autologowanie hasłem z wyliczeniem SHA-256 (dla newEncryptMode=1) lub SHA-1."""
        if not self.init_info:
            self.probe()

        # Wyciągnięcie deviceId jeśli nie ma w init_info
        device_mac = self.device_id
        if not device_mac or "/" in str(device_mac):
            # Spróbuj pobrać MAC z nagłówka strony logowania
            try:
                url_web = f"http://{self.ip}/cgi-bin/luci/web"
                with urllib.request.urlopen(url_web, timeout=4) as r:
                    html = r.read().decode("utf-8", errors="ignore")
                    m = re.search(r"deviceId\s*:\s*['\"]([^'\"]+)['\"]", html)
                    if m:
                        device_mac = m.group(1)
            except Exception:
                pass

        if not device_mac:
            device_mac = "00:00:00:00:00:00"  # fallback neutralny

        # Generowanie nonce: 0_MAC_TIMESTAMP_RANDOM
        ts = int(time.time())
        rand = random.randint(1000, 9999)
        nonce = f"0_{device_mac}_{ts}_{rand}"

        # Szyfrowanie hasła
        if self.new_encrypt_mode == 1:
            inner = hashlib.sha256((password + self.PUBLIC_KEY).encode()).hexdigest()
            pwd_hash = hashlib.sha256((nonce + inner).encode()).hexdigest()
        else:
            inner = hashlib.sha1((password + self.PUBLIC_KEY).encode()).hexdigest()
            pwd_hash = hashlib.sha1((nonce + inner).encode()).hexdigest()

        # Żądanie logowania
        login_url = f"http://{self.ip}/cgi-bin/luci/api/xqsystem/login"
        payload = urllib.parse.urlencode({
            "username": username,
            "password": pwd_hash,
            "logtype": "2",
            "nonce": nonce
        }).encode("utf-8")

        req = urllib.request.Request(
            login_url,
            data=payload,
            headers={"User-Agent": "MiWiFi-Manager/1.0", "Content-Type": "application/x-www-form-urlencoded"}
        )

        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8", errors="ignore"))
                if data.get("code") == 0 and "token" in data:
                    self.stok = data["token"]
                    self.connected = True
                    return True
                elif data.get("code") == 0 and "url" in data:
                    token = self.extract_stok(data["url"])
                    if token:
                        self.stok = token
                        self.connected = True
                        return True
        except Exception:
            pass

        self.connected = False
        return False

    def api_request(self, endpoint: str, method: str = "GET", data: Optional[Dict[str, Any]] = None, timeout: Optional[int] = None) -> Dict[str, Any]:
        """Wykonanie zapytania do API z aktywnym stok."""
        if not self.stok:
            raise RuntimeError("Brak aktywnego tokena autoryzacji (stok).")

        clean_ep = endpoint.lstrip("/")
        url = f"http://{self.ip}/cgi-bin/luci/;stok={self.stok}/{clean_ep}"

        req_data = None
        headers = {"User-Agent": "MiWiFi-Manager/1.0"}
        if data is not None:
            req_data = urllib.parse.urlencode(data).encode("utf-8")
            headers["Content-Type"] = "application/x-www-form-urlencoded"

        req_timeout = timeout if timeout is not None else 10
        req = urllib.request.Request(url, data=req_data, headers=headers, method=method)
        with urllib.request.urlopen(req, timeout=req_timeout) as resp:
            return json.loads(resp.read().decode("utf-8", errors="ignore"))

    # --- Metody odczytu stanu (GET) ---

    def get_status(self) -> Dict[str, Any]:
        """Pobiera status sprzętowy (CPU, RAM, transfer WAN, uptime)."""
        return self.api_request("api/misystem/status")

    def get_device_list(self) -> Dict[str, Any]:
        """Pobiera listę podłączonych urządzeń wraz z transferami i pasmem."""
        return self.api_request("api/misystem/devicelist")

    def get_wifi_detail(self) -> Dict[str, Any]:
        """Pobiera szczegóły pasm Wi-Fi (SSID, kanały, moce, hasła)."""
        return self.api_request("api/xqnetwork/wifi_detail_all")

    def get_wan_info(self) -> Dict[str, Any]:
        """Pobiera parametry łącza WAN (IP, brama, DNS, typ)."""
        return self.api_request("api/xqnetwork/wan_info")

    def get_mac_bind(self) -> Dict[str, Any]:
        """Pobiera listę powiązań IP/MAC (rezerwacje DHCP / adresy statyczne)."""
        try:
            return self.api_request("api/xqnetwork/macbind_info")
        except Exception:
            return {}

    def get_lan_info(self) -> Dict[str, Any]:
        """Pobiera parametry sieci LAN (adres IP routera, maska, status fizycznych portów linkList)."""
        try:
            return self.api_request("api/xqnetwork/lan_info")
        except Exception:
            return {}

    def get_lan_dhcp(self) -> Dict[str, Any]:
        """Pobiera parametry serwera DHCP LAN (zakresy IP, czas dzierżawy, serwery DNS)."""
        try:
            return self.api_request("api/xqnetwork/lan_dhcp")
        except Exception:
            return {}

    def get_storage_info(self) -> Dict[str, Any]:
        """Pobiera parametry pamięci masowej USB, Samby i swapu pod kątem backupu."""
        res = {"devices": [], "samba": {}, "usb3": {}, "swap": {}}
        try:
            res["devices"] = self.api_request("api/misystem/get_storage_device_list").get("deviceList", [])
        except Exception:
            pass
        try:
            res["samba"] = self.api_request("api/misystem/get_samba_status")
        except Exception:
            pass
        try:
            res["usb3"] = self.api_request("api/misystem/get_usb_u3")
        except Exception:
            pass
        try:
            res["swap"] = self.api_request("api/misystem/get_swap_info")
        except Exception:
            pass
        return res

    # --- Przekierowanie Portów, DMZ i UPnP ---

    def get_port_forward_single(self) -> Dict[str, Any]:
        """Pobiera listę przekierowań pojedynczych portów."""
        try:
            return self.api_request("api/xqsystem/portforward?ftype=1")
        except Exception as e:
            return {"error": str(e), "list": []}

    def get_port_forward_range(self) -> Dict[str, Any]:
        """Pobiera listę przekierowań zakresów portów."""
        try:
            return self.api_request("api/xqsystem/portforward?ftype=2")
        except Exception as e:
            return {"error": str(e), "list": []}

    def get_port_forward(self) -> Dict[str, Any]:
        """Pobiera kompletną strukturę NAT: pojedyncze porty, zakresy, DMZ i UPnP."""
        single = self.get_port_forward_single()
        range_pf = self.get_port_forward_range()
        dmz = self.get_dmz()
        upnp = self.get_upnp()
        return {
            "code": 0,
            "single": single.get("list", []) if isinstance(single, dict) else [],
            "range": range_pf.get("list", []) if isinstance(range_pf, dict) else [],
            "dmz": dmz if isinstance(dmz, dict) else {},
            "upnp": upnp if isinstance(upnp, dict) else {},
            "lanmask": single.get("lanmask", "255.255.255.0")
        }

    def add_port_redirect(self, name: str, ip: str, sport: int, dport: int, proto: int = 1, force: int = 1) -> Dict[str, Any]:
        """Dodaje lub aktualizuje regułę przekierowania pojedynczego portu (proto: 1=TCP, 2=UDP, 3=ALL)."""
        data = {
            "name": name,
            "ip": ip,
            "sport": str(sport),
            "dport": str(dport),
            "proto": str(proto)
        }
        res = self.api_request("api/xqsystem/add_redirect", method="POST", data=data)
        try:
            self.api_request("api/xqsystem/redirect_apply", method="POST", data={})
        except Exception:
            pass
        return res

    def add_range_redirect(self, name: str, ip: str, fport: int, tport: int, proto: int = 1, force: int = 1) -> Dict[str, Any]:
        """Dodaje lub aktualizuje regułę przekierowania zakresu portów (fport=od, tport=do)."""
        data = {
            "name": name,
            "ip": ip,
            "fport": str(fport),
            "tport": str(tport),
            "proto": str(proto)
        }
        res = self.api_request("api/xqsystem/add_range_redirect", method="POST", data=data)
        try:
            self.api_request("api/xqsystem/redirect_apply", method="POST", data={})
        except Exception:
            pass
        return res

    def delete_redirect(self, port: int, proto: Optional[int] = None) -> Dict[str, Any]:
        """Usuwa regułę przekierowania portu lub zakresu."""
        data = {"port": str(port)}
        if proto is not None:
            data["proto"] = str(proto)
        res = self.api_request("api/xqsystem/delete_redirect", method="POST", data=data)
        try:
            self.api_request("api/xqsystem/redirect_apply", method="POST")
        except Exception:
            pass
        return res

    def get_dmz(self) -> Dict[str, Any]:
        """Pobiera status strefy DMZ."""
        try:
            return self.api_request("api/xqsystem/dmz")
        except Exception as e:
            return {"error": str(e)}

    def set_dmz(self, ip: str) -> Dict[str, Any]:
        """Włącza DMZ i ustawia docelowy adres IP."""
        return self.api_request("api/xqsystem/set_dmz", method="POST", data={"ip": ip})

    def disable_dmz(self) -> Dict[str, Any]:
        """Wyłącza strefę DMZ."""
        res = self.api_request("api/xqsystem/dmz_off")
        try:
            self.api_request("api/xqsystem/dmz_reload")
        except Exception:
            pass
        return res

    def get_upnp(self) -> Dict[str, Any]:
        """Pobiera status UPnP i listę aktywnych reguł."""
        try:
            return self.api_request("api/xqsystem/upnp")
        except Exception as e:
            return {"error": str(e), "list": []}

    def set_upnp(self, switch_on: int) -> Dict[str, Any]:
        """Włącza (1) lub wyłącza (0) usługę UPnP."""
        return self.api_request(f"api/xqsystem/upnp_switch?switch={switch_on}")

    # --- QoS (Zarządzanie Pasmem) ---

    def get_qos_info(self) -> Dict[str, Any]:
        """Pobiera konfigurację QoS, pasmo łącza i limity per urządzenie."""
        try:
            return self.api_request("api/misystem/qos_info")
        except Exception as e:
            return {"error": str(e)}

    def set_qos_switch(self, on: int) -> Dict[str, Any]:
        """Włącza (1) lub wyłącza (0) usługę QoS."""
        return self.api_request(f"api/misystem/qos_switch?on={on}")

    def set_qos_mode(self, mode: int) -> Dict[str, Any]:
        """Ustawia tryb QoS: 0=Automatyczny, 1=Priorytet gier, 2=Przeglądanie stron, 3=Wideo."""
        return self.api_request(f"api/misystem/qos_mode?mode={mode}")

    def set_qos_band(self, upload: int, download: int) -> Dict[str, Any]:
        """Ustawia deklarowane pasmo łącza WAN (w Mbps)."""
        return self.api_request(f"api/misystem/set_band?upload={upload}&download={download}")

    def set_qos_limit(self, mac: str, up: int, down: int) -> Dict[str, Any]:
        """Ustawia limit prędkości dla danego urządzenia (w KB/s)."""
        return self.api_request(f"api/misystem/qos_limit?mac={mac}&up={up}&down={down}")

    # --- DDNS (Dynamiczny DNS) ---

    def get_ddns(self) -> Dict[str, Any]:
        """Pobiera listę skonfigurowanych usług DDNS."""
        try:
            return self.api_request("api/xqnetwork/ddns")
        except Exception as e:
            return {"error": str(e), "list": []}

    def set_ddns_switch(self, service_id: int, on: int) -> Dict[str, Any]:
        """Włącza (1) lub wyłącza (0) daną usługę DDNS."""
        return self.api_request(f"api/xqnetwork/ddns_switch?id={service_id}&on={on}")

    def reload_ddns(self, service_id: int) -> Dict[str, Any]:
        """Wymusza natychmiastowe odświeżenie adresu IP dla danej usługi DDNS."""
        return self.api_request(f"api/xqnetwork/ddns_reload?id={service_id}")

    def delete_ddns(self, service_id: int) -> Dict[str, Any]:
        """Usuwa usługę DDNS."""
        return self.api_request(f"api/xqnetwork/ddns_del?id={service_id}")

    def add_ddns(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Dodaje nową usługę DDNS."""
        return self.api_request("api/xqnetwork/ddns_add", method="POST", data=data)

    def edit_ddns(self, service_id: int, data: Dict[str, Any]) -> Dict[str, Any]:
        """Modyfikuje istniejącą usługę DDNS."""
        payload = dict(data)
        payload["id"] = str(service_id)
        return self.api_request("api/xqnetwork/ddns_edit", method="POST", data=payload)

    # --- VPN (Klient VPN i Smart VPN) ---

    def get_vpn_list(self) -> Dict[str, Any]:
        """Pobiera listę skonfigurowanych połączeń VPN klienta."""
        try:
            return self.api_request("api/xqsystem/vpn")
        except Exception as e:
            return {"error": str(e), "list": []}

    def get_vpn_status(self) -> Dict[str, Any]:
        """Pobiera bieżący stan połączenia VPN (0=rozłączony, 1=łączenie, 2=połączony)."""
        try:
            return self.api_request("api/xqsystem/vpn_status")
        except Exception as e:
            return {"error": str(e)}

    def connect_vpn(self, vpn_id: int) -> Dict[str, Any]:
        """Nawiązuje połączenie z profilem VPN."""
        return self.api_request(f"api/xqsystem/vpn_connect?id={vpn_id}")

    def disconnect_vpn(self) -> Dict[str, Any]:
        """Rozłącza aktywne połączenie VPN."""
        return self.api_request("api/xqsystem/vpn_disconnect")

    def set_vpn(self, proto: str, server: str, username: str, password: str, auto: int = 0, vpn_id: Optional[int] = None) -> Dict[str, Any]:
        """Dodaje lub edytuje profil VPN (proto: pptp lub l2tp)."""
        data = {
            "proto": proto,
            "server": server,
            "username": username,
            "password": password,
            "auto": str(auto)
        }
        if vpn_id is not None:
            data["id"] = str(vpn_id)
        return self.api_request("api/xqsystem/set_vpn", method="POST", data=data)

    def delete_vpn(self, vpn_id: int) -> Dict[str, Any]:
        """Usuwa profil VPN."""
        return self.api_request(f"api/xqsystem/del_vpn?id={vpn_id}")

    def get_smartvpn_info(self) -> Dict[str, Any]:
        """Pobiera stan inteligentnego dzielenia tunelu VPN (Smart VPN)."""
        try:
            return self.api_request("api/misystem/smartvpn_info")
        except Exception as e:
            return {"error": str(e)}

    def set_smartvpn_switch(self, enable: int, mode: int = 1) -> Dict[str, Any]:
        """Włącza (1) lub wyłącza (0) dzielenie ruchu Smart VPN (mode: 1=usługi/domeny, 2=urządzenia MAC)."""
        return self.api_request(f"api/misystem/smartvpn_switch?enable={enable}&mode={mode}")

    # --- Funkcje Portów Fizycznych (Dual WAN, LAG, IPTV, Gaming Port) ---

    def get_ps_map(self) -> Dict[str, Any]:
        """Pobiera mapowanie fizycznych portów sieciowych routera (np. 4x 2.5G)."""
        try:
            return self.api_request("api/misystem/get_ps_map")
        except Exception as e:
            return {"error": str(e), "ports": []}

    def get_ps_service(self, service: str) -> Dict[str, Any]:
        """Pobiera stan konkretnej usługi przypisanej do portów fizycznych (multiwan, lag, iptv, game)."""
        try:
            return self.api_request(f"api/misystem/get_ps_service?service={service}")
        except Exception as e:
            return {"error": str(e)}

    def set_ps_service(self, service: str, **kwargs) -> Dict[str, Any]:
        """Konfiguruje usługę portów fizycznych (multiwan, lag, iptv, game)."""
        data = {"service": service}
        for k, v in kwargs.items():
            if v is not None:
                data[k] = str(v)

        # Normalizacja parametrów pod specyfikację Xiaomi kernel/LuCI
        if service == "iptv":
            if "port" in kwargs and "ports" not in kwargs:
                data["ports"] = str(kwargs["port"])
                data.pop("port", None)
            if "profile" not in data:
                data["profile"] = "0"
            if "priority" not in data:
                data["priority"] = "-1"
            if "vid" not in data:
                data["vid"] = "-1"
        elif service == "game":
            if "port" in kwargs and "ports" not in kwargs:
                data["ports"] = str(kwargs["port"])
                data.pop("port", None)
        elif service == "lag":
            if "ports" in data and "," in data["ports"]:
                data["ports"] = data["ports"].replace(",", " ").strip()
            if "mode" not in data:
                data["mode"] = "2"

        return self.api_request("api/misystem/set_ps_service", method="POST", data=data, timeout=15)

    def get_router_name(self) -> Dict[str, Any]:
        """Pobiera nazwę routera."""
        try:
            return self.api_request("api/misystem/router_name")
        except Exception:
            return {}

    def get_led_status(self) -> Dict[str, Any]:
        """Pobiera stan diod LED."""
        try:
            return self.api_request("api/misystem/led")
        except Exception:
            return {}

    def get_reboot_task(self) -> Dict[str, Any]:
        """Pobiera harmonogram ponownego uruchamiania."""
        try:
            return self.api_request("api/xqsystem/reboot_task")
        except Exception:
            return {}

    def get_topo_graph(self) -> Dict[str, Any]:
        """Pobiera topologię sieci i węzły Mesh."""
        try:
            return self.api_request("api/misystem/topo_graph")
        except Exception:
            return {}

    # --- Metody sterowania i akcji ---

    def set_led(self, state: int) -> Dict[str, Any]:
        """Włącza (1) lub wyłącza (0) diody LED routera."""
        return self.api_request("api/misystem/led", method="POST", data={"state": str(state)})

    def reboot(self) -> Dict[str, Any]:
        """Wykonuje ponowne uruchomienie routera."""
        return self.api_request("api/xqsystem/reboot", method="GET")

    def factory_reset(self) -> Dict[str, Any]:
        """Wykonuje przywrócenie do ustawień fabrycznych (wymaga potwierdzeń w UI!)."""
        return self.api_request("api/xqsystem/reset", method="GET")

    def set_router_password(self, old_pwd: str, new_pwd: str) -> Dict[str, Any]:
        """Zmienia hasło administratora routera z użyciem natywnego szyfrowania AES-CBC."""
        if not self.connected or not self.stok:
            return {"code": -1, "error": "Brak aktywnego połączenia"}
        if not HAVE_CRYPTO:
            return {"code": -2, "error": "Brak biblioteki cryptography w środowisku Python"}

        # deviceId (klient MAC lub fallback neutralny)
        device_mac = self.device_id or "00:00:00:00:00:00"
        nonce = f"0_{device_mac}_{int(time.time())}_{random.randint(1000, 9999)}"
        key_str = self.PUBLIC_KEY
        iv_bytes = bytes.fromhex("64175472480004614961023454661220")

        # oldPwd
        old_hash = hashlib.sha256((old_pwd + key_str).encode("utf-8")).hexdigest()
        old_pwd_val = hashlib.sha256((nonce + old_hash).encode("utf-8")).hexdigest()

        # newPwd (AES SHA-1)
        k_sha1 = hashlib.sha1((old_pwd + key_str).encode("utf-8")).hexdigest()[:32]
        k_bytes_1 = bytes.fromhex(k_sha1)
        p_sha1 = hashlib.sha1((new_pwd + key_str).encode("utf-8")).hexdigest().encode("utf-8")
        padder1 = padding.PKCS7(128).padder()
        padded1 = padder1.update(p_sha1) + padder1.finalize()
        cipher1 = Cipher(algorithms.AES(k_bytes_1), modes.CBC(iv_bytes))
        enc1 = cipher1.encryptor()
        new_pwd_aes = base64.b64encode(enc1.update(padded1) + enc1.finalize()).decode("utf-8")

        # newPwd256 (AES SHA-256)
        k_sha256 = hashlib.sha256((old_pwd + key_str).encode("utf-8")).hexdigest()[:32]
        k_bytes_256 = bytes.fromhex(k_sha256)
        p_sha256 = hashlib.sha256((new_pwd + key_str).encode("utf-8")).hexdigest().encode("utf-8")
        padder256 = padding.PKCS7(128).padder()
        padded256 = padder256.update(p_sha256) + padder256.finalize()
        cipher256 = Cipher(algorithms.AES(k_bytes_256), modes.CBC(iv_bytes))
        enc256 = cipher256.encryptor()
        new_pwd_256_aes = base64.b64encode(enc256.update(padded256) + enc256.finalize()).decode("utf-8")

        data = {
            "nonce": nonce,
            "oldPwd": old_pwd_val,
            "newPwd": new_pwd_aes,
            "newPwd256": new_pwd_256_aes
        }
        return self.api_request("api/xqsystem/set_name_password", method="POST", data=data)

    def create_official_backup(self, keys: str = "mi_wifi_info,mi_network_info,mi_lan_info,mi_basic_info") -> Dict[str, Any]:
        """Zleca routerowi wygenerowanie oficjalnej binarnej kopii konfiguracji (.tar.gz)."""
        return self.api_request("api/misystem/c_backup", method="GET", data={"keys": keys})

    def download_official_backup(self, filename: str, output_path: str) -> bool:
        """Pobiera wygenerowany plik kopii zapasowej z routera i zapisuje go na dysku."""
        if not self.stok:
            return False
        url = f"http://{self.ip}/cgi-bin/luci/;stok={self.stok}/api/misystem/c_download/{filename}"
        req = urllib.request.Request(url, headers={"User-Agent": "MiWiFi-Manager/1.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            with open(output_path, "wb") as f:
                f.write(r.read())
        return True

    def restore_selective_snapshot(self, snapshot_data: Dict[str, Any], sections: Dict[str, bool]) -> Dict[str, Any]:
        """
        Selektywnie przywraca wybrane elementy konfiguracji ze snapshotu JSON:
        - mac_bind: statyczne rezerwacje adresów IP
        - port_forward: przekierowania pojedynczych portów i zakresów
        - wifi: ustawienia sieci Wi-Fi (SSID, hasła, kanały)
        - ps_services: usługi portów fizycznych (Dual WAN, LAG, IPTV, Gaming)
        - qos: reguły QoS i limity pasma
        """
        results = {"success": [], "errors": []}

        # 1. Rezerwacje DHCP (mac_bind)
        if sections.get("mac_bind"):
            bind_list = snapshot_data.get("mac_bind", {}).get("list", [])
            restored_count = 0
            for b in bind_list:
                mac = b.get("mac")
                ip = b.get("ip")
                name = b.get("name") or "Host"
                if mac and ip:
                    try:
                        res = self.add_mac_bind(mac=mac, ip=ip, name=name)
                        if res.get("code") == 0:
                            restored_count += 1
                        else:
                            results["errors"].append(f"Rezerwacja {name} ({ip}): kod {res.get('code')}")
                    except Exception as e:
                        results["errors"].append(f"Rezerwacja {name} ({ip}): {e}")
            results["success"].append(f"Przywrócono rezerwacji DHCP: {restored_count} z {len(bind_list)}")

        # 2. Przekierowania portów i zakresów (port_forward)
        if sections.get("port_forward"):
            pf_data = snapshot_data.get("port_forward", {})
            single_list = pf_data.get("single", [])
            range_list = pf_data.get("range", [])
            restored_single = 0
            restored_range = 0

            for r in single_list:
                name = r.get("name") or "Reguła"
                ip = r.get("destip")
                sport = r.get("srcport")
                dport = r.get("destport")
                proto = int(r.get("proto", 1))
                if ip and sport and dport:
                    try:
                        res = self.add_port_redirect(name=name, ip=ip, sport=int(sport), dport=int(dport), proto=proto, force=1)
                        if res.get("code") == 0:
                            restored_single += 1
                        else:
                            results["errors"].append(f"Port {name} ({sport}): kod {res.get('code')}")
                    except Exception as e:
                        results["errors"].append(f"Port {name} ({sport}): {e}")

            for r in range_list:
                name = r.get("name") or "Zakres"
                ip = r.get("destip")
                proto = int(r.get("proto", 1))
                src_obj = r.get("srcport", {})
                fport = src_obj.get("f") if isinstance(src_obj, dict) else src_obj
                tport = src_obj.get("t") if isinstance(src_obj, dict) else src_obj
                if ip and fport and tport:
                    try:
                        res = self.add_range_redirect(name=name, ip=ip, fport=int(fport), tport=int(tport), proto=proto, force=1)
                        if res.get("code") == 0:
                            restored_range += 1
                        else:
                            results["errors"].append(f"Zakres {name} ({fport}-{tport}): kod {res.get('code')}")
                    except Exception as e:
                        results["errors"].append(f"Zakres {name} ({fport}-{tport}): {e}")

            results["success"].append(f"Przywrócono przekierowań portów: {restored_single} pojedynczych, {restored_range} zakresów")

        # 3. Wi-Fi
        if sections.get("wifi"):
            wifi_info = snapshot_data.get("wifi_detail", {}).get("info", [])
            bsd = snapshot_data.get("wifi_detail", {}).get("bsd", 0)
            if len(wifi_info) >= 2:
                w1 = wifi_info[0]
                w2 = wifi_info[1]
                try:
                    res = self.set_all_wifi(
                        bsd=int(bsd),
                        wifi1={
                            "ssid": w1.get("ssid"),
                            "password": w1.get("password", ""),
                            "encryption": w1.get("encryption", "psk2"),
                            "channel": int(w1.get("channelInfo", {}).get("channel", 0)),
                            "bandwidth": int(w1.get("channelInfo", {}).get("bandwidth", 0)),
                            "txpwr": w1.get("txpwr", "max"),
                            "hidden": int(w1.get("hidden", 0)),
                            "on": int(w1.get("status", 1))
                        },
                        wifi2={
                            "ssid": w2.get("ssid"),
                            "password": w2.get("password", ""),
                            "encryption": w2.get("encryption", "psk2"),
                            "channel": int(w2.get("channelInfo", {}).get("channel", 0)),
                            "bandwidth": int(w2.get("channelInfo", {}).get("bandwidth", 0)),
                            "txpwr": w2.get("txpwr", "max"),
                            "hidden": int(w2.get("hidden", 0)),
                            "on": int(w2.get("status", 1))
                        }
                    )
                    if res.get("code") == 0:
                        results["success"].append("Przywrócono konfigurację sieci Wi-Fi (2.4G i 5G)")
                    else:
                        results["errors"].append(f"Wi-Fi: kod {res.get('code')}")
                except Exception as e:
                    results["errors"].append(f"Wi-Fi: {e}")

        # 4. Usługi portów fizycznych (ps_services)
        if sections.get("ps_services"):
            services = snapshot_data.get("ps_services", {})
            for svc_name in ["multiwan", "lag", "iptv", "game"]:
                svc_data = services.get(svc_name, {}).get(svc_name, {})
                if svc_data:
                    try:
                        res = self.set_ps_service(svc_name, **svc_data)
                        if res.get("code") == 0:
                            results["success"].append(f"Przywrócono usługę sprzętową: {svc_name}")
                        else:
                            results["errors"].append(f"Usługa {svc_name}: kod {res.get('code')}")
                    except Exception as e:
                        results["errors"].append(f"Usługa {svc_name}: {e}")

        # 5. QoS
        if sections.get("qos"):
            qos_data = snapshot_data.get("qos", {})
            st = qos_data.get("status", {})
            band = qos_data.get("band", {})
            try:
                if "on" in st:
                    self.set_qos_switch(int(st["on"]))
                if "mode" in st:
                    self.set_qos_mode(int(st["mode"]))
                if "upload" in band and "download" in band:
                    self.set_qos_band(int(band["upload"]), int(band["download"]))
                results["success"].append("Przywrócono konfigurację Inteligentnego QoS")
            except Exception as e:
                results["errors"].append(f"QoS: {e}")

        return results

    def scan_wifi_channels(self, poll_timeout: int = 35) -> Dict[str, Any]:
        """Uruchamia prawdziwy skan zatloczenia pasm Wi-Fi (api/misystem/channel_scan_start)
        i odpytuje api/misystem/channel_scan_result do zakonczenia (status == 0).
        """
        start_res = self.api_request("api/misystem/channel_scan_start", method="GET", timeout=15)
        if not isinstance(start_res, dict) or start_res.get("code") != 0:
            raise RuntimeError(f"channel_scan_start failed: {start_res}")

        deadline = time.time() + poll_timeout
        time.sleep(2.0)
        last_res: Dict[str, Any] = {}
        while time.time() < deadline:
            res = self.api_request("api/misystem/channel_scan_result", method="GET", timeout=15)
            last_res = res if isinstance(res, dict) else {}
            if last_res.get("code") == 0 and last_res.get("status") == 0:
                return last_res
            time.sleep(2.0)
        return last_res

    def optimize_wifi(self) -> Dict[str, Any]:
        """Wywołuje skanowanie i optymalizację kanałów Wi-Fi przez router."""
        return self.scan_wifi_channels()

    # --- Konfiguracja WAN ---

    def set_wan(self, wan_type: str, **kwargs) -> Dict[str, Any]:
        """
        Konfiguruje parametry łącza WAN:
        - wan_type: 'pppoe', 'dhcp', 'static'
        - kwargs dla pppoe: pppoeName, pppoePwd, mtu (np. 1472), dns1, dns2, peerdns ('0' lub '1')
        - kwargs dla dhcp: mtu (1500), dns1, dns2, peerdns ('0' lub '1')
        - kwargs dla static: staticIp, staticMask, staticGateway, mtu, dns1, dns2
        """
        data = {"wanType": wan_type}
        for k, v in kwargs.items():
            if v is not None:
                data[k] = str(v)
        return self.api_request("api/xqnetwork/set_wan", method="POST", data=data)

    def clone_mac(self, mac: str) -> Dict[str, Any]:
        """Klonuje adres MAC na interfejsie WAN (lub przywraca domyślny przy mac='')."""
        return self.api_request("api/xqnetwork/mac_clone", method="POST", data={"mac": mac})

    def pppoe_restart(self) -> Dict[str, Any]:
        """Restartuje sesję PPPoE."""
        try:
            self.api_request("api/xqnetwork/pppoe_stop")
            time.sleep(1)
        except Exception:
            pass
        return self.api_request("api/xqnetwork/pppoe_start")

    # --- Konfiguracja LAN i DHCP ---

    def set_lan_ip(self, ip: str, mask: str = "255.255.255.0") -> Dict[str, Any]:
        """Zmienia adres IP i maskę podsieci routera LAN."""
        return self.api_request("api/xqnetwork/set_lan_ip", method="POST", data={"ip": ip, "mask": mask})

    def set_lan_dhcp(self, start: int = 5, limit: Optional[int] = None, end: Optional[int] = None, leasetime: str = "720m", dns1: str = "", dns2: str = "") -> Dict[str, Any]:
        """
        Konfiguruje serwer DHCP LAN.
        Wysyła komplet parametrów wymaganych przez router Xiaomi BE7000:
        start, end, limit, leasetime (np. 120m), leasetimeNum, leasetimeUnit, ignore='0'.
        """
        start_val = int(start)
        if end is not None:
            end_val = int(end)
            limit_val = end_val - start_val + 1
        elif limit is not None:
            limit_val = int(limit)
            end_val = start_val + limit_val - 1
        else:
            end_val = 254
            limit_val = end_val - start_val + 1

        # Ograniczenia puli IP w OpenWrt/Xiaomi (zakres 2..254)
        start_val = max(2, min(start_val, 254))
        end_val = max(start_val, min(end_val, 254))
        limit_val = end_val - start_val + 1

        # Bezpieczne parsowanie leasetime (np. '120', '120m', '2h', '1d')
        lease_str = str(leasetime).strip()
        m = re.match(r"^(\d+)\s*([mhsd]?)$", lease_str, re.IGNORECASE)
        if m:
            lease_num = int(m.group(1))
            unit_raw = m.group(2).lower() if m.group(2) else "m"
            if unit_raw == "d":
                lease_num = lease_num * 24
                unit = "h"
            elif unit_raw == "s":
                lease_num = max(2, lease_num // 60)
                unit = "m"
            elif unit_raw in ("h", "m"):
                unit = unit_raw
            else:
                unit = "m"
        else:
            lease_num = 720
            unit = "m"

        # Walidacja limitów firmware Xiaomi:
        # unit == 'h' -> 1..48 godzin
        # unit == 'm' -> 2..2880 minut (od 2 min do 48h)
        if unit == "h":
            if lease_num < 1:
                lease_num = 1
            elif lease_num > 48:
                lease_num = 48
        else:
            if lease_num < 2:
                lease_num = 2
            elif lease_num > 2880:
                lease_num = 2880

        full_lease = f"{lease_num}{unit}"

        data = {
            "start": str(start_val),
            "end": str(end_val),
            "limit": str(limit_val),
            "leasetime": full_lease,
            "leasetimeNum": str(lease_num),
            "leasetimeUnit": unit,
            "ignore": "0"
        }
        if dns1:
            data["dns1"] = dns1
        if dns2:
            data["dns2"] = dns2
        return self.api_request("api/xqnetwork/set_lan_dhcp", method="POST", data=data, timeout=25)

    def add_mac_bind(self, mac: str, ip: str, name: str) -> Dict[str, Any]:
        """Dodaje rezerwację stałego adresu IP dla zadanego adresu MAC (DHCP Static Binding)."""
        data_json = json.dumps([{"ip": ip, "mac": mac, "name": name}])
        return self.api_request("api/xqnetwork/mac_bind", method="POST", data={"data": data_json})

    def remove_mac_bind(self, mac: str) -> Dict[str, Any]:
        """Usuwa rezerwację stałego adresu IP (DHCP Static Binding)."""
        return self.api_request("api/xqnetwork/mac_unbind", method="POST", data={"mac": mac})

    # --- Kontrola dostępu urządzeń ---

    def set_device_wan_access(self, mac: str, allow: bool) -> Dict[str, Any]:
        """Włącza (allow=True) lub blokuje (allow=False) dostęp do Internetu dla danego urządzenia po MAC."""
        wan_flag = "1" if allow else "0"
        return self.api_request("api/xqsystem/set_mac_filter", method="POST", data={"mac": mac, "wan": wan_flag})

    # --- Konfiguracja Wi-Fi ---

    def set_wifi(self, wifi_idx: int, ssid: str, password: str, encryption: str = "psk2", hidden: int = 0, txpwr: str = "max", on: int = 1, channel: int = 0, bandwidth: int = 0) -> Dict[str, Any]:
        """
        Zmienia parametry pojedynczego pasma Wi-Fi:
        - wifi_idx: 1 (2.4 GHz) lub 2 (5 GHz)
        - encryption: 'none', 'psk2' (WPA2 Personal), 'ccmp' (WPA3 Personal), 'psk2+ccmp' (WPA2/WPA3 Personal Mixed), 'mixed-psk' (WPA/WPA2 Mixed)
        - hidden: 0 (widoczne) lub 1 (ukryte)
        - txpwr: 'max' (wzmocniona), 'mid' (standardowa), 'min' (niska)
        - on: 1 (włączone) lub 0 (wyłączone)
        - channel: 0 (Auto) lub konkretny kanał
        - bandwidth: 0 (Auto) lub 20, 40, 80, 160
        """
        data = {
            "wifiIndex": str(wifi_idx),
            "ssid": ssid,
            "pwd": password,
            "encryption": encryption,
            "hidden": str(hidden),
            "txpwr": txpwr,
            "on": str(on),
            "channel": str(channel),
            "bandwidth": str(bandwidth)
        }
        return self.api_request("api/xqnetwork/set_wifi", method="POST", data=data)

    def set_channel(self, wifi_idx: int, channel: int, bandwidth: int = 0) -> Dict[str, Any]:
        """Samodzielna zmiana kanału i szerokości pasma dla danego radia (1=2.4G, 2=5G)."""
        data = {
            "wifiIndex": str(wifi_idx),
            "channel": str(channel),
            "bandwidth": str(bandwidth)
        }
        return self.api_request("api/xqnetwork/set_channel", method="POST", data=data)

    def set_all_wifi(self, bsd: int, wifi1: Dict[str, Any], wifi2: Dict[str, Any]) -> Dict[str, Any]:
        """
        Konfiguruje oba pasma Wi-Fi oraz przełącznik Smart Connect (Band Steering Dual/Tri-band BSD):
        - bsd: 1 (Smart Connect włączony - wspólne SSID), 0 (pasma rozdzielone)
        - wifi1: parametry pasma 2.4 GHz
        - wifi2: parametry pasma 5 GHz
        """
        c1 = str(wifi1.get("channel", 0))
        b1 = str(wifi1.get("bandwidth", 0))
        t1 = wifi1.get("txpwr", "max")
        c2 = str(wifi2.get("channel", 0))
        b2 = str(wifi2.get("bandwidth", 0))
        t2 = wifi2.get("txpwr", "max")

        data = {
            "bsd": str(bsd),
            # Pola konwencjonalne (kompatybilne z AX3600 i starszymi)
            "on1": str(wifi1.get("on", 1)),
            "ssid1": wifi1.get("ssid", ""),
            "pwd1": wifi1.get("pwd", wifi1.get("password", "")),
            "encryption1": wifi1.get("encryption", "psk2"),
            "channel1": c1,
            "bandwidth1": b1,
            "hidden1": str(wifi1.get("hidden", 0)),
            "txpwr1": t1,
            "on2": str(wifi2.get("on", 1)),
            "ssid2": wifi2.get("ssid", ""),
            "pwd2": wifi2.get("pwd", wifi2.get("password", "")),
            "encryption2": wifi2.get("encryption", "psk2"),
            "channel2": c2,
            "bandwidth2": b2,
            "hidden2": str(wifi2.get("hidden", 0)),
            "txpwr2": t2,
            # Pola LuCI dla nowszych modeli (BE7000 / BE6500)
            "channel": c1,
            "bandwidth": b1,
            "txpwr": t1,
            "channel50": c2,
            "bandwidth50": b2,
            "txpwr50": t2,
            "isDFS": "0"
        }
        return self.api_request("api/xqnetwork/set_all_wifi", method="POST", data=data)

    # --- Zaawansowane opcje Wi-Fi ---

    def set_wifi_ax(self, ax: int) -> Dict[str, Any]:
        """
        Przełącza tryb Wi-Fi 6 (802.11ax) / Wi-Fi 5 kompatybilności:
        - ax: 1 = Wi-Fi 6 włączone (tryb zgodności Wi-Fi 5 wyłączony)
        - ax: 0 = Tryb zgodności Wi-Fi 5 włączony (wyłącza Wi-Fi 6 / OFDMA / TWT)
        """
        return self.api_request("api/xqnetwork/set_wifi_ax", method="POST", data={"ax": str(ax), "isDFS": "0"})

    def get_twt(self) -> Dict[str, Any]:
        """Pobiera stan trybu oszczędzania energii TWT (Target Wake Time)."""
        return self.api_request("api/xqnetwork/get_twt")

    def set_twt(self, status: int) -> Dict[str, Any]:
        """Ustawia tryb oszczędzania energii TWT: 1 = włączony, 0 = wyłączony."""
        return self.api_request("api/xqnetwork/set_twt", method="POST", data={"on": str(status), "status": str(status)})

    def set_wifi_txbf(self, txbf: int) -> Dict[str, Any]:
        """Ustawia MU-MIMO / Beamforming: 1 = włączony, 0 = wyłączony."""
        return self.api_request("api/xqnetwork/set_wifi_txbf", method="POST", data={"txbf": str(txbf), "isDFS": "0"})

    def get_miotrelay_switch(self) -> Dict[str, Any]:
        """Pobiera stan usługi szybkiego parowania Xiaomi (Changkuailian / Miot Relay)."""
        return self.api_request("api/xqnetwork/get_miotrelay_switch")

    def set_miotrelay_switch(self, switch_on: int) -> Dict[str, Any]:
        """Ustawia szybkie parowanie Xiaomi (Changkuailian): 1 = włączone, 0 = wyłączone."""
        return self.api_request("api/xqnetwork/miotrelay_switch", method="POST", data={"on": str(switch_on), "switch": str(switch_on)})

    def get_wifi_silence(self) -> Dict[str, Any]:
        """Pobiera stan trybu cichego Wi-Fi (wyłączenie radia do restartu)."""
        return self.api_request("api/xqnetwork/get_wifi_silence")

    def set_wifi_silence(self, status: int) -> Dict[str, Any]:
        """Ustawia tryb cichy: 1 = wyłącza całe Wi-Fi do restartu routera, 0 = normalny stan."""
        return self.api_request("api/xqnetwork/set_wifi_silence", method="POST", data={"on": str(status), "status": str(status)})

    def get_aimesh_config(self) -> Dict[str, Any]:
        """Pobiera parametry roamingu Mesh i progi sygnału RSSI."""
        return self.api_request("api/xqnetwork/get_aimesh_config")

    def set_aimesh_config(self, manual_setting: int, threshold_2g: Optional[int] = None, threshold_5g: Optional[int] = None) -> Dict[str, Any]:
        """
        Ustawia parametry roamingu Mesh:
        - manual_setting: 0 = wyłączone (automatyczne), 1 = włączone ręczne progi
        - threshold_2g: próg roamingu RSSI dla 2.4 GHz (np. -65 dBm)
        - threshold_5g: próg roamingu RSSI dla 5 GHz (np. -70 dBm)
        """
        data = {"manual_roaming_setting": str(manual_setting)}
        if threshold_2g is not None:
            data["roam_rssi_thr_2g"] = str(threshold_2g)
            data["roam_rssi_threshold1"] = str(threshold_2g)
        if threshold_5g is not None:
            data["roam_rssi_thr_5g"] = str(threshold_5g)
            data["roam_rssi_threshold2"] = str(threshold_5g)
        return self.api_request("api/xqnetwork/set_aimesh_config", method="POST", data=data)

    def set_wifi_txpwr(self, txpwr: str = "max") -> Dict[str, Any]:
        """Ustawia poziom mocy nadawania Wi-Fi: 'max' (wzmocniona), 'mid' (standardowa), 'min' (niska)."""
        return self.api_request("api/xqnetwork/set_wifi_txpwr", method="POST", data={"txpwr": txpwr})

    def get_country_code(self) -> Dict[str, Any]:
        """Pobiera aktualny kod kraju (region regulacyjny Wi-Fi) i listę dozwolonych krajów."""
        try:
            return self.api_request("api/xqsystem/country_code")
        except Exception as e:
            return {"error": str(e)}

    def set_country_code(self, country: str) -> Dict[str, Any]:
        """Ustawia kod kraju (region regulacyjny) dla radia Wi-Fi (np. 'EU', 'PL' lub 'CN').
        Uwzglednia liste obslugiwanych kodow firmware (np. BE7000 CN akceptuje CN/HK/TW/KR/EU,
        wiec kody europejskie typu PL automatycznie mapuje na EU) oraz wykonuje weryfikacje
        odczytem (read-back) przez get_country_code().
        """
        eu_codes = {
            "PL", "DE", "FR", "CZ", "AT", "NL", "SE", "FI", "IT", "ES", "PT",
            "GR", "RO", "HU", "SK", "BE", "DK", "IE", "BG", "HR", "LT", "LV",
            "EE", "SI", "LU", "MT", "CY", "GB", "CH", "NO", "UA",
        }
        requested = (country or "").strip().upper()
        target = requested
        mapped_from = None
        supported: list = []

        try:
            pre = self.get_country_code()
            raw_list = pre.get("list") if isinstance(pre, dict) else None
            if isinstance(raw_list, list):
                supported = [
                    str(item.get("code", "")).strip().upper()
                    for item in raw_list
                    if isinstance(item, dict) and item.get("code")
                ]
            if supported and target not in supported:
                if target in eu_codes and "EU" in supported:
                    mapped_from = target
                    target = "EU"
        except Exception:
            pass

        payload = {"country": target, "countrycode": target, "code": target}
        try:
            res = self.api_request("api/xqsystem/set_country_code", method="POST", data=payload)
        except Exception as e:
            res = {"error": str(e)}

        if not (isinstance(res, dict) and res.get("code") == 0):
            try:
                qs = urllib.parse.urlencode(payload)
                res_get = self.api_request(f"api/xqsystem/set_country_code?{qs}")
                if isinstance(res_get, dict) and res_get.get("code") == 0:
                    res = res_get
            except Exception:
                pass

        if isinstance(res, dict) and res.get("code") == 0:
            res.setdefault("country", target)
            if mapped_from:
                res["mapped_from"] = mapped_from
            return res

        try:
            check = self.get_country_code()
            actual = (check.get("current") or check.get("country") or "").strip().upper()
            if actual == target and target:
                out = {
                    "code": 0,
                    "verified": True,
                    "country": target,
                    "raw_response": res,
                }
                if mapped_from:
                    out["mapped_from"] = mapped_from
                return out
        except Exception:
            pass

        if isinstance(res, dict):
            if supported:
                res["supported_codes"] = supported
            raw_msg = str(res.get("msg") or res.get("error") or "")
            err_code = res.get("code")
            if supported and target not in supported:
                sup_txt = ", ".join(supported)
                res["error_kind"] = "unsupported_code"
                res["error"] = f"Router firmware does not support country code '{target}'. Supported codes: {sup_txt}."
            elif err_code == 1606 or "操作失败" in raw_msg or "国家码" in raw_msg:
                res["error_kind"] = "firmware_locked"
                res["error"] = (
                    f"Router firmware blocks changing Wi-Fi region to '{target}' via API (code {err_code}). "
                    "On Chinese/stock builds, CountryCode is usually factory-locked in the bdata partition."
                )
            return res
        return {"error": str(res)}

    def check_firmware_update(self) -> Dict[str, Any]:
        """Sprawdza dostępność aktualizacji oprogramowania (OTA) w chmurze Xiaomi."""
        try:
            return self.api_request("api/xqsystem/check_rom_update")
        except Exception as e:
            return {"error": str(e)}

    def reboot_mesh_node(self, node_ip: str) -> Dict[str, Any]:
        """Wysyła polecenie restartu do węzła satelickiego Mesh."""
        try:
            url = f"http://{node_ip}/cgi-bin/luci/api/xqsystem/reboot"
            req = urllib.request.Request(url, headers={"User-Agent": "MiWiFi-Manager/1.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                return json.loads(resp.read().decode("utf-8", errors="ignore"))
        except Exception as e:
            return {"error": str(e)}

    def get_sys_time(self) -> Dict[str, Any]:
        """Pobiera czas systemowy i strefę czasową routera."""
        try:
            return self.api_request("api/misystem/sys_time")
        except Exception as e:
            return {"error": str(e)}

    def set_sys_time(self, time_str: Optional[str] = None, timezone_str: Optional[str] = None) -> Dict[str, Any]:
        """Ustawia czas systemowy i strefę czasową na routerze."""
        import datetime
        params = {}
        if time_str:
            params["time"] = time_str
        else:
            params["time"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if timezone_str:
            params["timezone"] = timezone_str
        else:
            params["timezone"] = "CET-1CEST"
        qs = urllib.parse.urlencode(params)
        return self.api_request(f"api/misystem/set_sys_time?{qs}")

    def set_nfc_status(self, enabled: bool = True) -> Dict[str, Any]:
        """Włącza lub wyłącza fizyczny tag NFC (jeśli wspierany sprzętowo)."""
        st = "1" if enabled else "0"
        return self.api_request("api/xqnetwork/set_nfc_status", method="POST", data={"status": st})

    def get_ps_services_summary(self) -> Dict[str, Any]:
        """Pobiera zbiorczy status wszystkich 4 usług portów fizycznych."""
        res = {}
        for s in ["multiwan", "lag", "iptv", "game"]:
            try:
                res[s] = self.get_ps_service(s)
            except Exception as e:
                res[s] = {"error": str(e)}
        return res

    # --- Kompletna migawka stanu routera (Snapshot) ---

    def fetch_full_snapshot(self) -> Dict[str, Any]:
        """Zbiera kompletny zrzut konfiguracji i parametrów ze wszystkich modułów routera."""
        snapshot = {
            "fetch_timestamp": int(time.time()),
            "fetch_date": time.strftime("%Y-%m-%d %H:%M:%S"),
            "router_ip": self.ip,
            "init_info": self.init_info or self.probe(),
            "status": {},
            "wan_info": {},
            "lan_info": {},
            "lan_dhcp": {},
            "wifi_detail": {},
            "device_list": {},
            "mac_bind": {},
            "port_forward": {},
            "storage_info": {},
            "router_name": {},
            "led_status": {},
            "reboot_task": {},
            "topo_graph": {},
            "twt": {},
            "miotrelay": {},
            "wifi_silence": {},
            "aimesh": {},
            "qos": {},
            "ddns": {},
            "vpn": {},
            "vpn_status": {},
            "ps_map": {},
            "ps_services": {}
        }

        # Bezpieczne pobieranie poszczególnych modułów
        for key, func in [
            ("status", self.get_status),
            ("wan_info", self.get_wan_info),
            ("lan_info", self.get_lan_info),
            ("lan_dhcp", self.get_lan_dhcp),
            ("wifi_detail", self.get_wifi_detail),
            ("device_list", self.get_device_list),
            ("mac_bind", self.get_mac_bind),
            ("port_forward", self.get_port_forward),
            ("storage_info", self.get_storage_info),
            ("router_name", self.get_router_name),
            ("led_status", self.get_led_status),
            ("reboot_task", self.get_reboot_task),
            ("topo_graph", self.get_topo_graph),
            ("twt", self.get_twt),
            ("miotrelay", self.get_miotrelay_switch),
            ("wifi_silence", self.get_wifi_silence),
            ("aimesh", self.get_aimesh_config),
            ("qos", self.get_qos_info),
            ("ddns", self.get_ddns),
            ("vpn", self.get_vpn_list),
            ("vpn_status", self.get_vpn_status),
            ("ps_map", self.get_ps_map),
            ("ps_services", self.get_ps_services_summary),
            ("country_code", self.get_country_code),
            ("rom_update", self.check_firmware_update),
            ("sys_time", self.get_sys_time)
        ]:
            try:
                res = func()
                if isinstance(res, dict) and res.get("code") == 0:
                    snapshot[key] = res
                else:
                    snapshot[key] = res
            except Exception as e:
                snapshot[key] = {"error": str(e)}

        return snapshot
