import json
import os
import re
import sys
import threading
import time
import traceback
from tkinter import filedialog, messagebox
import customtkinter as ctk

if getattr(sys, "frozen", False):
    APP_DIR = os.path.dirname(sys.executable)
else:
    APP_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, APP_DIR)

from miwifi_core import MiWiFiClient
from exporter_md import export_snapshot_to_markdown, format_bytes, format_speed, format_uptime
from i18n import t, load_settings, save_settings
from setup_wizard import SetupWizardDialog, TZ_POSIX_MAP, TZ_INDEX_MAP, TZ_DISPLAY_LIST
from version import APP_VERSION, APP_NAME

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


def safe_int(val, default=0):
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return default


def safe_float(val, default=0.0):
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def clean_model_name(raw_model) -> str:
    return str(raw_model or "Xiaomi").replace("Xiaomi路由器", "Xiaomi Router ").strip()


def format_uptime_compact(seconds: int) -> str:
    s = safe_int(seconds, 0)
    if s <= 0:
        return "<1m"
    d = s // 86400
    h = (s % 86400) // 3600
    m = (s % 3600) // 60
    if d > 0:
        return f"{d}d {h}h"
    if h > 0:
        return f"{h}h {m}m"
    if m > 0:
        return f"{m}m"
    return f"{s}s"


def parse_mem_total_bytes(val) -> float:
    """Parsuje ciągi rozmiaru pamięci (np. '1024MB', '512MB', surowe bajty) do bajtów."""
    if isinstance(val, (int, float)):
        v = float(val)
        return v * 1024 * 1024 if 0 < v < 65536 else v
    s = str(val or "").strip()
    m = re.match(r"^([\d\.]+)\s*([a-zA-Z]*)$", s)
    if not m:
        return 0.0
    num = float(m.group(1))
    unit = m.group(2).upper()
    if "TB" in unit:
        return num * (1024 ** 4)
    if "GB" in unit:
        return num * (1024 ** 3)
    if "MB" in unit or unit == "M":
        return num * (1024 ** 2)
    if "KB" in unit or unit == "K":
        return num * 1024
    if 0 < num < 65536:
        return num * (1024 ** 2)
    return num


def parse_ip_key(ip_str: str):
    """Zwraca krotkę liczb do numerycznego sortowania IPv4."""
    try:
        parts = str(ip_str).strip().split(".")
        if len(parts) == 4:
            return tuple(int(p) for p in parts)
    except Exception:
        pass
    return (999, 999, 999, 999)


def get_wifi_tx_options(lang: str = "pl") -> list:
    return [t("wifi_tx_max", lang), t("wifi_tx_mid", lang), t("wifi_tx_min", lang)]


def tx_to_code(val: str) -> str:
    s = str(val).lower()
    if "maks" in s or "max" in s or "wzmoc" in s or "boost" in s:
        return "max"
    elif "śred" in s or "sred" in s or "mid" in s or "med" in s:
        return "mid"
    elif "nisk" in s or "min" in s or "low" in s or "oszcz" in s:
        return "min"
    return "max"


def code_to_tx(code: str, lang: str = "pl") -> str:
    c = str(code).lower()
    if c == "min":
        return t("wifi_tx_min", lang)
    if c == "mid":
        return t("wifi_tx_mid", lang)
    return t("wifi_tx_max", lang)


def get_wifi_enc_options(lang: str = "pl") -> list:
    return [
        t("wifi_enc_sae_mixed", lang),
        t("wifi_enc_sae", lang),
        t("wifi_enc_psk2", lang),
        t("wifi_enc_mixed_psk", lang),
        t("wifi_enc_none", lang)
    ]


def enc_to_code(val: str) -> str:
    s = str(val).lower()
    if "psk2+ccmp" in s or "wpa2/wpa3" in s or "sae-mixed" in s or "personal (sae-mi" in s or ("mixed" in s and "wpa3" in s):
        return "psk2+ccmp"
    if "mixed-psk" in s or "psk-mixed" in s or "wpa/wpa2" in s:
        return "mixed-psk"
    if "psk2" in s or "wpa2" in s:
        return "psk2"
    if "ccmp" in s or "wpa3" in s or "sae" in s:
        return "ccmp"
    if "none" in s or "brak" in s or "otwart" in s or "open" in s:
        return "none"
    return "psk2+ccmp"


def code_to_enc(code: str, lang: str = "pl") -> str:
    c = str(code).lower()
    if c in ("psk2+ccmp", "sae-mixed"):
        return t("wifi_enc_sae_mixed", lang)
    if c in ("ccmp", "sae"):
        return t("wifi_enc_sae", lang)
    if c == "psk2":
        return t("wifi_enc_psk2", lang)
    if c in ("mixed-psk", "psk-mixed"):
        return t("wifi_enc_mixed_psk", lang)
    if c == "none":
        return t("wifi_enc_none", lang)
    return t("wifi_enc_sae_mixed", lang)


WIFI_ENC_OPTIONS = [
    "WPA2/WPA3 Personal (psk2+ccmp)",
    "WPA3 Personal (ccmp)",
    "WPA2 Personal (psk2)",
    "WPA/WPA2 Mixed (mixed-psk)",
    "Brak / Otwarta (none)"
]

WIFI_ENC_MAP_CODE = {
    "WPA2/WPA3 Personal (psk2+ccmp)": "psk2+ccmp",
    "WPA3 Personal (ccmp)": "ccmp",
    "WPA2 Personal (psk2)": "psk2",
    "WPA/WPA2 Mixed (mixed-psk)": "mixed-psk",
    "Brak / Otwarta (none)": "none"
}

WIFI_CODE_TO_ENC = {
    "psk2+ccmp": "WPA2/WPA3 Personal (psk2+ccmp)",
    "sae-mixed": "WPA2/WPA3 Personal (psk2+ccmp)",
    "ccmp": "WPA3 Personal (ccmp)",
    "sae": "WPA3 Personal (ccmp)",
    "psk2": "WPA2 Personal (psk2)",
    "mixed-psk": "WPA/WPA2 Mixed (mixed-psk)",
    "psk-mixed": "WPA/WPA2 Mixed (mixed-psk)",
    "none": "Brak / Otwarta (none)"
}

WIFI_TX_OPTIONS = [
    "Maksymalna (Wzmocniona)",
    "Średnia (Standardowa)",
    "Niska (Oszczędna)"
]

WIFI_TX_MAP_CODE = {
    "Maksymalna (Wzmocniona)": "max",
    "Średnia (Standardowa)": "mid",
    "Niska (Oszczędna)": "min"
}

WIFI_CODE_TO_TX = {
    "max": "Maksymalna (Wzmocniona)",
    "mid": "Średnia (Standardowa)",
    "min": "Niska (Oszczędna)"
}

WIFI_2G_CHANNELS = ["Auto", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13"]
WIFI_2G_BANDWIDTHS = ["40 / 20 MHz", "20 MHz"]

WIFI_5G_CHANNELS = ["Auto", "36", "40", "44", "48", "52", "56", "60", "64", "149", "153", "157", "161", "165"]
WIFI_5G_BANDWIDTHS = ["160 / 80 / 40 / 20 MHz (Wi-Fi 6/7)", "80 / 40 / 20 MHz", "40 MHz", "20 MHz"]


def channel_to_code(val_str: str) -> int:
    s = str(val_str).split()[0].strip()
    if s.lower() == "auto" or s == "0":
        return 0
    try:
        return int(s)
    except ValueError:
        return 0


def code_to_channel(code_val) -> str:
    c = safe_int(code_val, 0)
    if c == 0:
        return "Auto"
    return str(c)


def bandwidth_to_code(val_str: str) -> int:
    s = str(val_str).lower().strip()
    if "160 / 80" in s or "40 / 20" in s or "auto" in s or s == "0":
        return 0
    if "160" in s:
        return 160
    if "80" in s:
        return 80
    if "40" in s:
        return 40
    if "20" in s:
        return 20
    try:
        return int(s.split()[0])
    except (ValueError, IndexError):
        return 0


def code_to_bandwidth(code_val, band: str = "2g") -> str:
    c = safe_int(code_val, 0)
    if c == 0:
        return "160 / 80 / 40 / 20 MHz (Wi-Fi 6/7)" if str(band).lower() in ("5", "5g", "2") else "40 / 20 MHz"
    if c == 160:
        return "160 / 80 / 40 / 20 MHz (Wi-Fi 6/7)"
    if c == 80:
        return "80 / 40 / 20 MHz"
    if c == 40:
        return "40 MHz"
    if c == 20:
        return "20 MHz"
    return f"{c} MHz"


class MiWiFiManagerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.settings = load_settings()
        self.current_lang = self.settings.get("lang", "pl")

        self.title(f"{APP_NAME} v{APP_VERSION} (BE7000 / BE6500 / AX3600)")
        self.geometry("1240x840")
        self.minsize(1080, 720)

        # Ustawienie ikony okna jeśli istnieje
        icon_path = os.path.join(APP_DIR, "app_icon.ico")
        if not os.path.exists(icon_path) and hasattr(sys, "_MEIPASS"):
            icon_path = os.path.join(sys._MEIPASS, "app_icon.ico")
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception:
                pass

        self.client = MiWiFiClient()
        self.snapshot = {}
        self.auto_refresh_running = False
        self._staged_qos_mode = None
        self._staged_qos_band = None

        self._build_ui()
        self._auto_detect()

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # 1. Górny pasek połączenia
        top_frame = ctk.CTkFrame(self, corner_radius=10)
        top_frame.grid(row=0, column=0, padx=15, pady=(15, 10), sticky="ew")
        top_frame.grid_columnconfigure(4, weight=2)

        # Lewa strona: status i IP
        self.lbl_gateway_ip = ctk.CTkLabel(top_frame, text=t("gateway_ip", self.current_lang), font=ctk.CTkFont(weight="bold"))
        self.lbl_gateway_ip.grid(row=0, column=0, padx=(15, 5), pady=(10, 4))
        self.ip_entry = ctk.CTkEntry(top_frame, width=130)
        self.ip_entry.insert(0, self.client.ip)
        self.ip_entry.grid(row=0, column=1, padx=5, pady=(10, 4), sticky="w")

        # Środek: Stok lub Hasło
        self.auth_mode = ctk.CTkSegmentedButton(top_frame, values=["Link / Stok", "Hasło"], command=self._on_auth_mode_change)
        self.auth_mode.set("Hasło")
        self.auth_mode.grid(row=0, column=2, padx=(10, 4), pady=(10, 4))

        self.btn_auth_help = ctk.CTkButton(top_frame, text="?", width=28, height=28, fg_color="#334155", hover_color="#475569", font=ctk.CTkFont(weight="bold"), command=self._show_stok_help)
        self.btn_auth_help.grid(row=0, column=3, padx=(0, 6), pady=(10, 4))

        self.auth_entry = ctk.CTkEntry(top_frame, placeholder_text="Hasło administratora routera...", show="•", width=340)
        self.auth_entry.grid(row=0, column=4, padx=5, pady=(10, 4), sticky="ew")

        # Prawa strona: Przycisk Połącz i lampka statusu
        self.btn_connect = ctk.CTkButton(top_frame, text="Połącz", width=100, command=self._toggle_connect)
        self.btn_connect.grid(row=0, column=5, padx=10, pady=(10, 4))

        self.status_indicator = ctk.CTkLabel(top_frame, text="● Rozłączony", text_color="#ff5555", font=ctk.CTkFont(weight="bold"))
        self.status_indicator.grid(row=0, column=6, padx=(5, 8), pady=(10, 4))

        self.lang_selector = ctk.CTkSegmentedButton(top_frame, values=["PL", "EN"], width=65, command=self._on_language_change)
        self.lang_selector.set(self.current_lang.upper())
        self.lang_selector.grid(row=0, column=7, padx=(4, 6), pady=(10, 4))

        self.lbl_version_badge = ctk.CTkLabel(top_frame, text=f"v{APP_VERSION}", font=ctk.CTkFont(size=11, weight="bold"), text_color="#64748b")
        self.lbl_version_badge.grid(row=0, column=8, padx=(0, 15), pady=(10, 4))

        # Pasek podpowiedzi (wyjaśniający co to jest link/stok)
        self.lbl_auth_hint = ctk.CTkLabel(
            top_frame,
            text="💡 Logowanie hasłem: program automatycznie przeprowadza szyfrowaną autoryzację SHA-256 z routerem.",
            text_color="#94a3b8",
            font=ctk.CTkFont(size=11)
        )
        self.lbl_auth_hint.grid(row=1, column=0, columnspan=9, padx=15, pady=(0, 4), sticky="w")

        # Szeroki zielony przycisk kreatora pierwszej konfiguracji
        self.btn_wizard = ctk.CTkButton(
            top_frame,
            text=t("btn_wizard", self.current_lang),
            fg_color="#16a34a",
            hover_color="#15803d",
            font=ctk.CTkFont(size=13, weight="bold"),
            height=34,
            command=self._open_setup_wizard
        )
        self.btn_wizard.grid(row=2, column=0, columnspan=9, padx=15, pady=(2, 10), sticky="ew")

        # 2. Główne Menu (4 przestronne kategorie bez obcinania nazw)
        self.tabs = ctk.CTkTabview(self, corner_radius=10)
        self.tabs._segmented_button.configure(font=ctk.CTkFont(size=13, weight="bold"))
        self.tabs.grid(row=1, column=0, padx=15, pady=(0, 15), sticky="nsew")

        self.main_tab_dashboard = self.tabs.add("Pulpit i Urządzenia")
        self.main_tab_network = self.tabs.add("Konfiguracja Sieci")
        self.main_tab_ports = self.tabs.add("Porty i Usługi")
        self.main_tab_system = self.tabs.add("System i Narzędzia")

        # --- Kategoria 1: Pulpit i Urządzenia ---
        self.main_tab_dashboard.grid_columnconfigure(0, weight=1)
        self.main_tab_dashboard.grid_rowconfigure(1, weight=1)
        sub_bar_dash = ctk.CTkFrame(self.main_tab_dashboard, fg_color="transparent")
        sub_bar_dash.grid(row=0, column=0, padx=10, pady=(5, 8), sticky="ew")
        self.lbl_sub_dash = ctk.CTkLabel(sub_bar_dash, text=t("sub_view_label", self.current_lang), font=ctk.CTkFont(weight="bold"))
        self.lbl_sub_dash.pack(side="left", padx=(5, 10))
        self.seg_sub_dashboard = ctk.CTkSegmentedButton(
            sub_bar_dash,
            values=[t("sub_dash_live", self.current_lang), t("sub_dash_devices", self.current_lang), t("sub_dash_mesh", self.current_lang)],
            command=self._on_sub_dashboard_change
        )
        self.seg_sub_dashboard.set(t("sub_dash_live", self.current_lang))
        self.seg_sub_dashboard.pack(side="left", fill="x", expand=True)

        self.container_dashboard = ctk.CTkFrame(self.main_tab_dashboard, corner_radius=8, fg_color="transparent")
        self.container_dashboard.grid(row=1, column=0, padx=0, pady=0, sticky="nsew")
        self.container_dashboard.grid_columnconfigure(0, weight=1)
        self.container_dashboard.grid_rowconfigure(0, weight=1)

        self.tab_dashboard = ctk.CTkFrame(self.container_dashboard, fg_color="transparent")
        self.tab_devices = ctk.CTkFrame(self.container_dashboard, fg_color="transparent")
        self.tab_mesh = ctk.CTkFrame(self.container_dashboard, fg_color="transparent")
        self.tab_dashboard.grid(row=0, column=0, sticky="nsew")

        # --- Kategoria 2: Konfiguracja Sieci ---
        self.main_tab_network.grid_columnconfigure(0, weight=1)
        self.main_tab_network.grid_rowconfigure(1, weight=1)
        sub_bar_net = ctk.CTkFrame(self.main_tab_network, fg_color="transparent")
        sub_bar_net.grid(row=0, column=0, padx=10, pady=(5, 8), sticky="ew")
        self.lbl_sub_net = ctk.CTkLabel(sub_bar_net, text=t("sub_net_label", self.current_lang), font=ctk.CTkFont(weight="bold"))
        self.lbl_sub_net.pack(side="left", padx=(5, 10))
        self.seg_sub_network = ctk.CTkSegmentedButton(
            sub_bar_net,
            values=[t("sub_net_wan", self.current_lang), t("sub_net_lan", self.current_lang), t("sub_net_wifi", self.current_lang)],
            command=self._on_sub_network_change
        )
        self.seg_sub_network.set(t("sub_net_wan", self.current_lang))
        self.seg_sub_network.pack(side="left", fill="x", expand=True)

        self.container_network = ctk.CTkFrame(self.main_tab_network, corner_radius=8, fg_color="transparent")
        self.container_network.grid(row=1, column=0, padx=0, pady=0, sticky="nsew")
        self.container_network.grid_columnconfigure(0, weight=1)
        self.container_network.grid_rowconfigure(0, weight=1)

        self.tab_wan = ctk.CTkFrame(self.container_network, fg_color="transparent")
        self.tab_lan = ctk.CTkFrame(self.container_network, fg_color="transparent")
        self.tab_wifi = ctk.CTkFrame(self.container_network, fg_color="transparent")
        self.tab_wan.grid(row=0, column=0, sticky="nsew")

        # --- Kategoria 3: Porty i Usługi ---
        self.main_tab_ports.grid_columnconfigure(0, weight=1)
        self.main_tab_ports.grid_rowconfigure(1, weight=1)
        sub_bar_ports = ctk.CTkFrame(self.main_tab_ports, fg_color="transparent")
        sub_bar_ports.grid(row=0, column=0, padx=10, pady=(5, 8), sticky="ew")
        self.lbl_sub_ports = ctk.CTkLabel(sub_bar_ports, text=t("sub_ports_label", self.current_lang), font=ctk.CTkFont(weight="bold"))
        self.lbl_sub_ports.pack(side="left", padx=(5, 10))
        self.seg_sub_ports = ctk.CTkSegmentedButton(
            sub_bar_ports,
            values=[t("sub_ports_nat", self.current_lang), t("sub_ports_hw", self.current_lang), t("sub_ports_qos", self.current_lang)],
            command=self._on_sub_ports_change
        )
        self.seg_sub_ports.set(t("sub_ports_nat", self.current_lang))
        self.seg_sub_ports.pack(side="left", fill="x", expand=True)

        self.container_ports_main = ctk.CTkFrame(self.main_tab_ports, corner_radius=8, fg_color="transparent")
        self.container_ports_main.grid(row=1, column=0, padx=0, pady=0, sticky="nsew")
        self.container_ports_main.grid_columnconfigure(0, weight=1)
        self.container_ports_main.grid_rowconfigure(0, weight=1)

        self.tab_nat = ctk.CTkFrame(self.container_ports_main, fg_color="transparent")
        self.tab_ports = ctk.CTkFrame(self.container_ports_main, fg_color="transparent")
        self.tab_qos_vpn = ctk.CTkFrame(self.container_ports_main, fg_color="transparent")
        self.tab_nat.grid(row=0, column=0, sticky="nsew")

        # --- Kategoria 4: System i Narzędzia ---
        self.main_tab_system.grid_columnconfigure(0, weight=1)
        self.main_tab_system.grid_rowconfigure(1, weight=1)
        sub_bar_sys = ctk.CTkFrame(self.main_tab_system, fg_color="transparent")
        sub_bar_sys.grid(row=0, column=0, padx=10, pady=(5, 8), sticky="ew")
        self.lbl_sub_sys = ctk.CTkLabel(sub_bar_sys, text=t("sub_sys_label", self.current_lang), font=ctk.CTkFont(weight="bold"))
        self.lbl_sub_sys.pack(side="left", padx=(5, 10))
        self.seg_sub_system = ctk.CTkSegmentedButton(
            sub_bar_sys,
            values=[t("sub_sys_tools", self.current_lang), t("sub_sys_wizard", self.current_lang)],
            command=self._on_sub_system_change
        )
        self.seg_sub_system.set(t("sub_sys_tools", self.current_lang))
        self.seg_sub_system.pack(side="left", fill="x", expand=True)

        self.container_system = ctk.CTkFrame(self.main_tab_system, corner_radius=8, fg_color="transparent")
        self.container_system.grid(row=1, column=0, padx=0, pady=0, sticky="nsew")
        self.container_system.grid_columnconfigure(0, weight=1)
        self.container_system.grid_rowconfigure(0, weight=1)

        self.tab_tools = ctk.CTkFrame(self.container_system, fg_color="transparent")
        self.tab_wizard = ctk.CTkFrame(self.container_system, fg_color="transparent")
        self.tab_tools.grid(row=0, column=0, sticky="nsew")

        self.raw_binds = []
        self._build_dashboard_tab()
        self._build_devices_tab()
        self._build_mesh_tab()
        self._build_wan_tab()
        self._build_lan_tab()
        self._build_wifi_tab()
        self._build_nat_tab()
        self._build_qos_vpn_tab()
        self._build_ports_tab()
        self._build_tools_tab()
        self._build_wizard_tab()
        self._apply_language()

    def _on_sub_dashboard_change(self, choice):
        self.tab_dashboard.grid_forget()
        self.tab_devices.grid_forget()
        self.tab_mesh.grid_forget()
        if "Kokpit" in choice or "Live" in choice:
            self.tab_dashboard.grid(row=0, column=0, sticky="nsew")
        elif "Mesh" in choice:
            self.tab_mesh.grid(row=0, column=0, sticky="nsew")
            self._render_mesh_tab()
        else:
            self.tab_devices.grid(row=0, column=0, sticky="nsew")

    def _on_sub_network_change(self, choice):
        self.tab_wan.grid_forget()
        self.tab_lan.grid_forget()
        self.tab_wifi.grid_forget()
        if "WAN" in choice:
            self.tab_wan.grid(row=0, column=0, sticky="nsew")
        elif "LAN" in choice:
            self.tab_lan.grid(row=0, column=0, sticky="nsew")
        else:
            self.tab_wifi.grid(row=0, column=0, sticky="nsew")

    def _on_sub_ports_change(self, choice):
        self.tab_nat.grid_forget()
        self.tab_ports.grid_forget()
        self.tab_qos_vpn.grid_forget()
        c_low = choice.lower()
        if "fizycz" in c_low or "phys" in c_low or "2.5" in c_low:
            self.tab_ports.grid(row=0, column=0, sticky="nsew")
        elif "qos" in c_low or "vpn" in c_low or "ddns" in c_low:
            self.tab_qos_vpn.grid(row=0, column=0, sticky="nsew")
        else:
            self.tab_nat.grid(row=0, column=0, sticky="nsew")

    def _on_sub_system_change(self, choice):
        self.tab_tools.grid_forget()
        self.tab_wizard.grid_forget()
        c_low = choice.lower()
        if "kreator" in c_low or "wizard" in c_low:
            self.tab_wizard.grid(row=0, column=0, sticky="nsew")
        else:
            self.tab_tools.grid(row=0, column=0, sticky="nsew")

    def _on_auth_mode_change(self, mode):
        lg = self.current_lang
        if mode in ("Hasło", "Password"):
            self.auth_entry.configure(placeholder_text=t("pwd_placeholder", lg), show="•")
            self.lbl_auth_hint.configure(text=t("hint_pwd", lg))
        else:
            self.auth_entry.configure(placeholder_text=t("stok_placeholder", lg), show="")
            self.lbl_auth_hint.configure(text=t("hint_stok", lg))

    def _show_stok_help(self):
        lg = self.current_lang
        if lg == "pl":
            msg = (
                "CO TO JEST 'LINK / STOK' I JAK Z NIEGO KORZYSTAĆ?\n\n"
                "Każdy router Xiaomi po zalogowaniu w przeglądarce generuje unikalny token bezpieczeństwa "
                "sesji o nazwie 'stok' (Security Token), który widnieje w pasku adresu URL, np.:\n"
                "http://192.168.31.1/cgi-bin/luci/;stok=131774945a3c3c14.../web/home\n\n"
                "JAK SIĘ POŁĄCZYĆ PRZEZ LINK / STOK:\n"
                "1. Otwórz router w przeglądarce (np. Chrome, Edge, Firefox) i zaloguj się.\n"
                "2. Zaznacz cały adres w pasku przeglądarki i skopiuj go (Ctrl + C).\n"
                "3. Wklej skopiowany link w pole tekstowe w tym programie (Ctrl + V).\n"
                "4. Kliknij 'Połącz'.\n\n"
                "ZALETY:\n"
                "• Nie musisz wpisywać ani pamiętać hasła administratora.\n"
                "• Działa natychmiastowo, nawet jeśli router ma nietypowe zabezpieczenia.\n"
                "• Program sam automatycznie wyciągnie token 'stok' ze skopiowanego adresu."
            )
            title = "Czym jest Link / Stok?"
        else:
            msg = (
                "WHAT IS 'LINK / STOK' AND HOW TO USE IT?\n\n"
                "Every Xiaomi router generates a unique session security token named 'stok' "
                "(Security Token) upon browser login, visible in the URL bar, e.g.:\n"
                "http://192.168.31.1/cgi-bin/luci/;stok=131774945a3c3c14.../web/home\n\n"
                "HOW TO CONNECT VIA LINK / STOK:\n"
                "1. Open your router in a browser (e.g. Chrome, Edge, Firefox) and log in.\n"
                "2. Select the whole address in the browser bar and copy it (Ctrl + C).\n"
                "3. Paste the copied link into the text field in this app (Ctrl + V).\n"
                "4. Click 'Connect'.\n\n"
                "ADVANTAGES:\n"
                "• No need to type or remember the admin password.\n"
                "• Connects instantly even if router has custom login protections.\n"
                "• The app automatically extracts the 'stok' token from the pasted URL."
            )
            title = "What is Link / Stok?"
        messagebox.showinfo(title, msg)

    # --- KOKPIT ---
    def _build_dashboard_tab(self):
        tab = self.tab_dashboard
        tab.grid_columnconfigure((0, 1, 2), weight=1)

        dash_bar = ctk.CTkFrame(tab, fg_color="transparent")
        dash_bar.grid(row=0, column=0, columnspan=3, padx=10, pady=(5, 10), sticky="ew")

        self.lbl_router_title = ctk.CTkLabel(dash_bar, text=t("waiting_connection", self.current_lang), font=ctk.CTkFont(size=18, weight="bold"))
        self.lbl_router_title.pack(side="left", padx=5)

        self.btn_export_md = ctk.CTkButton(dash_bar, text=t("btn_export_md", self.current_lang), width=140, fg_color="#2b7a4b", hover_color="#205c38", command=self._export_to_md)
        self.btn_export_md.pack(side="right", padx=5)

        self.btn_refresh = ctk.CTkButton(dash_bar, text=t("btn_refresh", self.current_lang), width=90, command=self._fetch_data_thread)
        self.btn_refresh.pack(side="right", padx=5)

        self.switch_autorefresh = ctk.CTkSwitch(dash_bar, text=t("autorefresh", self.current_lang), command=self._toggle_autorefresh)
        self.switch_autorefresh.pack(side="right", padx=15)

        # Karta 1: Sprzęt i System
        card1 = ctk.CTkFrame(tab)
        card1.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        self.card1_title = ctk.CTkLabel(card1, text=t("card_hw_sys", self.current_lang), font=ctk.CTkFont(size=15, weight="bold"))
        self.card1_title.pack(anchor="w", padx=15, pady=(15, 10))
        self.lbl_model = ctk.CTkLabel(card1, text=f"{t('lbl_model', self.current_lang)} -", anchor="w")
        self.lbl_model.pack(fill="x", padx=15, pady=2)
        self.lbl_rom = ctk.CTkLabel(card1, text=f"{t('lbl_rom', self.current_lang)} -", anchor="w")
        self.lbl_rom.pack(fill="x", padx=15, pady=2)
        self.lbl_uptime = ctk.CTkLabel(card1, text=f"{t('lbl_uptime', self.current_lang)} -", anchor="w")
        self.lbl_uptime.pack(fill="x", padx=15, pady=2)
        self.lbl_router_id = ctk.CTkLabel(card1, text=f"{t('lbl_router_id', self.current_lang)} -", anchor="w")
        self.lbl_router_id.pack(fill="x", padx=15, pady=2)

        # Karta 2: Obciążenie CPU i RAM
        card2 = ctk.CTkFrame(tab)
        card2.grid(row=1, column=1, padx=10, pady=10, sticky="nsew")
        self.card2_title = ctk.CTkLabel(card2, text=t("card_cpu_ram", self.current_lang), font=ctk.CTkFont(size=15, weight="bold"))
        self.card2_title.pack(anchor="w", padx=15, pady=(15, 10))

        self.lbl_cpu = ctk.CTkLabel(card2, text=f"{t('lbl_cpu', self.current_lang)} --", anchor="w")
        self.lbl_cpu.pack(fill="x", padx=15, pady=(5, 2))
        self.pb_cpu = ctk.CTkProgressBar(card2)
        self.pb_cpu.set(0)
        self.pb_cpu.pack(fill="x", padx=15, pady=(0, 10))

        self.lbl_ram = ctk.CTkLabel(card2, text=f"{t('lbl_ram', self.current_lang)} 0 MB / 0 MB (0%)", anchor="w")
        self.lbl_ram.pack(fill="x", padx=15, pady=(5, 2))
        self.pb_ram = ctk.CTkProgressBar(card2)
        self.pb_ram.set(0)
        self.pb_ram.pack(fill="x", padx=15, pady=(0, 15))

        # Karta 3: Łącze Internetowe (WAN)
        card3 = ctk.CTkFrame(tab)
        card3.grid(row=1, column=2, padx=10, pady=10, sticky="nsew")
        self.card3_title = ctk.CTkLabel(card3, text=t("card_wan_speed", self.current_lang), font=ctk.CTkFont(size=15, weight="bold"))
        self.card3_title.pack(anchor="w", padx=15, pady=(15, 10))

        self.lbl_down = ctk.CTkLabel(card3, text=f"{t('lbl_down', self.current_lang)} 0 KB/s", font=ctk.CTkFont(size=14, weight="bold"), text_color="#33a02c", anchor="w")
        self.lbl_down.pack(fill="x", padx=15, pady=4)
        self.lbl_up = ctk.CTkLabel(card3, text=f"{t('lbl_up', self.current_lang)} 0 KB/s", font=ctk.CTkFont(size=14, weight="bold"), text_color="#1f78b4", anchor="w")
        self.lbl_up.pack(fill="x", padx=15, pady=4)
        self.lbl_wan_ip = ctk.CTkLabel(card3, text=f"{t('lbl_wan_ip', self.current_lang)} -", anchor="w")
        self.lbl_wan_ip.pack(fill="x", padx=15, pady=2)
        self.lbl_wan_dns = ctk.CTkLabel(card3, text=f"{t('lbl_wan_dns', self.current_lang)} -", anchor="w")
        self.lbl_wan_dns.pack(fill="x", padx=15, pady=2)

        # Dolny panel podsumowania
        summary_frame = ctk.CTkFrame(tab)
        summary_frame.grid(row=2, column=0, columnspan=3, padx=10, pady=10, sticky="nsew")
        tab.grid_rowconfigure(2, weight=1)

        self.card_sum_title = ctk.CTkLabel(summary_frame, text=t("card_summary", self.current_lang), font=ctk.CTkFont(size=15, weight="bold"))
        self.card_sum_title.pack(anchor="w", padx=15, pady=(10, 5))
        self.lbl_summary_devs = ctk.CTkLabel(summary_frame, text=f"{t('active_devs', self.current_lang)} 0  |  {t('led_status', self.current_lang)} -", anchor="w")
        self.lbl_summary_devs.pack(fill="x", padx=15, pady=5)

    # --- URZĄDZENIA ---
    def _build_devices_tab(self):
        tab = self.tab_devices
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(1, weight=1)

        dev_top = ctk.CTkFrame(tab, fg_color="transparent")
        dev_top.grid(row=0, column=0, padx=10, pady=5, sticky="ew")

        self.lbl_dev_heading = ctk.CTkLabel(dev_top, text=t("dev_heading", self.current_lang), font=ctk.CTkFont(size=15, weight="bold"))
        self.lbl_dev_heading.pack(side="left", padx=(5, 10))

        # Wyszukiwarka
        self.entry_filter_devices = ctk.CTkEntry(dev_top, placeholder_text=t("dev_search_placeholder", self.current_lang), width=180)
        self.entry_filter_devices.pack(side="left", padx=5)
        self.entry_filter_devices.bind("<KeyRelease>", lambda e: self._render_devices_list())

        # Sortowanie
        dev_sort_vals = [
            "Sortuj: Domyślnie",
            "Adres IP (rosnąco)",
            "Adres IP (malejąco)",
            "Nazwa (A-Z)",
            "Nazwa (Z-A)",
            "Aktywne najpierw",
            "Czas połączenia"
        ] if self.current_lang == "pl" else [
            "Sort: Default",
            "IP Address (Ascending)",
            "IP Address (Descending)",
            "Name (A-Z)",
            "Name (Z-A)",
            "Active First",
            "Connection Time"
        ]
        self.combo_dev_sort = ctk.CTkOptionMenu(
            dev_top,
            values=dev_sort_vals,
            width=180,
            command=lambda v: self._render_devices_list()
        )
        self.combo_dev_sort.set(dev_sort_vals[0])
        self.combo_dev_sort.pack(side="left", padx=5)

        # Przełącznik urządzeń offline
        self.switch_show_offline = ctk.CTkSwitch(dev_top, text=t("dev_show_offline", self.current_lang), command=self._render_devices_list)
        self.switch_show_offline.select()
        self.switch_show_offline.pack(side="left", padx=10)

        self.lbl_dev_count = ctk.CTkLabel(dev_top, text=t("dev_active_count", self.current_lang).format(count=0), font=ctk.CTkFont(weight="bold"))
        self.lbl_dev_count.pack(side="right", padx=10)

        self.scroll_devices = ctk.CTkScrollableFrame(tab, corner_radius=10)
        self.scroll_devices.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")
        self.scroll_devices.grid_columnconfigure(0, weight=1)

    def _render_devices_list(self):
        for widget in self.scroll_devices.winfo_children():
            widget.destroy()

        lg = self.current_lang
        raw_devs = getattr(self, "raw_devices", [])
        raw_binds = getattr(self, "raw_binds", [])

        # Szybka mapa rezerwacji po MAC
        binds_by_mac = {}
        for b in raw_binds:
            b_mac = (b.get("mac") or "").upper()
            if b_mac:
                binds_by_mac[b_mac] = b

        # Budowa mapy AP / Satelitów z topologii
        topo = self.snapshot.get("topo_graph", {})
        graph = topo.get("graph", {})
        ap_map = {}
        main_name = graph.get("name") or ("Main Router" if lg == "en" else "Router Główny")
        main_hw = "BE7000" if graph.get("hardware") == "RC06" else ("BE6500" if graph.get("hardware") == "RN02" else (graph.get("hardware") or ""))
        ap_map[graph.get("ip")] = f"{main_name} ({main_hw})" if main_hw else main_name
        if graph.get("mac"):
            ap_map[str(graph.get("mac")).upper().strip()] = ap_map[graph.get("ip")]

        for leaf in graph.get("leafs", []):
            l_ip = leaf.get("ip")
            l_name = leaf.get("name") or leaf.get("hardware") or ("Satellite" if lg == "en" else "Satelita")
            l_hw = "BE6500" if leaf.get("hardware") == "RN02" else ("BE7000" if leaf.get("hardware") == "RC06" else (leaf.get("hardware") or ""))
            label_leaf = f"{l_hw}" if l_hw and (not l_name or l_name.startswith("rn02_") or l_name == leaf.get("hardware")) else (f"{l_name} ({l_hw})" if l_hw else l_name)
            if l_ip:
                ap_map[l_ip] = label_leaf
            for mk in ("mac", "id"):
                mv = str(leaf.get(mk) or "").upper().strip()
                if mv and ":" in mv:
                    ap_map[mv] = label_leaf

        for d in raw_devs:
            d_ip = d.get("ip")
            if isinstance(d_ip, list) and d_ip:
                d_ip = d_ip[0].get("ip")
            d_mac = (d.get("mac") or "").upper().strip()
            if d_ip in ap_map and d_mac:
                ap_map[d_mac] = ap_map[d_ip]

        active_macs = set()
        items = []

        # 1. Urządzenia aktywne online
        for d in raw_devs:
            m = (d.get("mac") or "").upper()
            if m:
                active_macs.add(m)

            d_name = d.get("name") or d.get("oname") or ""
            if (not d_name or d_name.lower().startswith("device_")) and m in binds_by_mac:
                d_name = binds_by_mac[m].get("name") or d_name
            if not d_name:
                d_name = "Unknown" if lg == "en" else "Nieznane"

            ip_list = d.get("ip", [])
            if isinstance(ip_list, list) and ip_list:
                d_ip = ip_list[0].get("ip", "-")
            else:
                d_ip = str(d.get("ip", "-"))

            is_ap = safe_int(d.get("isap", 0)) > 0
            is_type = safe_int(d.get("type", 0))

            if is_ap:
                conn_type = "Mesh Node" if lg == "en" else "Węzeł Mesh"
                badge_color = "#06b6d4"
            elif is_type == 0:
                conn_type = "Wired (LAN)" if lg == "en" else "Kabel (LAN)"
                badge_color = "#3b82f6"
            elif is_type == 1:
                conn_type = "Wi-Fi 2.4G"
                badge_color = "#10b981"
            elif is_type == 2:
                conn_type = "Wi-Fi 5G"
                badge_color = "#8b5cf6"
            elif is_type == 3:
                conn_type = "Wi-Fi 5G Game"
                badge_color = "#f59e0b"
            elif is_type == 4:
                conn_type = "Wi-Fi 5G-2"
                badge_color = "#a855f7"
            elif is_type == 5:
                conn_type = "Wi-Fi 6G"
                badge_color = "#ec4899"
            elif is_type == 6:
                conn_type = "Guest Wi-Fi" if lg == "en" else "Wi-Fi Gość"
                badge_color = "#64748b"
            elif is_type == 7:
                conn_type = "Wi-Fi 7 MLO"
                badge_color = "#e11d48"
            elif is_type == 8:
                conn_type = "Wi-Fi IoT"
                badge_color = "#14b8a6"
            else:
                conn_type = "Other" if lg == "en" else "Inne"
                badge_color = "#94a3b8"

            stat = d.get("statistics", {})
            d_online_sec = safe_int(stat.get("online", 0))
            if d_online_sec == 0:
                d_online_sec = safe_int(d.get("uptime", 0))
            d_uptime_str = format_uptime_compact(d_online_sec)

            auth = d.get("authority", {})
            wan_allowed = auth.get("wan", 1) == 1
            is_ap = safe_int(d.get("isap", 0)) > 0
            is_admin = (auth.get("admin", 0) == 1) or (d.get("is_cur", 0) == 1) or is_ap

            parent_mac = (d.get("parent") or "").upper().strip()
            if is_ap:
                ap_point = t("mesh_satellite_badge", lg)
            elif parent_mac and parent_mac in ap_map:
                ap_point = f"🛰️ {ap_map[parent_mac]}"
            elif parent_mac:
                ap_point = f"🛰️ {('Satellite' if lg == 'en' else 'Satelita')} ({parent_mac[-5:]})"
            else:
                ap_point = t("mesh_root_badge", lg)

            items.append({
                "name": d_name,
                "ip": d_ip,
                "mac": d.get("mac", "-"),
                "type_code": is_type,
                "conn_type": conn_type,
                "badge_color": badge_color,
                "ap_point": ap_point,
                "downspeed": safe_float(stat.get("downspeed", 0)),
                "upspeed": safe_float(stat.get("upspeed", 0)),
                "online_sec": d_online_sec,
                "uptime_str": d_uptime_str,
                "wan_allowed": wan_allowed,
                "is_admin": is_admin,
                "is_offline": False
            })

        # 2. Urządzenia offline z rezerwacji DHCP
        show_offline = self.switch_show_offline.get() == 1 if hasattr(self, "switch_show_offline") else True
        offline_count = 0
        if show_offline:
            for b_mac, b in binds_by_mac.items():
                if b_mac not in active_macs:
                    offline_count += 1
                    b_name = b.get("name") or b.get("origin_name") or ("DHCP Reservation" if lg == "en" else "Rezerwacja DHCP")
                    b_ip = b.get("ip", "-")
                    items.append({
                        "name": b_name,
                        "ip": b_ip,
                        "mac": b.get("mac", "-"),
                        "type_code": 99,
                        "conn_type": "Offline",
                        "badge_color": "#64748b",
                        "ap_point": "-",
                        "downspeed": 0.0,
                        "upspeed": 0.0,
                        "online_sec": -1,
                        "uptime_str": "Not connected" if lg == "en" else "Brak w sieci",
                        "wan_allowed": True,
                        "is_admin": False,
                        "is_offline": True
                    })

        # 3. Filtr tekstowy
        filter_txt = self.entry_filter_devices.get().strip().lower() if hasattr(self, "entry_filter_devices") else ""
        if filter_txt:
            items = [
                it for it in items
                if filter_txt in it["name"].lower() or filter_txt in it["ip"].lower() or filter_txt in it["mac"].lower()
            ]

        # 4. Sortowanie
        sort_mode = self.combo_dev_sort.get().lower() if hasattr(self, "combo_dev_sort") else ""
        if "rosn" in sort_mode or "asc" in sort_mode:
            items.sort(key=lambda x: parse_ip_key(x["ip"]))
        elif "mal" in sort_mode or "desc" in sort_mode:
            items.sort(key=lambda x: parse_ip_key(x["ip"]), reverse=True)
        elif "a-z" in sort_mode:
            items.sort(key=lambda x: x["name"].lower())
        elif "z-a" in sort_mode:
            items.sort(key=lambda x: x["name"].lower(), reverse=True)
        elif "aktyw" in sort_mode or "active" in sort_mode:
            items.sort(key=lambda x: (1 if x["is_offline"] else 0, parse_ip_key(x["ip"])))
        elif "czas" in sort_mode or "time" in sort_mode:
            items.sort(key=lambda x: (-1 if x["is_offline"] else x["online_sec"]), reverse=True)
        elif "alfabet" in sort_mode:
            items.sort(key=lambda x: x["name"].lower())
        elif "ip" in sort_mode:
            items.sort(key=lambda x: parse_ip_key(x["ip"]))

        # 5. Aktualizacja licznika
        active_count = len(active_macs)
        cnt_text = f"Active: {active_count}" if lg == "en" else f"Aktywne: {active_count}"
        if show_offline:
            cnt_text += f" | Offline: {offline_count}"
        if filter_txt:
            cnt_text += f" | {('Results:' if lg == 'en' else 'Wyniki:')} {len(items)}"
        self.lbl_dev_count.configure(text=cnt_text)

        # 6. Renderowanie wierszy w scroll_devices
        if not items:
            ctk.CTkLabel(self.scroll_devices, text="No matching devices." if lg == "en" else "Brak pasujących urządzeń.", text_color="#94a3b8").pack(pady=20)
            return

        for it in items:
            row_f = ctk.CTkFrame(self.scroll_devices)
            row_f.pack(fill="x", padx=5, pady=3)

            # PRAWA STRONA NAJPIERW (gwarancja braku obcinania na węższych oknach)
            is_bound = ((it.get("mac") or "").upper() in binds_by_mac)

            if it["is_offline"]:
                if is_bound:
                    btn_del_bind = ctk.CTkButton(
                        row_f,
                        text=("Delete" if lg == "en" else "Usuń"),
                        width=60,
                        height=26,
                        fg_color="#dc2626",
                        hover_color="#991b1b",
                        command=lambda m=it["mac"], n=it["name"]: self._action_delete_mac_bind(m, n)
                    )
                    btn_del_bind.pack(side="right", padx=(3, 8))

                    btn_edit_bind = ctk.CTkButton(
                        row_f,
                        text=("Edit" if lg == "en" else "Edytuj"),
                        width=60,
                        height=26,
                        fg_color="#0284c7",
                        hover_color="#0369a1",
                        command=lambda m=it["mac"], n=it["name"], i=it["ip"]: self._dialog_edit_mac_bind(m, n, i)
                    )
                    btn_edit_bind.pack(side="right", padx=(3, 3))
                lbl_off = ctk.CTkLabel(row_f, text="Offline", text_color="#94a3b8", font=ctk.CTkFont(size=12, weight="bold"), width=75, anchor="e")
                lbl_off.pack(side="right", padx=(5, 10))
            elif it["is_admin"]:
                lbl_adm = ctk.CTkLabel(row_f, text="[Admin PC / AP]" if lg == "en" else "[Stacja Admina / AP]", text_color="#38bdf8", font=ctk.CTkFont(size=11, weight="bold"), width=130, anchor="e")
                lbl_adm.pack(side="right", padx=(5, 10))
            else:
                if lg == "en":
                    btn_txt = "Block Net" if it["wan_allowed"] else "Unblock Net"
                else:
                    btn_txt = "Blokuj Net" if it["wan_allowed"] else "Odblokuj Net"
                btn_color = "#475569" if it["wan_allowed"] else "#dc2626"
                btn_wan = ctk.CTkButton(
                    row_f,
                    text=btn_txt,
                    width=90,
                    height=26,
                    fg_color=btn_color,
                    hover_color="#334155" if it["wan_allowed"] else "#991b1b",
                    command=lambda m=it["mac"], cur=it["wan_allowed"]: self._action_toggle_dev_wan(m, cur)
                )
                btn_wan.pack(side="right", padx=(5, 10))

            # Wskaźnik i akcja rezerwacji DHCP dla urządzeń online
            if not it["is_offline"] and it.get("mac") and it["mac"] != "-":
                if is_bound:
                    btn_edit_bind = ctk.CTkButton(
                        row_f,
                        text=("Edit" if lg == "en" else "Edytuj"),
                        width=60,
                        height=26,
                        fg_color="#0284c7",
                        hover_color="#0369a1",
                        command=lambda m=it["mac"], n=it["name"], i=it["ip"]: self._dialog_edit_mac_bind(m, n, i)
                    )
                    btn_edit_bind.pack(side="right", padx=(3, 5))

                    lbl_bound = ctk.CTkLabel(
                        row_f,
                        text=("● Reserved" if lg == "en" else "● Stałe IP"),
                        text_color="#22c55e",
                        font=ctk.CTkFont(size=11, weight="bold"),
                        width=76,
                        anchor="e"
                    )
                    lbl_bound.pack(side="right", padx=(2, 4))
                else:
                    btn_bind = ctk.CTkButton(
                        row_f,
                        text=t("dev_btn_quick_bind", lg),
                        width=88,
                        height=26,
                        fg_color="#16a34a",
                        hover_color="#15803d",
                        command=lambda m=it["mac"], ip=it["ip"], n=it["name"]: self._dialog_add_mac_bind(prefill_mac=m, prefill_ip=ip, prefill_name=n)
                    )
                    btn_bind.pack(side="right", padx=(2, 4))

            # LEWA STRONA
            ctk.CTkLabel(row_f, text=it["name"], font=ctk.CTkFont(weight="bold"), width=155, anchor="w").pack(side="left", padx=(6, 3))
            ctk.CTkLabel(row_f, text=f"{it['ip']}", width=102, anchor="w", text_color="#38bdf8" if it["is_offline"] else None).pack(side="left", padx=3)
            ctk.CTkLabel(row_f, text=f"{it['mac']}", width=124, anchor="w").pack(side="left", padx=3)

            lbl_badge = ctk.CTkLabel(row_f, text=it["conn_type"], text_color=it["badge_color"], font=ctk.CTkFont(weight="bold"), width=82, anchor="w")
            lbl_badge.pack(side="left", padx=3)

            lbl_ap = ctk.CTkLabel(row_f, text=it.get("ap_point", "-"), text_color="#94a3b8", font=ctk.CTkFont(size=11), width=115, anchor="w")
            lbl_ap.pack(side="left", padx=3)

            if it["is_offline"]:
                ctk.CTkLabel(row_f, text="-", width=64, anchor="w", text_color="#64748b").pack(side="left", padx=2)
                ctk.CTkLabel(row_f, text="-", width=64, anchor="w", text_color="#64748b").pack(side="left", padx=2)
                ctk.CTkLabel(row_f, text="Offline", width=64, anchor="w", text_color="#64748b").pack(side="left", padx=2)
            else:
                ctk.CTkLabel(row_f, text=f"↓ {format_speed(it['downspeed'])}", text_color="#33a02c", width=68, anchor="w").pack(side="left", padx=2)
                ctk.CTkLabel(row_f, text=f"↑ {format_speed(it['upspeed'])}", text_color="#1f78b4", width=68, anchor="w").pack(side="left", padx=2)
                ctk.CTkLabel(row_f, text=it["uptime_str"], width=68, anchor="w", text_color="#94a3b8").pack(side="left", padx=2)

    # --- TOPOLOGIA I WĘZŁY MESH ---
    def _build_mesh_tab(self):
        tab = self.tab_mesh
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(1, weight=1)

        top_m = ctk.CTkFrame(tab, fg_color="transparent")
        top_m.grid(row=0, column=0, padx=10, pady=5, sticky="ew")

        self.lbl_mesh_title = ctk.CTkLabel(top_m, text=t("sub_dash_mesh", self.current_lang), font=ctk.CTkFont(size=16, weight="bold"))
        self.lbl_mesh_title.pack(side="left", padx=5)

        self.btn_ref_mesh = ctk.CTkButton(top_m, text="🔄 " + t("btn_refresh", self.current_lang), width=140, command=self._fetch_data_thread)
        self.btn_ref_mesh.pack(side="right", padx=5)

        self.scroll_mesh = ctk.CTkScrollableFrame(tab, corner_radius=10)
        self.scroll_mesh.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")
        self.scroll_mesh.grid_columnconfigure(0, weight=1)

    def _render_mesh_tab(self):
        for widget in self.scroll_mesh.winfo_children():
            widget.destroy()

        lg = self.current_lang
        topo = self.snapshot.get("topo_graph", {})
        graph = topo.get("graph", {})
        raw_devs = getattr(self, "raw_devices", [])

        # Słownik MAC urządzeń po IP
        mac_by_ip = {}
        for d in raw_devs:
            d_ip = d.get("ip")
            if isinstance(d_ip, list) and d_ip:
                d_ip = d_ip[0].get("ip")
            if d_ip and d.get("mac"):
                mac_by_ip[str(d_ip)] = d.get("mac")

        # Karta 1: Główny Router (Root / Controller)
        root_card = ctk.CTkFrame(self.scroll_mesh, fg_color="#1e293b", corner_radius=8, border_width=1, border_color="#3b82f6")
        root_card.pack(fill="x", padx=10, pady=(5, 10))

        r_hdr = ctk.CTkFrame(root_card, fg_color="transparent")
        r_hdr.pack(fill="x", padx=15, pady=(12, 6))

        r_badge = ctk.CTkLabel(r_hdr, text=t("mesh_root_card", lg), fg_color="#2563eb", text_color="#ffffff", corner_radius=6, font=ctk.CTkFont(size=12, weight="bold"))
        r_badge.pack(side="left")

        r_hw = graph.get("hardware", "")
        r_hw_name = "Xiaomi Router 7000 (BE7000)" if r_hw == "RC06" else ("Xiaomi Router BE6500" if r_hw == "RN02" else (r_hw or "Xiaomi Router"))
        r_name = graph.get("name") or ("Root" if lg == "en" else "Główny")
        ctk.CTkLabel(r_hdr, text=f" {r_hw_name} - {r_name} ", font=ctk.CTkFont(size=15, weight="bold")).pack(side="left", padx=10)

        r_body = ctk.CTkFrame(root_card, fg_color="transparent")
        r_body.pack(fill="x", padx=15, pady=(0, 8))

        ch_val = graph.get('channel', 'release')
        st_hw = self.snapshot.get("status", {}).get("hardware", {})
        wan_inf = self.snapshot.get("wan_info", {}).get("info", {}) if isinstance(self.snapshot.get("wan_info", {}).get("info"), dict) else self.snapshot.get("wan_info", {})
        r_mac = graph.get("mac") or (st_hw.get("mac") if isinstance(st_hw, dict) else None) or (wan_inf.get("mac") if isinstance(wan_inf, dict) else None) or "-"
        ctk.CTkLabel(r_body, text=f"IP: {graph.get('ip', self.client.ip)}  |  MAC: {r_mac}  |  SSID: {graph.get('ssid', '-')}  |  {t('mesh_channel', lg).format(channel=ch_val)}", text_color="#94a3b8").pack(side="left")

        # Podział aktywnych klientów (bez samych węzłów isap>0) na Master vs Satelity
        root_clients = []
        sat_clients_by_mac = {}
        for d in raw_devs:
            if safe_int(d.get("isap", 0)) > 0:
                continue
            d_name = d.get("name") or d.get("oname") or d.get("mac") or "?"
            p_mac = (d.get("parent") or "").upper().strip()
            if p_mac:
                sat_clients_by_mac.setdefault(p_mac, []).append(d_name)
            else:
                root_clients.append(d_name)

        onlines_count = max(safe_int(graph.get("onlines"), 0), len(root_clients))
        ctk.CTkLabel(r_body, text=t('mesh_net_devs', lg).format(count=onlines_count), text_color="#38bdf8", font=ctk.CTkFont(weight="bold")).pack(side="right")

        if root_clients:
            r_cli_lbl = ("Connected clients: " if lg == "en" else "Podłączeni klienci: ") + ", ".join(root_clients[:14])
            if len(root_clients) > 14:
                r_cli_lbl += f" (+{len(root_clients) - 14})"
            ctk.CTkLabel(root_card, text=r_cli_lbl, text_color="#cbd5e1", font=ctk.CTkFont(size=11), justify="left", anchor="w", wraplength=980).pack(fill="x", padx=15, pady=(0, 10))

        # Satelity Mesh (z leafs)
        leafs = graph.get("leafs", [])
        if not leafs and isinstance(graph.get("re"), list):
            leafs = graph.get("re", [])

        satellite_nodes = list(leafs)
        known_sat_ips = {str(s.get("ip")) for s in satellite_nodes if s.get("ip")}

        for d in raw_devs:
            if safe_int(d.get("isap", 0)) > 0 and d.get("ip"):
                d_ip = d.get("ip")
                if isinstance(d_ip, list) and d_ip:
                    d_ip = d_ip[0].get("ip")
                if d_ip and str(d_ip) != self.client.ip and str(d_ip) not in known_sat_ips:
                    satellite_nodes.append({
                        "name": d.get("name") or d.get("oname") or ("Satellite Node" if lg == "en" else "Węzeł Satelicki"),
                        "ip": str(d_ip),
                        "mac": d.get("mac", "-"),
                        "hardware": d.get("hardware") or "RN02",
                        "link_type": "wired" if safe_int(d.get("type", 1)) == 0 else "wifi"
                    })
                    known_sat_ips.add(str(d_ip))

        if not satellite_nodes:
            empty_box = ctk.CTkFrame(self.scroll_mesh, fg_color="#18202f", corner_radius=8)
            empty_box.pack(fill="x", padx=10, pady=15)
            ctk.CTkLabel(
                empty_box,
                text=t("mesh_no_nodes", lg),
                justify="left", text_color="#94a3b8", font=ctk.CTkFont(size=12)
            ).pack(padx=20, pady=18, anchor="w")
            return

        ctk.CTkLabel(self.scroll_mesh, text=t("mesh_heading", lg), font=ctk.CTkFont(size=14, weight="bold")).pack(anchor="w", padx=10, pady=(10, 5))

        for sat in satellite_nodes:
            sat_card = ctk.CTkFrame(self.scroll_mesh, fg_color="#1e293b", corner_radius=8)
            sat_card.pack(fill="x", padx=10, pady=6)

            s_top = ctk.CTkFrame(sat_card, fg_color="transparent")
            s_top.pack(fill="x", padx=15, pady=(10, 4))

            s_badge = ctk.CTkLabel(s_top, text=t("mesh_sat_card", lg), fg_color="#0d9488", text_color="#ffffff", corner_radius=6, font=ctk.CTkFont(size=11, weight="bold"))
            s_badge.pack(side="left")

            s_hw = sat.get("hardware", "")
            s_hw_name = "Xiaomi Router BE6500" if s_hw == "RN02" else ("Xiaomi Router 7000" if s_hw == "RC06" else s_hw)
            s_name = sat.get("name") or ("Satellite" if lg == "en" else "Satelita")
            ctk.CTkLabel(s_top, text=f" {s_hw_name} - {s_name} ", font=ctk.CTkFont(size=14, weight="bold")).pack(side="left", padx=8)

            s_ip = str(sat.get("ip", "-"))
            s_mac = sat.get("mac") or mac_by_ip.get(s_ip, "-")

            btn_reboot_sat = ctk.CTkButton(
                s_top, text=t("mesh_reboot_node", lg), width=130, height=26,
                fg_color="#d97706", hover_color="#b45309",
                command=lambda ip=s_ip: self._reboot_mesh_satellite(ip)
            )
            btn_reboot_sat.pack(side="right")

            s_bot = ctk.CTkFrame(sat_card, fg_color="transparent")
            s_bot.pack(fill="x", padx=15, pady=(0, 10))

            link_t = str(sat.get("link_type") or sat.get("backhaul") or "").lower()
            if "wire" in link_t or "kabel" in link_t or "lan" in link_t or sat.get("mode") == 0:
                bh_text = t("mesh_wired_bh", lg)
                bh_color = "#22c55e"
            else:
                bh_text = t("mesh_wifi_bh", lg)
                bh_color = "#38bdf8"

            s_onlines = sat.get("onlines", 0)

            ctk.CTkLabel(s_bot, text=f"IP: {s_ip}  |  MAC: {s_mac}  |  ", text_color="#94a3b8").pack(side="left")
            ctk.CTkLabel(s_bot, text=bh_text, text_color=bh_color, font=ctk.CTkFont(weight="bold")).pack(side="left")
            ctk.CTkLabel(s_bot, text=f"  |  {t('mesh_connected_clients', lg).format(count=s_onlines)}", text_color="#38bdf8", font=ctk.CTkFont(weight="bold")).pack(side="left")

            sat_keys = {str(s_mac).upper().strip(), str(sat.get("mac") or "").upper().strip(), str(sat.get("id") or "").upper().strip()}
            sat_clients = []
            for sk in sat_keys:
                if sk and sk in sat_clients_by_mac:
                    sat_clients.extend(sat_clients_by_mac[sk])
            if sat_clients:
                s_cli_txt = ("Connected clients: " if lg == "en" else "Podłączeni klienci: ") + ", ".join(sat_clients[:14])
                if len(sat_clients) > 14:
                    s_cli_txt += f" (+{len(sat_clients) - 14})"
                ctk.CTkLabel(sat_card, text=s_cli_txt, text_color="#cbd5e1", font=ctk.CTkFont(size=11), justify="left", anchor="w", wraplength=980).pack(fill="x", padx=15, pady=(0, 10))

    def _reboot_mesh_satellite(self, node_ip: str):
        if not node_ip or node_ip == "-":
            return
        if not messagebox.askyesno("Potwierdzenie restartu", f"Czy na pewno chcesz zrestartować węzeł satelicki Mesh ({node_ip})?"):
            return
        def do_reboot():
            res = self.client.reboot_mesh_node(node_ip)
            if res.get("code") == 0 or not res.get("error"):
                self.after(0, lambda: messagebox.showinfo("Restart węzła", f"Polecenie restartu zostało wysłane do węzła {node_ip}."))
            else:
                self.after(0, lambda: messagebox.showerror("Błąd", f"Nie udało się zrestartować węzła: {res.get('error') or res}"))
        threading.Thread(target=do_reboot, daemon=True).start()

    # --- USTAWIENIA WAN ---
    def _build_wan_tab(self):
        lg = self.current_lang
        tab = self.tab_wan
        tab.grid_columnconfigure((0, 1), weight=1)
        tab.grid_rowconfigure(0, weight=1)

        # Lewa kolumna: Status WAN (Live Info)
        card_status = ctk.CTkFrame(tab)
        card_status.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        ctk.CTkLabel(card_status, text=t("wan_status_title", lg), font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", padx=15, pady=(15, 10))

        self.lbl_wan_link = ctk.CTkLabel(card_status, text=f"{t('wan_lbl_link', lg)} ...", anchor="w")
        self.lbl_wan_link.pack(fill="x", padx=15, pady=3)

        self.lbl_wan_uptime = ctk.CTkLabel(card_status, text=f"{t('wan_lbl_uptime', lg)} -", anchor="w")
        self.lbl_wan_uptime.pack(fill="x", padx=15, pady=3)

        self.lbl_wan_type_info = ctk.CTkLabel(card_status, text=f"{t('wan_lbl_type', lg)} -", anchor="w")
        self.lbl_wan_type_info.pack(fill="x", padx=15, pady=3)

        self.lbl_wan_ip_val = ctk.CTkLabel(card_status, text=f"{t('wan_lbl_ip', lg)} -", font=ctk.CTkFont(weight="bold"), anchor="w")
        self.lbl_wan_ip_val.pack(fill="x", padx=15, pady=3)

        self.lbl_wan_mask_val = ctk.CTkLabel(card_status, text=f"{t('wan_lbl_mask', lg)} -", anchor="w")
        self.lbl_wan_mask_val.pack(fill="x", padx=15, pady=3)

        self.lbl_wan_gw_val = ctk.CTkLabel(card_status, text=f"{t('wan_lbl_gw', lg)} -", anchor="w")
        self.lbl_wan_gw_val.pack(fill="x", padx=15, pady=3)

        self.lbl_wan_dns_val = ctk.CTkLabel(card_status, text=f"{t('wan_lbl_dns', lg)} -", anchor="w")
        self.lbl_wan_dns_val.pack(fill="x", padx=15, pady=3)

        self.lbl_wan_mac_val = ctk.CTkLabel(card_status, text=f"{t('wan_lbl_mac', lg)} -", anchor="w")
        self.lbl_wan_mac_val.pack(fill="x", padx=15, pady=3)

        self.lbl_wan_ipv6_val = ctk.CTkLabel(card_status, text=f"{t('wan_lbl_ipv6', lg)} -", anchor="w")
        self.lbl_wan_ipv6_val.pack(fill="x", padx=15, pady=3)

        self.lbl_wan_mtu_val = ctk.CTkLabel(card_status, text=f"{t('wan_lbl_mtu', lg)} -", font=ctk.CTkFont(weight="bold"), anchor="w")
        self.lbl_wan_mtu_val.pack(fill="x", padx=15, pady=3)

        btn_restart_pppoe = ctk.CTkButton(card_status, text=t("wan_btn_restart_pppoe", lg), fg_color="#d97706", hover_color="#b45309", command=self._action_restart_pppoe)
        btn_restart_pppoe.pack(fill="x", padx=15, pady=(20, 10))

        # Prawa kolumna: Formularz Konfiguracji WAN
        card_cfg = ctk.CTkScrollableFrame(tab)
        card_cfg.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        ctk.CTkLabel(card_cfg, text=t("wan_cfg_title", lg), font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", padx=10, pady=(10, 10))

        f_mode_row = ctk.CTkFrame(card_cfg, fg_color="transparent")
        f_mode_row.pack(fill="x", padx=10, pady=(5, 10))
        ctk.CTkLabel(f_mode_row, text=t("wan_lbl_select_type", lg), font=ctk.CTkFont(weight="bold")).pack(side="left", padx=(0, 10))
        wan_modes = [
            ("PPPoE (Login i hasło światłowodu / Neostrady)" if lg == "pl" else "PPPoE (Fiber / Broadband Login)"),
            ("DHCP (Automatyczny IP od modemu / dostawcy)" if lg == "pl" else "DHCP (Automatic IP from Modem)"),
            ("Statyczny IP (Stała adresacja ręczna)" if lg == "pl" else "Static IP (Manual Addressing)")
        ]
        self.seg_wan_mode = ctk.CTkOptionMenu(f_mode_row, values=wan_modes, command=self._on_wan_mode_change)
        self.seg_wan_mode.set(wan_modes[0])
        self.seg_wan_mode.pack(side="left", fill="x", expand=True)

        # Sekcja PPPoE
        self.frame_wan_pppoe = ctk.CTkFrame(card_cfg, fg_color="transparent")
        self.frame_wan_pppoe.pack(fill="x", padx=5, pady=2)
        ctk.CTkLabel(self.frame_wan_pppoe, text=t("wan_lbl_user", lg)).pack(anchor="w", padx=5, pady=(2, 0))
        self.entry_wan_user = ctk.CTkEntry(self.frame_wan_pppoe, placeholder_text=t("wan_ph_user", lg))
        self.entry_wan_user.pack(fill="x", padx=5, pady=(2, 6))

        ctk.CTkLabel(self.frame_wan_pppoe, text=t("wan_lbl_pwd", lg)).pack(anchor="w", padx=5, pady=(2, 0))
        self.entry_wan_pwd = ctk.CTkEntry(self.frame_wan_pppoe, placeholder_text=t("wan_ph_pwd", lg), show="•")
        self.entry_wan_pwd.pack(fill="x", padx=5, pady=(2, 2))

        self.cb_show_wan_pwd = ctk.CTkCheckBox(self.frame_wan_pppoe, text=t("wan_show_pwd", lg), command=self._toggle_show_wan_pwd)
        self.cb_show_wan_pwd.pack(anchor="w", padx=5, pady=(2, 8))

        # Sekcja Statyczny IP
        self.frame_wan_static = ctk.CTkFrame(card_cfg, fg_color="transparent")
        ctk.CTkLabel(self.frame_wan_static, text=t("wan_lbl_static_ip", lg)).pack(anchor="w", padx=5, pady=(2, 0))
        self.entry_wan_static_ip = ctk.CTkEntry(self.frame_wan_static, placeholder_text="np. 192.168.1.100")
        self.entry_wan_static_ip.pack(fill="x", padx=5, pady=(2, 6))
        ctk.CTkLabel(self.frame_wan_static, text=t("wan_lbl_static_mask", lg)).pack(anchor="w", padx=5, pady=(2, 0))
        self.entry_wan_static_mask = ctk.CTkEntry(self.frame_wan_static, placeholder_text="255.255.255.0")
        self.entry_wan_static_mask.pack(fill="x", padx=5, pady=(2, 6))
        ctk.CTkLabel(self.frame_wan_static, text=t("wan_lbl_static_gw", lg)).pack(anchor="w", padx=5, pady=(2, 0))
        self.entry_wan_static_gw = ctk.CTkEntry(self.frame_wan_static, placeholder_text="np. 192.168.1.1")
        self.entry_wan_static_gw.pack(fill="x", padx=5, pady=(2, 8))

        # Sekcja Wspólna: MTU i DNS
        f_common = ctk.CTkFrame(card_cfg, fg_color="transparent")
        f_common.pack(fill="x", padx=5, pady=2)
        self.f_common_wan = f_common

        ctk.CTkLabel(f_common, text=t("wan_lbl_mtu_desc", lg), font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=5, pady=(4, 1))
        ctk.CTkLabel(
            f_common,
            text=t("wan_hint_mtu", lg),
            text_color="#94a3b8",
            font=ctk.CTkFont(size=11),
            wraplength=420,
            justify="left"
        ).pack(anchor="w", padx=5, pady=(0, 4))

        f_mtu_row = ctk.CTkFrame(f_common, fg_color="transparent")
        f_mtu_row.pack(fill="x", padx=5, pady=(0, 6))

        self.entry_wan_mtu = ctk.CTkEntry(f_mtu_row, width=130, placeholder_text="np. 1500")
        self.entry_wan_mtu.pack(side="left", padx=(0, 8))

        ctk.CTkButton(
            f_mtu_row, text=t("wan_btn_mtu_fiber", lg), width=110, height=28, fg_color="#334155", hover_color="#475569", font=ctk.CTkFont(size=11),
            command=lambda: (self.entry_wan_mtu.delete(0, "end"), self.entry_wan_mtu.insert(0, "1472"))
        ).pack(side="left", padx=2)
        ctk.CTkButton(
            f_mtu_row, text=t("wan_btn_mtu_pppoe", lg), width=85, height=28, fg_color="#334155", hover_color="#475569", font=ctk.CTkFont(size=11),
            command=lambda: (self.entry_wan_mtu.delete(0, "end"), self.entry_wan_mtu.insert(0, "1492"))
        ).pack(side="left", padx=2)
        ctk.CTkButton(
            f_mtu_row, text=t("wan_btn_mtu_std", lg), width=75, height=28, fg_color="#334155", hover_color="#475569", font=ctk.CTkFont(size=11),
            command=lambda: (self.entry_wan_mtu.delete(0, "end"), self.entry_wan_mtu.insert(0, "1500"))
        ).pack(side="left", padx=2)

        self.switch_wan_custom_dns = ctk.CTkSwitch(f_common, text=t("wan_switch_custom_dns", lg), command=self._toggle_custom_dns)
        self.switch_wan_custom_dns.pack(anchor="w", padx=5, pady=4)

        self.entry_wan_dns1 = ctk.CTkEntry(f_common, placeholder_text=t("wan_ph_dns1", lg))
        self.entry_wan_dns1.pack(fill="x", padx=5, pady=2)
        self.entry_wan_dns2 = ctk.CTkEntry(f_common, placeholder_text=t("wan_ph_dns2", lg))
        self.entry_wan_dns2.pack(fill="x", padx=5, pady=(2, 10))

        # Klonowanie MAC
        f_mac = ctk.CTkFrame(card_cfg, fg_color="transparent")
        f_mac.pack(fill="x", padx=5, pady=2)
        ctk.CTkLabel(f_mac, text=t("wan_lbl_clone_mac", lg)).pack(anchor="w", padx=5, pady=(2, 0))
        self.entry_clone_mac = ctk.CTkEntry(f_mac, placeholder_text="Nowy adres MAC (opcjonalnie)...")
        self.entry_clone_mac.pack(fill="x", padx=5, pady=(2, 4))
        btn_clone_apply = ctk.CTkButton(f_mac, text=("Apply MAC clone" if lg == "en" else "Zastosuj klonowanie MAC"), fg_color="#475569", hover_color="#334155", command=self._action_clone_mac)
        btn_clone_apply.pack(fill="x", padx=5, pady=(0, 15))

        # Przycisk Zastosuj
        btn_save_wan = ctk.CTkButton(card_cfg, text=t("wan_btn_apply", lg), font=ctk.CTkFont(weight="bold"), fg_color="#2563eb", hover_color="#1d4ed8", height=38, command=self._action_save_wan)
        btn_save_wan.pack(fill="x", padx=10, pady=(10, 15))

    def _on_wan_mode_change(self, mode):
        m_low = str(mode).lower()
        if "pppoe" in m_low:
            self.frame_wan_pppoe.pack(fill="x", padx=5, pady=2, before=self.f_common_wan)
            self.frame_wan_static.pack_forget()
            if not self.entry_wan_mtu.get().strip():
                self.entry_wan_mtu.insert(0, "1472")
        elif "stat" in m_low:
            self.frame_wan_pppoe.pack_forget()
            self.frame_wan_static.pack(fill="x", padx=5, pady=2, before=self.f_common_wan)
            if not self.entry_wan_mtu.get().strip():
                self.entry_wan_mtu.insert(0, "1500")
        else:  # DHCP
            self.frame_wan_pppoe.pack_forget()
            self.frame_wan_static.pack_forget()
            if not self.entry_wan_mtu.get().strip():
                self.entry_wan_mtu.insert(0, "1500")

    def _toggle_show_wan_pwd(self):
        show_char = "" if self.cb_show_wan_pwd.get() == 1 else "•"
        self.entry_wan_pwd.configure(show=show_char)

    def _toggle_custom_dns(self):
        enabled = self.switch_wan_custom_dns.get() == 1
        state = "normal" if enabled else "disabled"
        self.entry_wan_dns1.configure(state=state)
        self.entry_wan_dns2.configure(state=state)

    # --- USTAWIENIA LAN ---
    def _build_lan_tab(self):
        lg = self.current_lang
        tab = self.tab_lan
        tab.grid_columnconfigure((0, 1), weight=1)
        tab.grid_rowconfigure(1, weight=1)

        # 1. Karta lewa: Adresacja LAN
        card_lan_ip = ctk.CTkFrame(tab)
        card_lan_ip.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="nsew")
        ctk.CTkLabel(card_lan_ip, text=t("lan_card_addr", lg), font=ctk.CTkFont(size=15, weight="bold")).pack(anchor="w", padx=15, pady=(10, 6))

        f_ip = ctk.CTkFrame(card_lan_ip, fg_color="transparent")
        f_ip.pack(fill="x", padx=15, pady=2)
        ctk.CTkLabel(f_ip, text=t("lan_lbl_ip", lg)).pack(side="left")
        self.entry_lan_ip = ctk.CTkEntry(f_ip, width=150)
        self.entry_lan_ip.insert(0, "192.168.31.1")
        self.entry_lan_ip.pack(side="right")

        f_mask = ctk.CTkFrame(card_lan_ip, fg_color="transparent")
        f_mask.pack(fill="x", padx=15, pady=4)
        ctk.CTkLabel(f_mask, text=t("lan_lbl_mask", lg)).pack(side="left")
        self.entry_lan_mask = ctk.CTkEntry(f_mask, width=150)
        self.entry_lan_mask.insert(0, "255.255.255.0")
        self.entry_lan_mask.pack(side="right")

        btn_save_lan_ip = ctk.CTkButton(card_lan_ip, text=("Apply Gateway IP" if lg == "en" else "Zastosuj Adres IP Bramy LAN"), fg_color="#dc2626", hover_color="#991b1b", font=ctk.CTkFont(weight="bold"), command=self._action_save_lan_ip)
        btn_save_lan_ip.pack(fill="x", padx=15, pady=(8, 10))

        # 2. Karta prawa: Serwer DHCP
        card_dhcp = ctk.CTkFrame(tab)
        card_dhcp.grid(row=0, column=1, padx=10, pady=(10, 5), sticky="nsew")
        ctk.CTkLabel(card_dhcp, text=t("lan_card_dhcp", lg), font=ctk.CTkFont(size=15, weight="bold")).pack(anchor="w", padx=15, pady=(10, 6))

        f_pool = ctk.CTkFrame(card_dhcp, fg_color="transparent")
        f_pool.pack(fill="x", padx=15, pady=2)
        ctk.CTkLabel(f_pool, text=f"{t('lan_lbl_start', lg)} / {t('lan_lbl_limit', lg)}").pack(side="left")
        self.entry_dhcp_limit = ctk.CTkEntry(f_pool, width=70)
        self.entry_dhcp_limit.insert(0, "250")
        self.entry_dhcp_limit.pack(side="right", padx=(4, 0))
        self.entry_dhcp_start = ctk.CTkEntry(f_pool, width=70)
        self.entry_dhcp_start.insert(0, "5")
        self.entry_dhcp_start.pack(side="right")

        f_lease = ctk.CTkFrame(card_dhcp, fg_color="transparent")
        f_lease.pack(fill="x", padx=15, pady=2)
        ctk.CTkLabel(f_lease, text=t("lan_lbl_lease", lg)).pack(side="left")
        self.entry_dhcp_lease = ctk.CTkEntry(f_lease, width=150, placeholder_text="np. 720, 1440")
        self.entry_dhcp_lease.insert(0, "720")
        self.entry_dhcp_lease.pack(side="right")

        f_dns = ctk.CTkFrame(card_dhcp, fg_color="transparent")
        f_dns.pack(fill="x", padx=15, pady=2)
        ctk.CTkLabel(f_dns, text=t("lan_lbl_dns", lg)).pack(side="left")
        self.entry_dhcp_dns2 = ctk.CTkEntry(f_dns, width=110)
        self.entry_dhcp_dns2.insert(0, "192.168.31.1")
        self.entry_dhcp_dns2.pack(side="right", padx=(4, 0))
        self.entry_dhcp_dns1 = ctk.CTkEntry(f_dns, width=110)
        self.entry_dhcp_dns1.insert(0, "192.168.31.12")
        self.entry_dhcp_dns1.pack(side="right")

        btn_save_dhcp = ctk.CTkButton(card_dhcp, text=t("lan_btn_save", lg), fg_color="#2563eb", hover_color="#1d4ed8", command=self._action_save_dhcp)
        btn_save_dhcp.pack(fill="x", padx=15, pady=(8, 10))

        # 3. Dolna karta: Tabela Rezerwacji Stałych IP
        card_binds = ctk.CTkFrame(tab)
        card_binds.grid(row=1, column=0, columnspan=2, padx=10, pady=(5, 10), sticky="nsew")
        card_binds.grid_columnconfigure(0, weight=1)
        card_binds.grid_rowconfigure(1, weight=1)

        bar_binds = ctk.CTkFrame(card_binds, fg_color="transparent")
        bar_binds.grid(row=0, column=0, padx=10, pady=(10, 5), sticky="ew")

        self.lbl_bind_count = ctk.CTkLabel(bar_binds, text=f"{t('lan_card_binds', lg)}: 0", font=ctk.CTkFont(size=15, weight="bold"))
        self.lbl_bind_count.pack(side="left", padx=5)

        btn_add_bind = ctk.CTkButton(bar_binds, text=f"+ {t('lan_btn_add_bind', lg)}", fg_color="#16a34a", hover_color="#15803d", width=180, command=self._dialog_add_mac_bind)
        btn_add_bind.pack(side="right", padx=5)

        self.entry_filter_bind = ctk.CTkEntry(bar_binds, placeholder_text=t("lan_ph_search_bind", lg), width=180)
        self.entry_filter_bind.pack(side="right", padx=(5, 10))
        self.entry_filter_bind.bind("<KeyRelease>", lambda e: self._filter_mac_bind_list())

        bind_sort_vals = [
            "Kolejność routera (domyślnie)",
            "Adres IP (rosnąco)",
            "Adres IP (malejąco)",
            "Nazwa (A-Z)",
            "Nazwa (Z-A)"
        ] if lg == "pl" else [
            "Router Default",
            "IP Address (Ascending)",
            "IP Address (Descending)",
            "Name (A-Z)",
            "Name (Z-A)"
        ]
        self.combo_bind_sort = ctk.CTkOptionMenu(
            bar_binds,
            values=bind_sort_vals,
            width=200,
            command=lambda v: self._filter_mac_bind_list()
        )
        self.combo_bind_sort.set(bind_sort_vals[0])
        self.combo_bind_sort.pack(side="right", padx=5)

        self.scroll_binds = ctk.CTkScrollableFrame(card_binds, corner_radius=8)
        self.scroll_binds.grid(row=1, column=0, padx=10, pady=(0, 10), sticky="nsew")
        self.scroll_binds.grid_columnconfigure(0, weight=1)

    def _filter_mac_bind_list(self):
        txt = self.entry_filter_bind.get().strip().lower()
        self._render_mac_bind_list(txt)

    def _render_mac_bind_list(self, filter_text=""):
        lg = self.current_lang
        for w in self.scroll_binds.winfo_children():
            w.destroy()

        binds = list(getattr(self, "raw_binds", []))
        if filter_text:
            binds = [b for b in binds if filter_text in (b.get("name") or "").lower() or filter_text in (b.get("ip") or "").lower() or filter_text in (b.get("mac") or "").lower()]

        sort_mode = self.combo_bind_sort.get().lower() if hasattr(self, "combo_bind_sort") else ""
        if "rosn" in sort_mode or "asc" in sort_mode:
            binds.sort(key=lambda b: parse_ip_key(b.get("ip", "")))
        elif "mal" in sort_mode or "desc" in sort_mode:
            binds.sort(key=lambda b: parse_ip_key(b.get("ip", "")), reverse=True)
        elif "a-z" in sort_mode:
            binds.sort(key=lambda b: (b.get("name") or b.get("origin_name") or "").lower())
        elif "z-a" in sort_mode:
            binds.sort(key=lambda b: (b.get("name") or b.get("origin_name") or "").lower(), reverse=True)

        total_binds = len(getattr(self, "raw_binds", []))
        lbl_head = ("Static DHCP Leases (Total: {count})" if lg == "en" else "Statyczne Rezerwacje IP (Łącznie: {count})").format(count=total_binds)
        if filter_text:
            lbl_head += f" | {('Filter results:' if lg == 'en' else 'Wyniki filtra:')} {len(binds)}"
        self.lbl_bind_count.configure(text=lbl_head)

        if not binds:
            ctk.CTkLabel(self.scroll_binds, text=("No matching IP reservations found." if lg == "en" else "Brak pasujących rezerwacji IP w tabeli."), text_color="#94a3b8").pack(pady=20)
            return

        for b in binds:
            b_name = b.get("name") or b.get("origin_name") or ("No name" if lg == "en" else "Bez nazwy")
            b_ip = b.get("ip", "-")
            b_mac = b.get("mac", "-")

            row_f = ctk.CTkFrame(self.scroll_binds)
            row_f.pack(fill="x", padx=5, pady=3)

            # Prawa strona najpierw (gwarancja braku clippingu)
            btn_del = ctk.CTkButton(
                row_f,
                text=t("btn_delete", lg),
                width=70,
                height=26,
                fg_color="#dc2626",
                hover_color="#991b1b",
                command=lambda m=b_mac, n=b_name: self._action_delete_mac_bind(m, n)
            )
            btn_del.pack(side="right", padx=(5, 10))

            btn_edit = ctk.CTkButton(
                row_f,
                text=t("btn_edit", lg),
                width=70,
                height=26,
                fg_color="#0284c7",
                hover_color="#0369a1",
                command=lambda m=b_mac, n=b_name, i=b_ip: self._dialog_edit_mac_bind(m, n, i)
            )
            btn_edit.pack(side="right", padx=5)

            # Lewa strona
            ctk.CTkLabel(row_f, text=f"{b_name}", font=ctk.CTkFont(weight="bold"), width=220, anchor="w").pack(side="left", padx=10)
            ctk.CTkLabel(row_f, text=f"IP: {b_ip}", width=140, anchor="w", text_color="#38bdf8", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=5)
            ctk.CTkLabel(row_f, text=f"MAC: {b_mac}", width=160, anchor="w").pack(side="left", padx=5)

    def _dialog_edit_mac_bind(self, orig_mac: str, orig_name: str, orig_ip: str):
        if not self.client.connected:
            messagebox.showinfo("Błąd", "Najpierw połącz się z routerem.")
            return

        lg = self.current_lang
        dialog = ctk.CTkToplevel(self)
        dialog.title(t("dhcp_dlg_edit_title", lg))
        dialog.geometry("480x360")
        dialog.resizable(False, False)
        dialog.grab_set()

        ctk.CTkLabel(dialog, text=t("dhcp_dlg_edit_heading", lg).format(name=orig_name), font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(15, 10))

        f_form = ctk.CTkFrame(dialog, fg_color="transparent")
        f_form.pack(fill="x", padx=25, pady=5)

        ctk.CTkLabel(f_form, text=t("dhcp_dlg_dev_name", lg)).pack(anchor="w")
        ent_name = ctk.CTkEntry(f_form)
        ent_name.insert(0, orig_name)
        ent_name.pack(fill="x", pady=(2, 8))

        ctk.CTkLabel(f_form, text=t("dhcp_dlg_mac", lg)).pack(anchor="w")
        ent_mac = ctk.CTkEntry(f_form)
        ent_mac.insert(0, orig_mac)
        ent_mac.pack(fill="x", pady=(2, 8))

        ctk.CTkLabel(f_form, text=t("dhcp_dlg_static_ip", lg)).pack(anchor="w")
        ent_ip = ctk.CTkEntry(f_form)
        ent_ip.insert(0, orig_ip)
        ent_ip.pack(fill="x", pady=(2, 15))

        def do_update():
            new_name = ent_name.get().strip()
            new_mac = ent_mac.get().strip()
            new_ip = ent_ip.get().strip()
            if not new_name or not new_mac or not new_ip:
                messagebox.showerror(t("err_title", lg), t("dhcp_dlg_err_fields", lg), parent=dialog)
                return

            try:
                if new_mac.lower() != orig_mac.lower() or new_ip != orig_ip:
                    self.client.remove_mac_bind(orig_mac)

                res = self.client.add_mac_bind(new_mac, new_ip, new_name)
                if res.get("code") == 0:
                    messagebox.showinfo(t("succ_title", lg), t("dhcp_dlg_succ_updated", lg).format(name=new_name), parent=dialog)
                    dialog.destroy()
                    self._fetch_data_thread()
                else:
                    messagebox.showwarning(t("notice_title", lg), f"Router: {res}", parent=dialog)
            except Exception as e:
                messagebox.showerror(t("err_title", lg), f"{e}", parent=dialog)

        btn_box = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_box.pack(fill="x", padx=25, pady=10)

        ctk.CTkButton(btn_box, text=t("dhcp_dlg_btn_cancel", lg), fg_color="#475569", width=120, command=dialog.destroy).pack(side="left")
        ctk.CTkButton(btn_box, text=t("dhcp_dlg_btn_save", lg), fg_color="#0284c7", hover_color="#0369a1", width=160, command=do_update).pack(side="right")

    def _dialog_add_mac_bind(self, prefill_mac: str = None, prefill_ip: str = None, prefill_name: str = None):
        if not self.client.connected:
            messagebox.showinfo(t("err_title", self.current_lang), t("err_not_connected", self.current_lang))
            return

        lg = self.current_lang
        dialog = ctk.CTkToplevel(self)
        dialog.title(t("dhcp_dlg_add_title", lg))
        dialog.geometry("480x420")
        dialog.resizable(False, False)
        dialog.grab_set()

        heading = t("dhcp_dlg_quick_add_heading", lg) if prefill_mac else t("dhcp_dlg_add_heading", lg)
        ctk.CTkLabel(dialog, text=heading, font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(15, 10))

        if not prefill_mac:
            # Opcja wyboru z aktualnie wykrytych urządzeń
            online_devs = self.snapshot.get("device_list", {}).get("list", []) if self.snapshot else []
            dev_map = {}
            dev_options = [t("hint_manual_entry", lg)]
            for d in online_devs:
                d_n = d.get("name") or d.get("oname") or ("Unknown" if lg == "en" else "Nieznane")
                d_m = d.get("mac", "")
                d_i = d.get("ip", [{}])[0].get("ip") if isinstance(d.get("ip"), list) and d.get("ip") else str(d.get("ip", ""))
                opt_label = f"{d_n} ({d_i} / {d_m})"
                dev_options.append(opt_label)
                dev_map[opt_label] = (d_n, d_m, d_i)

            f_select = ctk.CTkFrame(dialog, fg_color="transparent")
            f_select.pack(fill="x", padx=25, pady=5)
            ctk.CTkLabel(f_select, text=t("dhcp_dlg_select_active", lg)).pack(anchor="w")

            def on_device_select(choice):
                if choice in dev_map:
                    n, m, i = dev_map[choice]
                    ent_name.delete(0, "end")
                    ent_name.insert(0, n)
                    ent_mac.delete(0, "end")
                    ent_mac.insert(0, m)
                    ent_ip.delete(0, "end")
                    ent_ip.insert(0, i)

            combo_dev = ctk.CTkComboBox(f_select, values=dev_options, width=420, command=on_device_select)
            combo_dev.pack(fill="x", pady=(2, 8))
        else:
            f_info = ctk.CTkFrame(dialog, fg_color="transparent")
            f_info.pack(fill="x", padx=25, pady=5)
            ctk.CTkLabel(f_info, text=t("dhcp_dlg_quick_info", lg).format(mac=prefill_mac), text_color="#10b981", font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(2, 8))

        f_form = ctk.CTkFrame(dialog, fg_color="transparent")
        f_form.pack(fill="x", padx=25, pady=5)

        ctk.CTkLabel(f_form, text=t("dhcp_dlg_dev_name", lg)).pack(anchor="w")
        ent_name = ctk.CTkEntry(f_form, placeholder_text=t("dhcp_dlg_ph_dev_name", lg))
        ent_name.pack(fill="x", pady=(2, 8))
        if prefill_name:
            ent_name.insert(0, prefill_name)

        ctk.CTkLabel(f_form, text=t("dhcp_dlg_mac_hint", lg)).pack(anchor="w")
        ent_mac = ctk.CTkEntry(f_form, placeholder_text=t("dhcp_dlg_ph_mac", lg))
        ent_mac.pack(fill="x", pady=(2, 8))
        if prefill_mac:
            ent_mac.insert(0, prefill_mac)
            ent_mac.configure(state="disabled")

        ctk.CTkLabel(f_form, text=t("dhcp_dlg_static_ip", lg)).pack(anchor="w")
        ent_ip = ctk.CTkEntry(f_form, placeholder_text=t("dhcp_dlg_ph_ip", lg))
        ent_ip.pack(fill="x", pady=(2, 15))
        if prefill_ip and prefill_ip != "-":
            ent_ip.insert(0, prefill_ip)

        def do_save():
            name = ent_name.get().strip()
            mac = prefill_mac if prefill_mac else ent_mac.get().strip()
            ip = ent_ip.get().strip()
            if not name or not mac or not ip:
                messagebox.showerror(t("err_title", lg), t("dhcp_dlg_err_fields", lg), parent=dialog)
                return

            try:
                res = self.client.add_mac_bind(mac, ip, name)
                if res.get("code") == 0:
                    messagebox.showinfo(t("succ_title", lg), t("dhcp_dlg_succ_added", lg).format(name=name), parent=dialog)
                    dialog.destroy()
                    self._fetch_data_thread()
                else:
                    messagebox.showwarning(t("notice_title", lg), f"Router: {res}", parent=dialog)
            except Exception as e:
                messagebox.showerror(t("err_title", lg), f"{e}", parent=dialog)

        btn_box = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_box.pack(fill="x", padx=25, pady=10)

        ctk.CTkButton(btn_box, text=t("dhcp_dlg_btn_cancel", lg), fg_color="#475569", width=120, command=dialog.destroy).pack(side="left")
        ctk.CTkButton(btn_box, text=t("dhcp_dlg_btn_add", lg), fg_color="#16a34a", hover_color="#15803d", width=160, command=do_save).pack(side="right")

    # --- WI-FI I PASMA ---
    def _build_wifi_tab(self):
        lg = self.current_lang
        tab = self.tab_wifi
        tab.grid_columnconfigure((0, 1), weight=1)
        tab.grid_rowconfigure(2, weight=1)

        # 1. Górny pasek globalnych kontrolek Wi-Fi
        wifi_top = ctk.CTkFrame(tab, fg_color="transparent")
        wifi_top.grid(row=0, column=0, columnspan=2, padx=10, pady=5, sticky="ew")

        ctk.CTkLabel(wifi_top, text=t("wifi_heading", lg), font=ctk.CTkFont(size=16, weight="bold")).pack(side="left", padx=5)

        self.btn_wifi_card = ctk.CTkButton(wifi_top, text=t("wifi_btn_card", lg), fg_color="#0891b2", hover_color="#0e7490", command=self._dialog_wifi_access_card)
        self.btn_wifi_card.pack(side="right", padx=5)

        self.btn_opt_wifi = ctk.CTkButton(wifi_top, text=t("wifi_btn_opt", lg), fg_color="#d97706", hover_color="#b45309", command=self._optimize_wifi)
        self.btn_opt_wifi.pack(side="right", padx=5)

        self.switch_bsd = ctk.CTkSwitch(wifi_top, text=t("wifi_smart_connect", lg), command=self._on_toggle_bsd)
        self.switch_bsd.pack(side="right", padx=15)

        # Pasek postępu optymalizacji Wi-Fi (ukryty domyślnie)
        self.frame_opt_progress = ctk.CTkFrame(tab, fg_color="#1e293b", corner_radius=8)
        self.lbl_opt_progress = ctk.CTkLabel(
            self.frame_opt_progress,
            text=t("opt_wifi_progress", lg),
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#f59e0b"
        )
        self.lbl_opt_progress.pack(side="top", padx=15, pady=(8, 4))
        self.pbar_opt = ctk.CTkProgressBar(self.frame_opt_progress, orientation="horizontal", mode="indeterminate", width=420)
        self.pbar_opt.pack(side="top", padx=15, pady=(0, 8))

        # 2. Główny obszar przewijany
        self.scroll_wifi = ctk.CTkScrollableFrame(tab, corner_radius=10)
        self.scroll_wifi.grid(row=2, column=0, columnspan=2, padx=10, pady=(0, 10), sticky="nsew")
        self.scroll_wifi.grid_columnconfigure((0, 1), weight=1)

        # Baner informacyjny Smart Connect
        self.frame_bsd_banner = ctk.CTkFrame(self.scroll_wifi, fg_color="#1e293b")
        self.frame_bsd_banner.grid(row=0, column=0, columnspan=2, padx=5, pady=(2, 10), sticky="ew")
        self.lbl_bsd_banner = ctk.CTkLabel(
            self.frame_bsd_banner,
            text=t("wifi_bsd_banner_on", lg),
            text_color="#38bdf8",
            font=ctk.CTkFont(weight="bold")
        )
        self.lbl_bsd_banner.pack(padx=10, pady=8)

        # KARTA WSPÓLNA: Smart Connect Wi-Fi (Pełna szerokość)
        self.card_wifi_combined = ctk.CTkFrame(self.scroll_wifi, corner_radius=10)
        self.card_wifi_combined.grid(row=1, column=0, columnspan=2, padx=5, pady=(0, 10), sticky="ew")

        top_comb = ctk.CTkFrame(self.card_wifi_combined, fg_color="transparent")
        top_comb.pack(fill="x", padx=15, pady=(12, 6))
        ctk.CTkLabel(top_comb, text=("Wspólna sieć Wi-Fi (Smart Connect)" if lg == "pl" else "Combined Wi-Fi Network (Smart Connect)"), font=ctk.CTkFont(size=15, weight="bold")).pack(side="left")

        self.f_ssid_common = ctk.CTkFrame(self.card_wifi_combined, fg_color="transparent")
        self.f_ssid_common.pack(fill="x", padx=15, pady=4)
        ctk.CTkLabel(self.f_ssid_common, text=("Wspólna nazwa (SSID):" if lg == "pl" else "Combined Network Name (SSID):"), font=ctk.CTkFont(weight="bold")).pack(side="left")
        self.entry_wifi_ssid_common = ctk.CTkEntry(self.f_ssid_common, width=280)
        self.entry_wifi_ssid_common.pack(side="right")

        self.f_enc_common = ctk.CTkFrame(self.card_wifi_combined, fg_color="transparent")
        self.f_enc_common.pack(fill="x", padx=15, pady=4)
        ctk.CTkLabel(self.f_enc_common, text=("Wspólne szyfrowanie:" if lg == "pl" else "Combined Security:"), font=ctk.CTkFont(weight="bold")).pack(side="left")
        self.combo_wifi_enc_common = ctk.CTkComboBox(self.f_enc_common, values=get_wifi_enc_options(lg), width=280)
        self.combo_wifi_enc_common.set(code_to_enc("psk2+ccmp", lg))
        self.combo_wifi_enc_common.pack(side="right")

        self.f_pwd_common = ctk.CTkFrame(self.card_wifi_combined, fg_color="transparent")
        self.f_pwd_common.pack(fill="x", padx=15, pady=4)
        ctk.CTkLabel(self.f_pwd_common, text=("Wspólne hasło Wi-Fi:" if lg == "pl" else "Combined Wi-Fi Password:"), font=ctk.CTkFont(weight="bold")).pack(side="left")
        self.entry_wifi_pwd_common = ctk.CTkEntry(self.f_pwd_common, width=280, show="•")
        self.entry_wifi_pwd_common.pack(side="right")

        self.f_show_common = ctk.CTkFrame(self.card_wifi_combined, fg_color="transparent")
        self.f_show_common.pack(fill="x", padx=15, pady=(2, 12))
        self.switch_show_pwd_common = ctk.CTkCheckBox(
            self.f_show_common,
            text=t("wifi_show_pwd", lg),
            command=lambda: self.entry_wifi_pwd_common.configure(show="" if self.switch_show_pwd_common.get() == 1 else "•")
        )
        self.switch_show_pwd_common.pack(side="right")

        # KARTA LEWA: Pasmo 2.4 GHz
        self.card_2g = ctk.CTkFrame(self.scroll_wifi)
        self.card_2g.grid(row=2, column=0, padx=5, pady=5, sticky="nsew")

        self.lbl_title_2g = ctk.CTkLabel(self.card_2g, text=t("wifi_2g_title", lg), font=ctk.CTkFont(size=15, weight="bold"))
        self.lbl_title_2g.pack(anchor="w", padx=15, pady=(15, 8))

        f_on_2g = ctk.CTkFrame(self.card_2g, fg_color="transparent")
        f_on_2g.pack(fill="x", padx=15, pady=3)
        ctk.CTkLabel(f_on_2g, text=t("wifi_2g_radio", lg)).pack(side="left")
        self.switch_wifi_on_2g = ctk.CTkSwitch(f_on_2g, text=t("status_enabled", lg))
        self.switch_wifi_on_2g.select()
        self.switch_wifi_on_2g.pack(side="right")

        self.f_ssid_2g = ctk.CTkFrame(self.card_2g, fg_color="transparent")
        self.f_ssid_2g.pack(fill="x", padx=15, pady=4)
        self.lbl_ssid_2g = ctk.CTkLabel(self.f_ssid_2g, text=t("wifi_ssid", lg))
        self.lbl_ssid_2g.pack(side="left")
        self.entry_wifi_ssid_2g = ctk.CTkEntry(self.f_ssid_2g, width=200)
        self.entry_wifi_ssid_2g.pack(side="right")

        self.f_enc_2g = ctk.CTkFrame(self.card_2g, fg_color="transparent")
        self.f_enc_2g.pack(fill="x", padx=15, pady=4)
        self.lbl_enc_2g = ctk.CTkLabel(self.f_enc_2g, text=t("wifi_enc", lg))
        self.lbl_enc_2g.pack(side="left")
        self.combo_wifi_enc_2g = ctk.CTkComboBox(self.f_enc_2g, values=get_wifi_enc_options(lg), width=220)
        self.combo_wifi_enc_2g.set(code_to_enc("psk2+ccmp", lg))
        self.combo_wifi_enc_2g.pack(side="right")

        self.f_pwd_2g = ctk.CTkFrame(self.card_2g, fg_color="transparent")
        self.f_pwd_2g.pack(fill="x", padx=15, pady=4)
        self.lbl_pwd_2g = ctk.CTkLabel(self.f_pwd_2g, text=t("wifi_pwd", lg))
        self.lbl_pwd_2g.pack(side="left")
        self.entry_wifi_pwd_2g = ctk.CTkEntry(self.f_pwd_2g, width=200, show="•")
        self.entry_wifi_pwd_2g.pack(side="right")

        self.f_show_2g = ctk.CTkFrame(self.card_2g, fg_color="transparent")
        self.f_show_2g.pack(fill="x", padx=15, pady=2)
        self.switch_show_pwd_2g = ctk.CTkCheckBox(self.f_show_2g, text=t("wifi_show_pwd", lg), command=lambda: self._toggle_show_pwd(2))
        self.switch_show_pwd_2g.pack(side="right")

        self.f_tx_2g = ctk.CTkFrame(self.card_2g, fg_color="transparent")
        self.f_tx_2g.pack(fill="x", padx=15, pady=4)
        ctk.CTkLabel(self.f_tx_2g, text=t("wifi_txpwr", lg)).pack(side="left")
        self.combo_wifi_tx_2g = ctk.CTkComboBox(self.f_tx_2g, values=get_wifi_tx_options(lg), width=235)
        self.combo_wifi_tx_2g.set(code_to_tx("max", lg))
        self.combo_wifi_tx_2g.pack(side="right")

        f_ch_2g = ctk.CTkFrame(self.card_2g, fg_color="transparent")
        f_ch_2g.pack(fill="x", padx=15, pady=4)
        ctk.CTkLabel(f_ch_2g, text=t("wifi_channel", lg)).pack(side="left")
        self.combo_wifi_ch_2g = ctk.CTkComboBox(f_ch_2g, values=WIFI_2G_CHANNELS, width=200)
        self.combo_wifi_ch_2g.set("Auto")
        self.combo_wifi_ch_2g.pack(side="right")

        f_bw_2g = ctk.CTkFrame(self.card_2g, fg_color="transparent")
        f_bw_2g.pack(fill="x", padx=15, pady=4)
        ctk.CTkLabel(f_bw_2g, text=t("wifi_bandwidth", lg)).pack(side="left")
        self.combo_wifi_bw_2g = ctk.CTkComboBox(f_bw_2g, values=WIFI_2G_BANDWIDTHS, width=200)
        self.combo_wifi_bw_2g.set("Auto")
        self.combo_wifi_bw_2g.pack(side="right")

        f_hid_2g = ctk.CTkFrame(self.card_2g, fg_color="transparent")
        f_hid_2g.pack(fill="x", padx=15, pady=4)
        ctk.CTkLabel(f_hid_2g, text=t("wifi_hide", lg)).pack(side="left")
        self.switch_wifi_hidden_2g = ctk.CTkSwitch(f_hid_2g, text=t("wifi_hidden_switch_off", lg), command=self._on_toggle_hidden_2g)
        self.switch_wifi_hidden_2g.pack(side="right")

        self.lbl_wifi_status_2g = ctk.CTkLabel(self.card_2g, text=f"{t('wifi_channel', lg)} Auto | {t('wifi_bandwidth', lg)} {t('wifi_width_40', lg)}", text_color="#94a3b8", anchor="w")
        self.lbl_wifi_status_2g.pack(fill="x", padx=15, pady=(6, 12))

        self.btn_save_2g = ctk.CTkButton(self.card_2g, text=t("wifi_btn_save_2g", lg), fg_color="#2563eb", hover_color="#1d4ed8", command=lambda: self._action_save_single_wifi(1))
        self.btn_save_2g.pack(fill="x", padx=15, pady=(5, 15))


        # KARTA PRAWA: Pasmo 5 GHz
        self.card_5g = ctk.CTkFrame(self.scroll_wifi)
        self.card_5g.grid(row=2, column=1, padx=5, pady=5, sticky="nsew")

        self.lbl_title_5g = ctk.CTkLabel(self.card_5g, text=t("wifi_5g_title", lg), font=ctk.CTkFont(size=15, weight="bold"))
        self.lbl_title_5g.pack(anchor="w", padx=15, pady=(15, 8))

        f_on_5g = ctk.CTkFrame(self.card_5g, fg_color="transparent")
        f_on_5g.pack(fill="x", padx=15, pady=3)
        ctk.CTkLabel(f_on_5g, text=t("wifi_5g_radio", lg)).pack(side="left")
        self.switch_wifi_on_5g = ctk.CTkSwitch(f_on_5g, text=t("status_enabled", lg))
        self.switch_wifi_on_5g.select()
        self.switch_wifi_on_5g.pack(side="right")

        self.frame_5g_sync = ctk.CTkFrame(self.card_5g, fg_color="#1e293b", corner_radius=6)
        self.lbl_5g_sync_info = ctk.CTkLabel(
            self.frame_5g_sync,
            text=t("wifi_bsd_info", lg),
            text_color="#38bdf8",
            font=ctk.CTkFont(size=11, weight="bold"),
            justify="left"
        )
        self.lbl_5g_sync_info.pack(padx=12, pady=10)

        self.f_ssid_5g = ctk.CTkFrame(self.card_5g, fg_color="transparent")
        self.f_ssid_5g.pack(fill="x", padx=15, pady=4)
        ctk.CTkLabel(self.f_ssid_5g, text=t("wifi_ssid", lg)).pack(side="left")
        self.entry_wifi_ssid_5g = ctk.CTkEntry(self.f_ssid_5g, width=200)
        self.entry_wifi_ssid_5g.pack(side="right")

        self.f_enc_5g = ctk.CTkFrame(self.card_5g, fg_color="transparent")
        self.f_enc_5g.pack(fill="x", padx=15, pady=4)
        ctk.CTkLabel(self.f_enc_5g, text=t("wifi_enc", lg)).pack(side="left")
        self.combo_wifi_enc_5g = ctk.CTkComboBox(self.f_enc_5g, values=get_wifi_enc_options(lg), width=220)
        self.combo_wifi_enc_5g.set(code_to_enc("psk2+ccmp", lg))
        self.combo_wifi_enc_5g.pack(side="right")

        self.f_pwd_5g = ctk.CTkFrame(self.card_5g, fg_color="transparent")
        self.f_pwd_5g.pack(fill="x", padx=15, pady=4)
        ctk.CTkLabel(self.f_pwd_5g, text=t("wifi_pwd", lg)).pack(side="left")
        self.entry_wifi_pwd_5g = ctk.CTkEntry(self.f_pwd_5g, width=200, show="•")
        self.entry_wifi_pwd_5g.pack(side="right")

        self.f_show_5g = ctk.CTkFrame(self.card_5g, fg_color="transparent")
        self.f_show_5g.pack(fill="x", padx=15, pady=2)
        self.switch_show_pwd_5g = ctk.CTkCheckBox(self.f_show_5g, text=t("wifi_show_pwd", lg), command=lambda: self._toggle_show_pwd(5))
        self.switch_show_pwd_5g.pack(side="right")

        self.f_tx_5g = ctk.CTkFrame(self.card_5g, fg_color="transparent")
        self.f_tx_5g.pack(fill="x", padx=15, pady=4)
        ctk.CTkLabel(self.f_tx_5g, text=t("wifi_txpwr", lg)).pack(side="left")
        self.combo_wifi_tx_5g = ctk.CTkComboBox(self.f_tx_5g, values=get_wifi_tx_options(lg), width=235)
        self.combo_wifi_tx_5g.set(code_to_tx("max", lg))
        self.combo_wifi_tx_5g.pack(side="right")

        f_ch_5g = ctk.CTkFrame(self.card_5g, fg_color="transparent")
        f_ch_5g.pack(fill="x", padx=15, pady=4)
        ctk.CTkLabel(f_ch_5g, text=t("wifi_channel", lg)).pack(side="left")
        self.combo_wifi_ch_5g = ctk.CTkComboBox(f_ch_5g, values=WIFI_5G_CHANNELS, width=200)
        self.combo_wifi_ch_5g.set("Auto")
        self.combo_wifi_ch_5g.pack(side="right")

        f_bw_5g = ctk.CTkFrame(self.card_5g, fg_color="transparent")
        f_bw_5g.pack(fill="x", padx=15, pady=4)
        ctk.CTkLabel(f_bw_5g, text=t("wifi_bandwidth", lg)).pack(side="left")
        self.combo_wifi_bw_5g = ctk.CTkComboBox(f_bw_5g, values=WIFI_5G_BANDWIDTHS, width=250)
        self.combo_wifi_bw_5g.set("Auto")
        self.combo_wifi_bw_5g.pack(side="right")

        f_hid_5g = ctk.CTkFrame(self.card_5g, fg_color="transparent")
        f_hid_5g.pack(fill="x", padx=15, pady=4)
        ctk.CTkLabel(f_hid_5g, text=t("wifi_hide", lg)).pack(side="left")
        self.switch_wifi_hidden_5g = ctk.CTkSwitch(f_hid_5g, text=t("wifi_hidden_switch_off", lg), command=self._on_toggle_hidden_5g)
        self.switch_wifi_hidden_5g.pack(side="right")

        self.lbl_wifi_status_5g = ctk.CTkLabel(self.card_5g, text=f"{t('wifi_channel', lg)} Auto | {t('wifi_bandwidth', lg)} {t('wifi_width_160', lg)}", text_color="#94a3b8", anchor="w")
        self.lbl_wifi_status_5g.pack(fill="x", padx=15, pady=(6, 12))

        self.btn_save_5g = ctk.CTkButton(self.card_5g, text=t("wifi_btn_save_5g", lg), fg_color="#2563eb", hover_color="#1d4ed8", command=lambda: self._action_save_single_wifi(2))
        self.btn_save_5g.pack(fill="x", padx=15, pady=(5, 15))

        # Panel wspólnego zapisu (pod kartami 2.4 GHz i 5 GHz dla Smart Connect)
        self.frame_save_bsd = ctk.CTkFrame(self.scroll_wifi, fg_color="transparent")
        self.frame_save_bsd.grid(row=3, column=0, columnspan=2, padx=5, pady=(6, 10), sticky="ew")

        btn_save_all = ctk.CTkButton(
            self.frame_save_bsd,
            text=("Zapisz ustawienia Wi-Fi" if lg == "pl" else "Save Wi-Fi Settings"),
            fg_color="#16a34a",
            hover_color="#15803d",
            height=36,
            font=ctk.CTkFont(weight="bold"),
            command=self._action_save_all_wifi
        )
        btn_save_all.pack(fill="x")

        # 3. KARTA ZAAWANSOWANYCH USTAWIEŃ WI-FI (Funkcje LuCI / Firmware Xiaomi)
        self.card_adv_wifi = ctk.CTkFrame(self.scroll_wifi, corner_radius=10)
        self.card_adv_wifi.grid(row=4, column=0, columnspan=2, padx=5, pady=(10, 15), sticky="ew")

        ctk.CTkLabel(
            self.card_adv_wifi,
            text=t("wifi_adv_title", lg),
            font=ctk.CTkFont(size=15, weight="bold")
        ).pack(anchor="w", padx=15, pady=(15, 10))

        # 1. Wi-Fi 5 Kompatybilność
        f_adv_w5 = ctk.CTkFrame(self.card_adv_wifi, fg_color="transparent")
        f_adv_w5.pack(fill="x", padx=15, pady=6)
        f_adv_w5_info = ctk.CTkFrame(f_adv_w5, fg_color="transparent")
        f_adv_w5_info.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(f_adv_w5_info, text=t("wifi_adv_w5_title", lg), font=ctk.CTkFont(weight="bold")).pack(anchor="w")
        ctk.CTkLabel(f_adv_w5_info, text=t("wifi_adv_w5_desc", lg), text_color="#94a3b8", font=ctk.CTkFont(size=12)).pack(anchor="w")
        self.switch_wifi5_compat = ctk.CTkSwitch(f_adv_w5, text=t("status_disabled", lg), command=self._action_toggle_wifi5_compat)
        self.switch_wifi5_compat.pack(side="right", padx=5)

        ctk.CTkFrame(self.card_adv_wifi, height=1, fg_color="#334155").pack(fill="x", padx=15, pady=4)

        # 2. TWT
        f_adv_twt = ctk.CTkFrame(self.card_adv_wifi, fg_color="transparent")
        f_adv_twt.pack(fill="x", padx=15, pady=6)
        f_adv_twt_info = ctk.CTkFrame(f_adv_twt, fg_color="transparent")
        f_adv_twt_info.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(f_adv_twt_info, text=t("wifi_adv_twt_title", lg), font=ctk.CTkFont(weight="bold")).pack(anchor="w")
        ctk.CTkLabel(f_adv_twt_info, text=t("wifi_adv_twt_desc", lg), text_color="#94a3b8", font=ctk.CTkFont(size=12)).pack(anchor="w")
        self.switch_twt = ctk.CTkSwitch(f_adv_twt, text=t("status_disabled", lg), command=self._action_toggle_twt)
        self.switch_twt.pack(side="right", padx=5)

        ctk.CTkFrame(self.card_adv_wifi, height=1, fg_color="#334155").pack(fill="x", padx=15, pady=4)

        # 3. MU-MIMO
        f_adv_mimo = ctk.CTkFrame(self.card_adv_wifi, fg_color="transparent")
        f_adv_mimo.pack(fill="x", padx=15, pady=6)
        f_adv_mimo_info = ctk.CTkFrame(f_adv_mimo, fg_color="transparent")
        f_adv_mimo_info.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(f_adv_mimo_info, text=t("wifi_adv_mimo_title", lg), font=ctk.CTkFont(weight="bold")).pack(anchor="w")
        ctk.CTkLabel(f_adv_mimo_info, text=t("wifi_adv_mimo_desc", lg), text_color="#94a3b8", font=ctk.CTkFont(size=12)).pack(anchor="w")
        self.switch_mumimo = ctk.CTkSwitch(f_adv_mimo, text=t("status_disabled", lg), command=self._action_toggle_mumimo)
        self.switch_mumimo.pack(side="right", padx=5)

        ctk.CTkFrame(self.card_adv_wifi, height=1, fg_color="#334155").pack(fill="x", padx=15, pady=4)

        # 4. Szybkie parowanie Xiaomi
        f_adv_ckl = ctk.CTkFrame(self.card_adv_wifi, fg_color="transparent")
        f_adv_ckl.pack(fill="x", padx=15, pady=6)
        f_adv_ckl_info = ctk.CTkFrame(f_adv_ckl, fg_color="transparent")
        f_adv_ckl_info.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(f_adv_ckl_info, text=t("wifi_adv_ckl_title", lg), font=ctk.CTkFont(weight="bold")).pack(anchor="w")
        ctk.CTkLabel(f_adv_ckl_info, text=t("wifi_adv_ckl_desc", lg), text_color="#94a3b8", font=ctk.CTkFont(size=12)).pack(anchor="w")
        self.switch_miotrelay = ctk.CTkSwitch(f_adv_ckl, text=t("status_disabled", lg), command=self._action_toggle_miotrelay)
        self.switch_miotrelay.pack(side="right", padx=5)

        ctk.CTkFrame(self.card_adv_wifi, height=1, fg_color="#334155").pack(fill="x", padx=15, pady=4)

        # 5. Tryb cichy Wi-Fi
        f_adv_silence = ctk.CTkFrame(self.card_adv_wifi, fg_color="transparent")
        f_adv_silence.pack(fill="x", padx=15, pady=6)
        f_adv_silence_info = ctk.CTkFrame(f_adv_silence, fg_color="transparent")
        f_adv_silence_info.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(f_adv_silence_info, text=t("wifi_adv_silence_title", lg), font=ctk.CTkFont(weight="bold")).pack(anchor="w")
        ctk.CTkLabel(f_adv_silence_info, text=t("wifi_adv_silence_desc", lg), text_color="#f87171", font=ctk.CTkFont(size=12)).pack(anchor="w")
        self.switch_wifi_silence = ctk.CTkSwitch(f_adv_silence, text=t("status_disabled", lg), command=self._action_toggle_wifi_silence)
        self.switch_wifi_silence.pack(side="right", padx=5)

        ctk.CTkFrame(self.card_adv_wifi, height=1, fg_color="#334155").pack(fill="x", padx=15, pady=4)

        # 6. Ręczne parametry roamingu Mesh
        f_adv_roam = ctk.CTkFrame(self.card_adv_wifi, fg_color="transparent")
        f_adv_roam.pack(fill="x", padx=15, pady=6)
        f_adv_roam_top = ctk.CTkFrame(f_adv_roam, fg_color="transparent")
        f_adv_roam_top.pack(fill="x")
        f_adv_roam_info = ctk.CTkFrame(f_adv_roam_top, fg_color="transparent")
        f_adv_roam_info.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(f_adv_roam_info, text=t("wifi_adv_roam_title", lg), font=ctk.CTkFont(weight="bold")).pack(anchor="w")
        ctk.CTkLabel(f_adv_roam_info, text=t("wifi_adv_roam_desc", lg), text_color="#94a3b8", font=ctk.CTkFont(size=12)).pack(anchor="w")
        self.switch_roam_manual = ctk.CTkSwitch(f_adv_roam_top, text=t("status_manual_thresholds", lg), command=self._on_toggle_roam_manual)
        self.switch_roam_manual.pack(side="right", padx=5)

        # Pola progów roamingu
        self.frame_roam_fields = ctk.CTkFrame(f_adv_roam, fg_color="#1e293b", corner_radius=8)
        self.frame_roam_fields.pack(fill="x", pady=(8, 2))

        f_rf1 = ctk.CTkFrame(self.frame_roam_fields, fg_color="transparent")
        f_rf1.pack(side="left", padx=15, pady=8)
        ctk.CTkLabel(f_rf1, text=t("wifi_adv_roam_2g", lg)).pack(side="left", padx=5)
        self.entry_roam_2g = ctk.CTkEntry(f_rf1, width=70)
        self.entry_roam_2g.insert(0, "-65")
        self.entry_roam_2g.pack(side="left")

        f_rf2 = ctk.CTkFrame(self.frame_roam_fields, fg_color="transparent")
        f_rf2.pack(side="left", padx=15, pady=8)
        ctk.CTkLabel(f_rf2, text=t("wifi_adv_roam_5g", lg)).pack(side="left", padx=5)
        self.entry_roam_5g = ctk.CTkEntry(f_rf2, width=70)
        self.entry_roam_5g.insert(0, "-70")
        self.entry_roam_5g.pack(side="left")

        self.btn_save_roam = ctk.CTkButton(self.frame_roam_fields, text=t("wifi_adv_roam_btn_save", lg), fg_color="#2563eb", hover_color="#1d4ed8", width=160, command=self._action_save_roaming)
        self.btn_save_roam.pack(side="right", padx=15, pady=8)

        ctk.CTkFrame(self.card_adv_wifi, height=1, fg_color="#334155").pack(fill="x", padx=15, pady=6)

        # 7. Globalna Moc Nadawania Radia Wi-Fi (Tx Power)
        f_adv_txpwr = ctk.CTkFrame(self.card_adv_wifi, fg_color="transparent")
        f_adv_txpwr.pack(fill="x", padx=15, pady=(6, 15))
        f_txpwr_info = ctk.CTkFrame(f_adv_txpwr, fg_color="transparent")
        f_txpwr_info.pack(side="left", fill="x", expand=True)
        ctk.CTkLabel(f_txpwr_info, text=t("wifi_global_txpwr_title", lg), font=ctk.CTkFont(weight="bold")).pack(anchor="w")
        ctk.CTkLabel(f_txpwr_info, text=t("wifi_global_txpwr_desc", lg), text_color="#94a3b8", font=ctk.CTkFont(size=12)).pack(anchor="w")

        f_txpwr_ctrl = ctk.CTkFrame(f_adv_txpwr, fg_color="transparent")
        f_txpwr_ctrl.pack(side="right", padx=5)
        self.combo_txpwr = ctk.CTkComboBox(f_txpwr_ctrl, values=get_wifi_tx_options(lg), width=200)
        self.combo_txpwr.set(code_to_tx("max", lg))
        self.combo_txpwr.pack(side="left", padx=5)
        self.btn_save_txpwr = ctk.CTkButton(f_txpwr_ctrl, text=t("btn_apply", lg), fg_color="#2563eb", hover_color="#1d4ed8", width=110, command=self._action_save_txpwr)
        self.btn_save_txpwr.pack(side="left", padx=5)

    def _action_save_txpwr(self):
        val = self.combo_txpwr.get()
        tx = tx_to_code(val)
        def run():
            res = self.client.set_wifi_txpwr(tx)
            if res.get("code") == 0 or not res.get("error"):
                self.after(0, lambda: messagebox.showinfo(
                    "Success" if self.current_lang == "en" else "Sukces",
                    f"Wi-Fi TX power updated to: {val}" if self.current_lang == "en" else f"Moc nadawania Wi-Fi została ustawiona na: {val}."
                ))
            else:
                self.after(0, lambda: messagebox.showerror(
                    "Error" if self.current_lang == "en" else "Błąd",
                    f"Failed to set Wi-Fi power: {res.get('error') or res}" if self.current_lang == "en" else f"Nie udało się ustawić mocy Wi-Fi: {res.get('error') or res}"
                ))
        threading.Thread(target=run, daemon=True).start()

    def _toggle_show_pwd(self, band):
        if band == 2:
            show_char = "" if self.switch_show_pwd_2g.get() == 1 else "•"
            self.entry_wifi_pwd_2g.configure(show=show_char)
        else:
            show_char = "" if self.switch_show_pwd_5g.get() == 1 else "•"
            self.entry_wifi_pwd_5g.configure(show=show_char)

    def _update_smartconnect_layout(self, is_on: bool):
        lg = self.current_lang
        if is_on:
            self.lbl_bsd_banner.configure(text=t("wifi_bsd_banner_on", lg))
            if hasattr(self, "card_wifi_combined"):
                self.card_wifi_combined.grid(row=1, column=0, columnspan=2, padx=5, pady=(0, 10), sticky="ew")

            self.lbl_title_2g.configure(text=("📊 Parametry radiowe 2.4 GHz" if lg == "pl" else "📊 2.4 GHz Radio Parameters"))
            self.lbl_title_5g.configure(text=("🚀 Parametry radiowe 5 GHz" if lg == "pl" else "🚀 5 GHz Radio Parameters"))

            if hasattr(self, "f_ssid_2g"):
                self.f_ssid_2g.pack_forget()
                self.f_enc_2g.pack_forget()
                self.f_pwd_2g.pack_forget()
                self.f_show_2g.pack_forget()
                self.btn_save_2g.pack_forget()

            if hasattr(self, "f_ssid_5g"):
                self.f_ssid_5g.pack_forget()
                self.f_enc_5g.pack_forget()
                self.f_pwd_5g.pack_forget()
                self.f_show_5g.pack_forget()
                self.btn_save_5g.pack_forget()

            if hasattr(self, "frame_5g_sync") and hasattr(self, "f_tx_5g"):
                self.frame_5g_sync.pack(fill="x", padx=15, pady=(5, 10), before=self.f_tx_5g)
            if hasattr(self, "frame_save_bsd"):
                self.frame_save_bsd.grid(row=3, column=0, columnspan=2, padx=5, pady=(6, 10), sticky="ew")
        else:
            self.lbl_bsd_banner.configure(text=t("wifi_bsd_banner_off", lg))
            if hasattr(self, "card_wifi_combined"):
                self.card_wifi_combined.grid_remove()

            self.lbl_title_2g.configure(text=t("wifi_2g_title", lg))
            self.lbl_title_5g.configure(text=t("wifi_5g_title", lg))

            if hasattr(self, "f_ssid_2g") and hasattr(self, "f_tx_2g"):
                self.f_ssid_2g.pack(fill="x", padx=15, pady=4, before=self.f_tx_2g)
                self.f_enc_2g.pack(fill="x", padx=15, pady=4, before=self.f_tx_2g)
                self.f_pwd_2g.pack(fill="x", padx=15, pady=4, before=self.f_tx_2g)
                self.f_show_2g.pack(fill="x", padx=15, pady=2, before=self.f_tx_2g)
                self.btn_save_2g.pack(fill="x", padx=15, pady=(5, 15))

            if hasattr(self, "frame_5g_sync"):
                self.frame_5g_sync.pack_forget()
            if hasattr(self, "f_ssid_5g") and hasattr(self, "f_tx_5g"):
                self.f_ssid_5g.pack(fill="x", padx=15, pady=4, before=self.f_tx_5g)
                self.f_enc_5g.pack(fill="x", padx=15, pady=4, before=self.f_tx_5g)
                self.f_pwd_5g.pack(fill="x", padx=15, pady=4, before=self.f_tx_5g)
                self.f_show_5g.pack(fill="x", padx=15, pady=2, before=self.f_tx_5g)
                self.btn_save_5g.pack(fill="x", padx=15, pady=(5, 15))
            if hasattr(self, "frame_save_bsd"):
                self.frame_save_bsd.grid_forget()

    def _on_toggle_bsd(self):
        is_on = self.switch_bsd.get() == 1
        self._update_smartconnect_layout(is_on)
        if is_on:
            ssid_2g = self.entry_wifi_ssid_2g.get().strip()
            pwd_2g = self.entry_wifi_pwd_2g.get().strip()
            enc_2g = self.combo_wifi_enc_2g.get()
            if hasattr(self, "entry_wifi_ssid_common"):
                if not self.entry_wifi_ssid_common.get().strip() and ssid_2g:
                    self.entry_wifi_ssid_common.delete(0, "end")
                    self.entry_wifi_ssid_common.insert(0, ssid_2g)
            if hasattr(self, "entry_wifi_pwd_common"):
                if not self.entry_wifi_pwd_common.get().strip() and pwd_2g:
                    self.entry_wifi_pwd_common.delete(0, "end")
                    self.entry_wifi_pwd_common.insert(0, pwd_2g)
            if hasattr(self, "combo_wifi_enc_common") and enc_2g:
                self.combo_wifi_enc_common.set(enc_2g)

    def _action_save_single_wifi(self, wifi_idx: int):
        if not self.client.connected:
            return

        if wifi_idx == 1:
            band_name = "2.4 GHz"
            ssid = self.entry_wifi_ssid_2g.get().strip()
            pwd = self.entry_wifi_pwd_2g.get().strip()
            enc_display = self.combo_wifi_enc_2g.get()
            tx_display = self.combo_wifi_tx_2g.get()
            hidden = 1 if self.switch_wifi_hidden_2g.get() == 1 else 0
            is_on = 1 if self.switch_wifi_on_2g.get() == 1 else 0
            channel = channel_to_code(self.combo_wifi_ch_2g.get())
            bandwidth = bandwidth_to_code(self.combo_wifi_bw_2g.get())
        else:
            band_name = "5 GHz"
            ssid = self.entry_wifi_ssid_5g.get().strip()
            pwd = self.entry_wifi_pwd_5g.get().strip()
            enc_display = self.combo_wifi_enc_5g.get()
            tx_display = self.combo_wifi_tx_5g.get()
            hidden = 1 if self.switch_wifi_hidden_5g.get() == 1 else 0
            is_on = 1 if self.switch_wifi_on_5g.get() == 1 else 0
            channel = channel_to_code(self.combo_wifi_ch_5g.get())
            bandwidth = bandwidth_to_code(self.combo_wifi_bw_5g.get())

        enc_code = enc_to_code(enc_display)
        tx_code = WIFI_TX_MAP_CODE.get(tx_display, "max")
        lg = self.current_lang
        if enc_code in ("ccmp", "sae"):
            if not messagebox.askyesno(t("warn_title", lg), t("wifi_enc_warn_wpa3", lg)):
                return

        if not ssid:
            messagebox.showerror("Błąd", f"Podaj nazwę sieci (SSID) dla pasma {band_name}.")
            return

        if enc_code != "none" and len(pwd) < 8:
            messagebox.showerror("Błąd hasła", "Dla zabezpieczeń WPA2 / WPA3 hasło musi mieć co najmniej 8 znaków.")
            return

        bw_band = "5g" if wifi_idx == 2 else "2g"
        msg_confirm = (
            f"Czy na pewno chcesz zapisać nowe parametry dla pasma {band_name}?\n\n"
            f"- SSID: {ssid}\n"
            f"- Szyfrowanie: {enc_display}\n"
            f"- Kanał: {code_to_channel(channel)}\n"
            f"- Szerokość: {code_to_bandwidth(bandwidth, bw_band)}\n"
            f"- Moc nadawania: {tx_display}\n"
            f"- Ukryte SSID: {'Tak' if hidden else 'Nie'}\n\n"
            f"UWAGA: Zmiana parametrów rozłączy urządzenia bezprzewodowe na około 10-15 sekund!"
        )

        if not messagebox.askyesno(f"Zapis Wi-Fi ({band_name})", msg_confirm):
            return

        def run():
            try:
                res = self.client.set_wifi(
                    wifi_idx=wifi_idx,
                    ssid=ssid,
                    password=pwd,
                    encryption=enc_code,
                    hidden=hidden,
                    txpwr=tx_code,
                    on=is_on,
                    channel=channel,
                    bandwidth=bandwidth
                )
                if res.get("code") == 0:
                    messagebox.showinfo("Sukces", f"Pomyślnie zaktualizowano parametry pasma {band_name}!")
                    time.sleep(2)
                    self._fetch_data_thread()
                else:
                    messagebox.showwarning("Uwaga", f"Odpowiedź routera: {res}")
            except Exception as e:
                messagebox.showerror("Błąd", f"Błąd zapisu Wi-Fi: {e}")
        threading.Thread(target=run, daemon=True).start()

    def _action_save_all_wifi(self):
        if not self.client.connected:
            return

        bsd = 1 if self.switch_bsd.get() == 1 else 0

        ssid_2g = self.entry_wifi_ssid_2g.get().strip()
        pwd_2g = self.entry_wifi_pwd_2g.get().strip()
        enc_2g = enc_to_code(self.combo_wifi_enc_2g.get())
        tx_2g = WIFI_TX_MAP_CODE.get(self.combo_wifi_tx_2g.get(), "max")
        hid_2g = 1 if self.switch_wifi_hidden_2g.get() == 1 else 0
        on_2g = 1 if self.switch_wifi_on_2g.get() == 1 else 0
        ch_2g = channel_to_code(self.combo_wifi_ch_2g.get())
        bw_2g = bandwidth_to_code(self.combo_wifi_bw_2g.get())

        ch_5g = channel_to_code(self.combo_wifi_ch_5g.get())
        bw_5g = bandwidth_to_code(self.combo_wifi_bw_5g.get())

        if bsd == 1:
            if hasattr(self, "entry_wifi_ssid_common") and self.entry_wifi_ssid_common.get().strip():
                ssid_common = self.entry_wifi_ssid_common.get().strip()
                pwd_common = self.entry_wifi_pwd_common.get().strip()
                enc_common = enc_to_code(self.combo_wifi_enc_common.get())
            else:
                ssid_common = ssid_2g
                pwd_common = pwd_2g
                enc_common = enc_2g
            ssid_2g = ssid_common
            pwd_2g = pwd_common
            enc_2g = enc_common
            ssid_5g = ssid_common
            pwd_5g = pwd_common
            enc_5g = enc_common
            tx_5g = WIFI_TX_MAP_CODE.get(self.combo_wifi_tx_5g.get(), "max")
            hid_5g = 1 if self.switch_wifi_hidden_5g.get() == 1 else 0
            on_5g = 1 if self.switch_wifi_on_5g.get() == 1 else 0
        else:
            ssid_5g = self.entry_wifi_ssid_5g.get().strip()
            pwd_5g = self.entry_wifi_pwd_5g.get().strip()
            enc_5g = enc_to_code(self.combo_wifi_enc_5g.get())
            tx_5g = WIFI_TX_MAP_CODE.get(self.combo_wifi_tx_5g.get(), "max")
            hid_5g = 1 if self.switch_wifi_hidden_5g.get() == 1 else 0
            on_5g = 1 if self.switch_wifi_on_5g.get() == 1 else 0

        lg = self.current_lang
        if enc_2g in ("ccmp", "sae") or (bsd == 0 and enc_5g in ("ccmp", "sae")):
            if not messagebox.askyesno(t("warn_title", lg), t("wifi_enc_warn_wpa3", lg)):
                return

        if not ssid_2g or (bsd == 0 and not ssid_5g):
            messagebox.showerror(t("err_title", lg), "Wprowadź nazwę sieci (SSID)." if lg == "pl" else "Please enter network name (SSID).")
            return

        if enc_2g != "none" and len(pwd_2g) < 8:
            messagebox.showerror("Błąd hasła", "Hasło Wi-Fi 2.4 GHz musi mieć co najmniej 8 znaków.")
            return
        if enc_5g != "none" and len(pwd_5g) < 8:
            messagebox.showerror("Błąd hasła", "Hasło Wi-Fi 5 GHz musi mieć co najmniej 8 znaków.")
            return

        msg_confirm = (
            f"Czy na pewno chcesz zapisać globalną konfigurację Wi-Fi?\n\n"
            f"- Smart Connect (BSD): {'WŁĄCZONY (Wspólne SSID)' if bsd else 'WYŁĄCZONY (Osobne pasma)'}\n"
            f"- 2.4 GHz: '{ssid_2g}' (Kanał: {code_to_channel(ch_2g)}, Szerokość: {code_to_bandwidth(bw_2g, '2g')})\n"
            f"- 5 GHz: '{ssid_5g}' (Kanał: {code_to_channel(ch_5g)}, Szerokość: {code_to_bandwidth(bw_5g, '5g')})\n\n"
            f"UWAGA: Zmiana parametrów rozłączy urządzenia bezprzewodowe na około 10-15 sekund!"
        )

        if not messagebox.askyesno("Globalna Konfiguracja Wi-Fi", msg_confirm):
            return

        wifi1 = {
            "on": on_2g,
            "ssid": ssid_2g,
            "pwd": pwd_2g,
            "encryption": enc_2g,
            "txpwr": tx_2g,
            "hidden": hid_2g,
            "channel": ch_2g,
            "bandwidth": bw_2g
        }
        wifi2 = {
            "on": on_5g,
            "ssid": ssid_5g,
            "pwd": pwd_5g,
            "encryption": enc_5g,
            "txpwr": tx_5g,
            "hidden": hid_5g,
            "channel": ch_5g,
            "bandwidth": bw_5g
        }

        def run():
            try:
                res = self.client.set_all_wifi(bsd, wifi1, wifi2)
                if res.get("code") == 0:
                    messagebox.showinfo("Sukces", "Pomyślnie zaktualizowano konfigurację Wi-Fi w routerze!")
                    time.sleep(2)
                    self._fetch_data_thread()
                else:
                    messagebox.showwarning("Uwaga", f"Odpowiedź routera: {res}")
            except Exception as e:
                messagebox.showerror("Błąd", f"Błąd zapisu Wi-Fi: {e}")
        threading.Thread(target=run, daemon=True).start()

    # --- Obsługa zaawansowanych przełączników Wi-Fi ---

    def _action_toggle_wifi5_compat(self):
        if not self.client.connected:
            return
        lg = self.current_lang
        is_compat = self.switch_wifi5_compat.get() == 1
        self.switch_wifi5_compat.configure(text=t("status_enabled" if is_compat else "status_disabled", lg))
        ax = 0 if is_compat else 1

        def run():
            try:
                res = self.client.set_wifi_ax(ax)
                if res.get("code") == 0:
                    status_txt = "WŁĄCZONY (Wi-Fi 6 wyłączone)" if is_compat else "WYŁĄCZONY (Wi-Fi 6 aktywne)"
                    messagebox.showinfo("Wi-Fi 5 Kompatybilność", f"Tryb zgodności z Wi-Fi 5 został: {status_txt}")
                else:
                    messagebox.showwarning("Uwaga", f"Odpowiedź routera: {res}")
            except Exception as e:
                messagebox.showerror("Błąd", f"Błąd przełączania trybu Wi-Fi 5: {e}")
        threading.Thread(target=run, daemon=True).start()

    def _action_toggle_twt(self):
        if not self.client.connected:
            return
        lg = self.current_lang
        status = 1 if self.switch_twt.get() == 1 else 0
        self.switch_twt.configure(text=t("status_enabled" if status == 1 else "status_disabled", lg))

        def run():
            try:
                res = self.client.set_twt(status)
                if res.get("code") == 0:
                    txt = "WŁĄCZONY" if status == 1 else "WYŁĄCZONY"
                    messagebox.showinfo("Tryb TWT", f"Tryb oszczędzania energii TWT został: {txt}")
                else:
                    messagebox.showwarning("Uwaga", f"Odpowiedź routera: {res}")
            except Exception as e:
                messagebox.showerror("Błąd", f"Błąd przełączania trybu TWT: {e}")
        threading.Thread(target=run, daemon=True).start()

    def _action_toggle_mumimo(self):
        if not self.client.connected:
            return
        lg = self.current_lang
        txbf = 1 if self.switch_mumimo.get() == 1 else 0
        self.switch_mumimo.configure(text=t("status_enabled" if txbf == 1 else "status_disabled", lg))

        def run():
            try:
                res = self.client.set_wifi_txbf(txbf)
                if res.get("code") == 0:
                    txt = "WŁĄCZONE" if txbf == 1 else "WYŁĄCZONE"
                    messagebox.showinfo("MU-MIMO", f"MU-MIMO / Beamforming zostało: {txt}")
                else:
                    messagebox.showwarning("Uwaga", f"Odpowiedź routera: {res}")
            except Exception as e:
                messagebox.showerror("Błąd", f"Błąd przełączania MU-MIMO: {e}")
        threading.Thread(target=run, daemon=True).start()

    def _action_toggle_miotrelay(self):
        if not self.client.connected:
            return
        lg = self.current_lang
        switch_on = 1 if self.switch_miotrelay.get() == 1 else 0
        self.switch_miotrelay.configure(text=t("status_enabled" if switch_on == 1 else "status_disabled", lg))

        def run():
            try:
                res = self.client.set_miotrelay_switch(switch_on)
                if res.get("code") == 0:
                    txt = "WŁĄCZONE" if switch_on == 1 else "WYŁĄCZONE"
                    messagebox.showinfo("Szybkie parowanie Xiaomi", f"Szybkie parowanie Xiaomi (Changkuailian) zostało: {txt}")
                else:
                    messagebox.showwarning("Uwaga", f"Odpowiedź routera: {res}")
            except Exception as e:
                messagebox.showerror("Błąd", f"Błąd przełączania szybkiego parowania: {e}")
        threading.Thread(target=run, daemon=True).start()

    def _action_toggle_wifi_silence(self):
        if not self.client.connected:
            return
        lg = self.current_lang
        is_silence = self.switch_wifi_silence.get() == 1
        if is_silence:
            confirm = messagebox.askyesno(
                "Tryb cichy Wi-Fi (Ostrzeżenie)",
                "UWAGA: Włączenie trybu cichego natychmiast wyłączy WSZYSTKIE moduły radiowe Wi-Fi routera.\n"
                "Urządzenia bezprzewodowe stracą połączenie. Tryb wyłączy się automatycznie po fizycznym restarcie routera.\n\n"
                "Czy na pewno chcesz włączyć tryb cichy Wi-Fi?"
            )
            if not confirm:
                self.switch_wifi_silence.deselect()
                self.switch_wifi_silence.configure(text=t("status_disabled", lg))
                return

        self.switch_wifi_silence.configure(text=t("status_enabled" if is_silence else "status_disabled", lg))
        status = 1 if is_silence else 0

        def run():
            try:
                res = self.client.set_wifi_silence(status)
                if res.get("code") == 0:
                    txt = "WŁĄCZONY (Wi-Fi wyłączone do restartu)" if status == 1 else "WYŁĄCZONY"
                    messagebox.showinfo("Tryb cichy Wi-Fi", f"Tryb cichy routera został: {txt}")
                else:
                    messagebox.showwarning("Uwaga", f"Odpowiedź routera: {res}")
            except Exception as e:
                messagebox.showerror("Błąd", f"Błąd zmiany trybu cichego: {e}")
        threading.Thread(target=run, daemon=True).start()

    def _on_toggle_roam_manual(self):
        if not self.client.connected:
            return
        lg = self.current_lang
        is_manual = self.switch_roam_manual.get() == 1
        self.switch_roam_manual.configure(text=t("wifi_adv_roam_manual", lg) if is_manual else t("status_disabled", lg))
        if not is_manual:
            def run():
                try:
                    res = self.client.set_aimesh_config(0)
                    if res.get("code") == 0:
                        messagebox.showinfo("Roaming Mesh", "Ręczne progi roamingu zostały wyłączone (tryb automatyczny).")
                    else:
                        messagebox.showwarning("Uwaga", f"Odpowiedź routera: {res}")
                except Exception as e:
                    messagebox.showerror("Błąd", f"Błąd zapisu parametrów roamingu: {e}")
            threading.Thread(target=run, daemon=True).start()

    def _action_save_roaming(self):
        if not self.client.connected:
            return
        try:
            val_2g = int(self.entry_roam_2g.get().strip())
            val_5g = int(self.entry_roam_5g.get().strip())
            if not (-85 <= val_2g <= -45) or not (-85 <= val_5g <= -45):
                messagebox.showerror("Błąd", "Progi RSSI muszą mieścić się w zakresie od -85 do -45 dBm.")
                return
        except ValueError:
            messagebox.showerror("Błąd", "Wprowadź prawidłowe liczby całkowite dla progów RSSI (np. -65, -70).")
            return

        def run():
            try:
                res = self.client.set_aimesh_config(1, val_2g, val_5g)
                if res.get("code") == 0:
                    self.switch_roam_manual.select()
                    messagebox.showinfo("Roaming Mesh", f"Zapisano progi roamingu: 2.4G={val_2g} dBm, 5G={val_5g} dBm!")
                else:
                    messagebox.showwarning("Uwaga", f"Odpowiedź routera: {res}")
            except Exception as e:
                messagebox.showerror("Błąd", f"Błąd zapisu roamingu Mesh: {e}")
        threading.Thread(target=run, daemon=True).start()

    def _on_toggle_hidden_2g(self):
        is_h = self.switch_wifi_hidden_2g.get() == 1
        lg = self.current_lang
        self.switch_wifi_hidden_2g.configure(text=t("wifi_hidden_switch_on" if is_h else "wifi_hidden_switch_off", lg))

    def _on_toggle_hidden_5g(self):
        is_h = self.switch_wifi_hidden_5g.get() == 1
        lg = self.current_lang
        self.switch_wifi_hidden_5g.configure(text=t("wifi_hidden_switch_on" if is_h else "wifi_hidden_switch_off", lg))

    def _dialog_wifi_access_card(self):
        lg = self.current_lang
        bsd = 1 if hasattr(self, "switch_bsd") and self.switch_bsd.get() == 1 else 0

        dialog = ctk.CTkToplevel(self)
        dialog.title(t("wcard_dlg_title", lg))
        dialog.geometry("520x460")
        dialog.resizable(False, False)
        dialog.grab_set()

        ctk.CTkLabel(dialog, text=t("wcard_dlg_heading", lg), font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(20, 10))

        card = ctk.CTkFrame(dialog, corner_radius=10)
        card.pack(fill="both", expand=True, padx=20, pady=10)

        ssid_2g = self.entry_wifi_ssid_2g.get().strip() if hasattr(self, "entry_wifi_ssid_2g") else "MyWiFi"
        pwd_2g = self.entry_wifi_pwd_2g.get().strip() if hasattr(self, "entry_wifi_pwd_2g") else ""
        enc_2g = self.combo_wifi_enc_2g.get() if hasattr(self, "combo_wifi_enc_2g") else "WPA2/WPA3 Personal"

        ssid_5g = self.entry_wifi_ssid_5g.get().strip() if hasattr(self, "entry_wifi_ssid_5g") else "MyWiFi"
        pwd_5g = self.entry_wifi_pwd_5g.get().strip() if hasattr(self, "entry_wifi_pwd_5g") else ""

        no_pwd_str = t("wcard_no_pwd", lg)
        sec_lbl = t("wcard_security", lg)
        pwd_lbl = t("wcard_password", lg)

        if bsd == 1:
            ctk.CTkLabel(card, text=t("wcard_home_smart", lg), font=ctk.CTkFont(size=14, weight="bold"), text_color="#38bdf8").pack(anchor="w", padx=20, pady=(15, 2))
            ctk.CTkLabel(card, text=f"SSID: {ssid_2g}", font=ctk.CTkFont(size=16, weight="bold")).pack(anchor="w", padx=20, pady=2)
            ctk.CTkLabel(card, text=f"{sec_lbl} {enc_2g}", text_color="#94a3b8").pack(anchor="w", padx=20, pady=2)
            ctk.CTkLabel(card, text=f"{pwd_lbl} {pwd_2g or no_pwd_str}", font=ctk.CTkFont(size=15, weight="bold"), text_color="#22c55e").pack(anchor="w", padx=20, pady=(6, 10))

            qr_str = f"WIFI:T:WPA;S:{ssid_2g};P:{pwd_2g};;"
        else:
            ctk.CTkLabel(card, text=t("wcard_band_2g", lg), font=ctk.CTkFont(size=14, weight="bold"), text_color="#10b981").pack(anchor="w", padx=20, pady=(10, 2))
            ctk.CTkLabel(card, text=f"SSID: {ssid_2g} | {pwd_lbl} {pwd_2g or no_pwd_str}").pack(anchor="w", padx=20, pady=1)

            ctk.CTkLabel(card, text=t("wcard_band_5g", lg), font=ctk.CTkFont(size=14, weight="bold"), text_color="#8b5cf6").pack(anchor="w", padx=20, pady=(10, 2))
            ctk.CTkLabel(card, text=f"SSID: {ssid_5g} | {pwd_lbl} {pwd_5g or no_pwd_str}").pack(anchor="w", padx=20, pady=1)

            qr_str = f"WIFI:T:WPA;S:{ssid_5g};P:{pwd_5g};;"

        # Format QR String
        ctk.CTkLabel(card, text=t("wcard_qr_heading", lg), font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", padx=20, pady=(15, 2))
        ent_qr = ctk.CTkEntry(card, width=440)
        ent_qr.insert(0, qr_str)
        ent_qr.pack(padx=20, pady=4)

        def copy_pwd():
            self.clipboard_clear()
            self.clipboard_append(pwd_2g or pwd_5g)
            messagebox.showinfo(t("succ_title", lg), t("status_copied", lg), parent=dialog)

        def copy_qr():
            self.clipboard_clear()
            self.clipboard_append(qr_str)
            messagebox.showinfo(t("succ_title", lg), t("status_copied", lg), parent=dialog)

        btn_box = ctk.CTkFrame(dialog, fg_color="transparent")
        btn_box.pack(fill="x", padx=20, pady=(5, 15))

        ctk.CTkButton(btn_box, text=t("wcard_copy_pwd", lg), fg_color="#2563eb", width=140, command=copy_pwd).pack(side="left", padx=5)
        ctk.CTkButton(btn_box, text=t("wcard_copy_qr", lg), fg_color="#0891b2", width=140, command=copy_qr).pack(side="left", padx=5)
        ctk.CTkButton(btn_box, text=t("btn_close", lg), fg_color="#475569", width=110, command=dialog.destroy).pack(side="right", padx=5)


    # =========================================================================
    # ZAKŁADKA 6: PORTY I NAT (PORT FORWARDING, RANGE, DMZ, UPNP)
    # =========================================================================

    def _build_nat_tab(self):
        lg = self.current_lang
        tab = self.tab_nat
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(0, weight=1)

        self.scroll_nat = ctk.CTkScrollableFrame(tab)
        self.scroll_nat.pack(fill="both", expand=True, padx=5, pady=5)
        self.scroll_nat.grid_columnconfigure((0, 1), weight=1)

        # KARTA 1: Przekierowanie pojedynczych portów (Pełna szerokość)
        self.card_nat_single = ctk.CTkFrame(self.scroll_nat)
        self.card_nat_single.grid(row=0, column=0, columnspan=2, padx=5, pady=5, sticky="nsew")

        top_s = ctk.CTkFrame(self.card_nat_single, fg_color="transparent")
        top_s.pack(fill="x", padx=15, pady=(15, 8))
        ctk.CTkLabel(top_s, text=t("nat_single_title", lg), font=ctk.CTkFont(size=15, weight="bold")).pack(side="left")
        self.lbl_count_nat_single = ctk.CTkLabel(top_s, text=f"{t('nat_count_active', lg)} 0", font=ctk.CTkFont(size=12), text_color="#94a3b8")
        self.lbl_count_nat_single.pack(side="left", padx=10)
        ctk.CTkButton(top_s, text=t("nat_btn_add_single", lg), fg_color="#2563eb", hover_color="#1d4ed8", width=160, command=lambda: self._dialog_port_forward(None)).pack(side="right")

        self.nat_single_list_frame = ctk.CTkFrame(self.card_nat_single, fg_color="transparent")
        self.nat_single_list_frame.pack(fill="both", expand=True, padx=15, pady=(5, 15))

        # KARTA 2: Przekierowanie zakresów portów (Pełna szerokość)
        self.card_nat_range = ctk.CTkFrame(self.scroll_nat)
        self.card_nat_range.grid(row=1, column=0, columnspan=2, padx=5, pady=5, sticky="nsew")

        top_r = ctk.CTkFrame(self.card_nat_range, fg_color="transparent")
        top_r.pack(fill="x", padx=15, pady=(15, 8))
        ctk.CTkLabel(top_r, text=t("nat_range_title", lg), font=ctk.CTkFont(size=15, weight="bold")).pack(side="left")
        self.lbl_count_nat_range = ctk.CTkLabel(top_r, text=f"{t('nat_count_active', lg)} 0", font=ctk.CTkFont(size=12), text_color="#94a3b8")
        self.lbl_count_nat_range.pack(side="left", padx=10)
        ctk.CTkButton(top_r, text=t("nat_btn_add_range", lg), fg_color="#2563eb", hover_color="#1d4ed8", width=160, command=lambda: self._dialog_range_forward(None)).pack(side="right")

        self.nat_range_list_frame = ctk.CTkFrame(self.card_nat_range, fg_color="transparent")
        self.nat_range_list_frame.pack(fill="both", expand=True, padx=15, pady=(5, 15))

        # KARTA 3: Strefa DMZ (Demilitarized Zone)
        self.card_nat_dmz = ctk.CTkFrame(self.scroll_nat)
        self.card_nat_dmz.grid(row=2, column=0, padx=5, pady=5, sticky="nsew")

        ctk.CTkLabel(self.card_nat_dmz, text=t("nat_card_dmz", lg), font=ctk.CTkFont(size=15, weight="bold")).pack(anchor="w", padx=15, pady=(15, 6))
        ctk.CTkLabel(
            self.card_nat_dmz,
            text=t("nat_desc_dmz", lg),
            text_color="#94a3b8",
            wraplength=480,
            justify="left"
        ).pack(anchor="w", padx=15, pady=(0, 10))

        self.lbl_dmz_collision = ctk.CTkLabel(
            self.card_nat_dmz,
            text="",
            text_color="#eab308",
            wraplength=480,
            justify="left",
            font=ctk.CTkFont(weight="bold")
        )
        self.lbl_dmz_collision.pack(anchor="w", padx=15, pady=(0, 8))

        f_dmz_sw = ctk.CTkFrame(self.card_nat_dmz, fg_color="transparent")
        f_dmz_sw.pack(fill="x", padx=15, pady=6)
        ctk.CTkLabel(f_dmz_sw, text=t("nat_lbl_dmz_state", lg)).pack(side="left")
        self.switch_dmz = ctk.CTkSwitch(f_dmz_sw, text=t("status_enabled", lg))
        self.switch_dmz.pack(side="right")

        f_dmz_ip = ctk.CTkFrame(self.card_nat_dmz, fg_color="transparent")
        f_dmz_ip.pack(fill="x", padx=15, pady=6)
        ctk.CTkLabel(f_dmz_ip, text=t("nat_lbl_dmz_ip", lg)).pack(side="left")
        self.entry_dmz_ip = ctk.CTkEntry(f_dmz_ip, width=180, placeholder_text="np. 192.168.31.200")
        self.entry_dmz_ip.pack(side="right")

        self.btn_save_dmz = ctk.CTkButton(self.card_nat_dmz, text=t("nat_btn_save_dmz", lg), fg_color="#2563eb", hover_color="#1d4ed8", command=self._action_save_dmz)
        self.btn_save_dmz.pack(fill="x", padx=15, pady=(10, 15))

        # KARTA 4: Universal Plug and Play (UPnP)
        self.card_nat_upnp = ctk.CTkFrame(self.scroll_nat)
        self.card_nat_upnp.grid(row=2, column=1, padx=5, pady=5, sticky="nsew")

        top_u = ctk.CTkFrame(self.card_nat_upnp, fg_color="transparent")
        top_u.pack(fill="x", padx=15, pady=(15, 6))
        ctk.CTkLabel(top_u, text=t("nat_card_upnp", lg), font=ctk.CTkFont(size=15, weight="bold")).pack(side="left")
        self.switch_upnp = ctk.CTkSwitch(top_u, text=t("status_enabled", lg), command=self._action_toggle_upnp)
        self.switch_upnp.pack(side="right")

        ctk.CTkLabel(
            self.card_nat_upnp,
            text=t("nat_desc_upnp", lg),
            text_color="#94a3b8",
            wraplength=480,
            justify="left"
        ).pack(anchor="w", padx=15, pady=(0, 10))

        ctk.CTkLabel(self.card_nat_upnp, text=t("nat_upnp_active", lg), font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=15, pady=(5, 3))
        self.upnp_list_frame = ctk.CTkFrame(self.card_nat_upnp, fg_color="transparent")
        self.upnp_list_frame.pack(fill="both", expand=True, padx=15, pady=(0, 15))

    # --- DIALOGI PRZEKIEROWAŃ PORTÓW (Z PEŁNĄ OBSŁUGĄ EDYCJI) ---

    def _dialog_port_forward(self, rule=None):
        if not self.client.connected:
            return

        lg = self.current_lang
        is_edit = rule is not None
        title = t("pf_dlg_single_edit_title" if is_edit else "pf_dlg_single_new_title", lg)

        orig_sport = str(rule.get("srcport", "")) if is_edit else ""
        orig_proto = safe_int(rule.get("proto", 1)) if is_edit else 1

        dialog = ctk.CTkToplevel(self)
        dialog.title(title)
        dialog.geometry("480x420")
        dialog.resizable(False, False)
        dialog.grab_set()

        f = ctk.CTkFrame(dialog, corner_radius=10)
        f.pack(fill="both", expand=True, padx=15, pady=15)

        ctk.CTkLabel(f, text=title, font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(10, 15))

        f_name = ctk.CTkFrame(f, fg_color="transparent")
        f_name.pack(fill="x", padx=15, pady=5)
        ctk.CTkLabel(f_name, text=t("pf_dlg_lbl_name", lg), width=150, anchor="w").pack(side="left")
        e_name = ctk.CTkEntry(f_name, width=240, placeholder_text="np. NPM HTTPS, Plex, Poczta")
        if is_edit: e_name.insert(0, rule.get("name", ""))
        e_name.pack(side="right")

        f_proto = ctk.CTkFrame(f, fg_color="transparent")
        f_proto.pack(fill="x", padx=15, pady=5)
        ctk.CTkLabel(f_proto, text=t("pf_dlg_lbl_proto", lg), width=150, anchor="w").pack(side="left")
        proto_opts = ["TCP", "UDP", "TCP i UDP"]
        combo_proto = ctk.CTkComboBox(f_proto, values=proto_opts, width=240)
        if is_edit:
            cur_p = orig_proto
            combo_proto.set("TCP" if cur_p == 1 else ("UDP" if cur_p == 2 else "TCP i UDP"))
        else:
            combo_proto.set("TCP")
        combo_proto.pack(side="right")

        f_sport = ctk.CTkFrame(f, fg_color="transparent")
        f_sport.pack(fill="x", padx=15, pady=5)
        ctk.CTkLabel(f_sport, text=t("pf_dlg_lbl_wan_port", lg), width=150, anchor="w").pack(side="left")
        e_sport = ctk.CTkEntry(f_sport, width=240, placeholder_text="1 - 65535 (np. 443)")
        if is_edit: e_sport.insert(0, orig_sport)
        e_sport.pack(side="right")

        f_ip = ctk.CTkFrame(f, fg_color="transparent")
        f_ip.pack(fill="x", padx=15, pady=5)
        ctk.CTkLabel(f_ip, text=t("pf_dlg_lbl_lan_ip", lg), width=150, anchor="w").pack(side="left")
        e_ip = ctk.CTkEntry(f_ip, width=240, placeholder_text="192.168.31.X")
        if is_edit: e_ip.insert(0, rule.get("destip", ""))
        e_ip.pack(side="right")

        devices = self._get_known_devices_hints()
        if devices:
            f_hint = ctk.CTkFrame(f, fg_color="transparent")
            f_hint.pack(fill="x", padx=15, pady=2)
            ctk.CTkLabel(f_hint, text=t("pf_dlg_lbl_host", lg), width=150, anchor="w", text_color="#94a3b8").pack(side="left")
            hint_txt = t("hint_select_known", lg)
            combo_host = ctk.CTkOptionMenu(
                f_hint,
                values=[hint_txt] + [f"{d['ip']} - {d['name']}" for d in devices[:25]],
                width=240,
                command=lambda val, ht=hint_txt: (e_ip.delete(0, "end"), e_ip.insert(0, val.split(" - ")[0].strip())) if val != ht else None
            )
            combo_host.set(hint_txt)
            combo_host.pack(side="right")

        f_dport = ctk.CTkFrame(f, fg_color="transparent")
        f_dport.pack(fill="x", padx=15, pady=5)
        ctk.CTkLabel(f_dport, text=t("pf_dlg_lbl_lan_port", lg), width=150, anchor="w").pack(side="left")
        e_dport = ctk.CTkEntry(f_dport, width=240, placeholder_text="1 - 65535 (np. 4443)")
        if is_edit: e_dport.insert(0, str(rule.get("destport", "")))
        e_dport.pack(side="right")

        def do_save():
            name = e_name.get().strip()
            p_str = combo_proto.get()
            proto_val = 1 if p_str == "TCP" else (2 if p_str == "UDP" else 3)
            sport_str = e_sport.get().strip()
            ip_str = e_ip.get().strip()
            dport_str = e_dport.get().strip()

            if not name or not sport_str or not ip_str or not dport_str:
                messagebox.showerror("Błąd", "Wszystkie pola są wymagane.", parent=dialog)
                return

            try:
                sport_val = int(sport_str)
                dport_val = int(dport_str)
                if not (1 <= sport_val <= 65535) or not (1 <= dport_val <= 65535):
                    raise ValueError()
            except ValueError:
                messagebox.showerror("Błąd", "Porty muszą być liczbami w zakresie od 1 do 65535.", parent=dialog)
                return

            try:
                if is_edit:
                    try:
                        self.client.delete_redirect(int(orig_sport), orig_proto)
                    except Exception:
                        pass

                res = self.client.add_port_redirect(
                    name=name,
                    ip=ip_str,
                    sport=sport_val,
                    dport=dport_val,
                    proto=proto_val,
                    force=1
                )
                if res.get("code") == 0:
                    messagebox.showinfo("Sukces", f"Pomyślnie {'zaktualizowano' if is_edit else 'dodano'} przekierowanie portu {sport_val}!", parent=dialog)
                    dialog.destroy()
                    self._fetch_data_thread()
                else:
                    messagebox.showwarning("Uwaga", f"Odpowiedź routera: {res}", parent=dialog)
            except Exception as e:
                messagebox.showerror("Błąd", f"Nie udało się zapisać reguły: {e}", parent=dialog)

        btn_box = ctk.CTkFrame(f, fg_color="transparent")
        btn_box.pack(fill="x", padx=15, pady=(20, 10))
        btn_save_txt = t("pf_dlg_btn_save_changes", lg) if is_edit else t("pf_dlg_btn_save_rule", lg)
        ctk.CTkButton(btn_box, text=btn_save_txt, fg_color="#16a34a", hover_color="#15803d", width=140, command=do_save).pack(side="left")
        ctk.CTkButton(btn_box, text=t("pf_dlg_btn_cancel", lg), fg_color="#475569", width=100, command=dialog.destroy).pack(side="right")

    def _dialog_range_forward(self, rule=None):
        if not self.client.connected:
            return

        lg = self.current_lang
        is_edit = rule is not None
        title = t("pf_dlg_range_edit_title" if is_edit else "pf_dlg_range_new_title", lg)

        orig_src = rule.get("srcport", {}) if is_edit else {}
        orig_fport = str(orig_src.get("f", "")) if isinstance(orig_src, dict) else str(orig_src)
        orig_proto = safe_int(rule.get("proto", 1)) if is_edit else 1

        dialog = ctk.CTkToplevel(self)
        dialog.title(title)
        dialog.geometry("480x380")
        dialog.resizable(False, False)
        dialog.grab_set()

        f = ctk.CTkFrame(dialog, corner_radius=10)
        f.pack(fill="both", expand=True, padx=15, pady=15)

        ctk.CTkLabel(f, text=title, font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(10, 15))

        f_name = ctk.CTkFrame(f, fg_color="transparent")
        f_name.pack(fill="x", padx=15, pady=5)
        ctk.CTkLabel(f_name, text=t("pf_dlg_lbl_range_name", lg), width=150, anchor="w").pack(side="left")
        e_name = ctk.CTkEntry(f_name, width=240, placeholder_text="np. FTP pasive, Gry Steam")
        if is_edit: e_name.insert(0, rule.get("name", ""))
        e_name.pack(side="right")

        f_proto = ctk.CTkFrame(f, fg_color="transparent")
        f_proto.pack(fill="x", padx=15, pady=5)
        ctk.CTkLabel(f_proto, text=t("pf_dlg_lbl_proto", lg), width=150, anchor="w").pack(side="left")
        proto_opts = ["TCP", "UDP", "TCP i UDP"]
        combo_proto = ctk.CTkComboBox(f_proto, values=proto_opts, width=240)
        if is_edit:
            cur_p = orig_proto
            combo_proto.set("TCP" if cur_p == 1 else ("UDP" if cur_p == 2 else "TCP i UDP"))
        else:
            combo_proto.set("TCP")
        combo_proto.pack(side="right")

        f_ports = ctk.CTkFrame(f, fg_color="transparent")
        f_ports.pack(fill="x", padx=15, pady=5)
        ctk.CTkLabel(f_ports, text=t("pf_dlg_lbl_port_range", lg), width=150, anchor="w").pack(side="left")
        box_p = ctk.CTkFrame(f_ports, fg_color="transparent")
        box_p.pack(side="right")
        e_fport = ctk.CTkEntry(box_p, width=105, placeholder_text="Od np. 50000")
        if is_edit: e_fport.insert(0, orig_fport)
        e_fport.pack(side="left", padx=(0, 5))
        ctk.CTkLabel(box_p, text="-").pack(side="left")
        orig_tport = str(orig_src.get("t", "")) if isinstance(orig_src, dict) else ""
        e_tport = ctk.CTkEntry(box_p, width=105, placeholder_text="Do np. 51000")
        if is_edit: e_tport.insert(0, orig_tport)
        e_tport.pack(side="left", padx=(5, 0))

        f_ip = ctk.CTkFrame(f, fg_color="transparent")
        f_ip.pack(fill="x", padx=15, pady=5)
        ctk.CTkLabel(f_ip, text=t("pf_dlg_lbl_lan_ip", lg), width=150, anchor="w").pack(side="left")
        e_ip = ctk.CTkEntry(f_ip, width=240, placeholder_text="192.168.31.X")
        if is_edit: e_ip.insert(0, rule.get("destip", ""))
        e_ip.pack(side="right")

        devices = self._get_known_devices_hints()
        if devices:
            f_hint = ctk.CTkFrame(f, fg_color="transparent")
            f_hint.pack(fill="x", padx=15, pady=2)
            ctk.CTkLabel(f_hint, text=t("pf_dlg_lbl_host", lg), width=150, anchor="w", text_color="#94a3b8").pack(side="left")
            hint_txt = t("hint_select_known", lg)
            combo_host = ctk.CTkOptionMenu(
                f_hint,
                values=[hint_txt] + [f"{d['ip']} - {d['name']}" for d in devices[:25]],
                width=240,
                command=lambda val, ht=hint_txt: (e_ip.delete(0, "end"), e_ip.insert(0, val.split(" - ")[0].strip())) if val != ht else None
            )
            combo_host.set(hint_txt)
            combo_host.pack(side="right")

        def do_save():
            name = e_name.get().strip()
            p_str = combo_proto.get()
            proto_val = 1 if p_str == "TCP" else (2 if p_str == "UDP" else 3)
            fport_str = e_fport.get().strip()
            tport_str = e_tport.get().strip()
            ip_str = e_ip.get().strip()

            if not name or not fport_str or not tport_str or not ip_str:
                messagebox.showerror("Błąd", "Wszystkie pola są wymagane.", parent=dialog)
                return

            try:
                fport_val = int(fport_str)
                tport_val = int(tport_str)
                if not (1 <= fport_val <= 65535) or not (1 <= tport_val <= 65535) or fport_val > tport_val:
                    raise ValueError()
            except ValueError:
                messagebox.showerror("Błąd", "Porty muszą być liczbami w zakresie od 1 do 65535, a port 'Od' musi być mniejszy lub równy 'Do'.", parent=dialog)
                return

            try:
                if is_edit:
                    try:
                        self.client.delete_redirect(int(orig_fport), orig_proto)
                    except Exception:
                        pass

                res = self.client.add_range_redirect(
                    name=name,
                    ip=ip_str,
                    fport=fport_val,
                    tport=tport_val,
                    proto=proto_val,
                    force=1
                )
                if res.get("code") == 0:
                    messagebox.showinfo("Sukces", f"Pomyślnie {'zaktualizowano' if is_edit else 'dodano'} zakres portów {fport_val}-{tport_val}!", parent=dialog)
                    dialog.destroy()
                    self._fetch_data_thread()
                else:
                    messagebox.showwarning("Uwaga", f"Odpowiedź routera: {res}", parent=dialog)
            except Exception as e:
                messagebox.showerror("Błąd", f"Nie udało się zapisać zakresu: {e}", parent=dialog)

        btn_box = ctk.CTkFrame(f, fg_color="transparent")
        btn_box.pack(fill="x", padx=15, pady=(20, 10))
        btn_save_txt = t("pf_dlg_btn_save_changes", lg) if is_edit else t("pf_dlg_btn_save_range", lg)
        ctk.CTkButton(btn_box, text=btn_save_txt, fg_color="#16a34a", hover_color="#15803d", width=140, command=do_save).pack(side="left")
        ctk.CTkButton(btn_box, text=t("pf_dlg_btn_cancel", lg), fg_color="#475569", width=100, command=dialog.destroy).pack(side="right")

    def _get_known_devices_hints(self):
        hints = []
        if not self.snapshot: return hints
        dev_list = self.snapshot.get("device_list", {}).get("list", [])
        for d in dev_list:
            raw_ip = d.get("ip")
            ip_str = ""
            if isinstance(raw_ip, list) and raw_ip:
                first = raw_ip[0]
                ip_str = first.get("ip", "") if isinstance(first, dict) else str(first)
            elif isinstance(raw_ip, dict):
                ip_str = raw_ip.get("ip", "")
            elif isinstance(raw_ip, str):
                ip_str = raw_ip
            name = d.get("name") or d.get("oname") or d.get("hostname") or "Host"
            if ip_str and str(ip_str).strip():
                hints.append({"ip": str(ip_str).strip(), "name": name})
        return hints

    def _action_delete_port_forward(self, port: int, proto: int, name: str):
        lg = self.current_lang
        prompt = t("pf_del_single_prompt", lg).format(port=port)
        if not messagebox.askyesno(t("pf_del_single_title", lg), prompt):
            return
        def run():
            try:
                res = self.client.delete_redirect(port, proto)
                if res.get("code") == 0:
                    messagebox.showinfo("Sukces", f"Usunięto przekierowanie portu {port}.")
                    self._fetch_data_thread()
                else:
                    messagebox.showwarning("Uwaga", f"Odpowiedź routera: {res}")
            except Exception as e:
                messagebox.showerror("Błąd", f"Nie udało się usunąć: {e}")
        threading.Thread(target=run, daemon=True).start()

    def _action_delete_range_forward(self, fport: int, proto: int, name: str):
        lg = self.current_lang
        prompt = t("pf_del_range_prompt", lg).format(name=name, port=fport)
        if not messagebox.askyesno(t("pf_del_range_title", lg), prompt):
            return
        def run():
            try:
                res = self.client.delete_redirect(fport, proto)
                if res.get("code") == 0:
                    messagebox.showinfo("Sukces", f"Usunięto zakres portów rozpoczynający się od {fport}.")
                    self._fetch_data_thread()
                else:
                    messagebox.showwarning("Uwaga", f"Odpowiedź routera: {res}")
            except Exception as e:
                messagebox.showerror("Błąd", f"Nie udało się usunąć: {e}")
        threading.Thread(target=run, daemon=True).start()

    def _action_save_dmz(self):
        if not self.client.connected: return
        is_on = self.switch_dmz.get() == 1
        if is_on:
            target_ip = self.entry_dmz_ip.get().strip()
            if not target_ip:
                messagebox.showerror("Błąd", "Wprowadź docelowy adres IP hosta DMZ przed zapisaniem.")
                return
            def run():
                try:
                    res = self.client.set_dmz(target_ip)
                    if res.get("code") == 0:
                        messagebox.showinfo("DMZ", f"Strefa DMZ została pomyślnie włączona dla hosta {target_ip}!")
                        self._fetch_data_thread()
                    elif res.get("code") == 1609:
                        messagebox.showerror("Blokada Sprzętowa Xiaomi (Błąd 1609)", "Nie można włączyć DMZ, dopóki na routerze istnieją jakiekolwiek aktywne reguły przekierowania portów!\nUsuń reguły przekierowań portów, aby móc skorzystać ze strefy DMZ.")
                        self.switch_dmz.deselect()
                    else:
                        messagebox.showwarning("Uwaga", f"Odpowiedź routera: {res}")
                except Exception as e:
                    messagebox.showerror("Błąd", f"Błąd włączania DMZ: {e}")
            threading.Thread(target=run, daemon=True).start()
        else:
            def run():
                try:
                    res = self.client.disable_dmz()
                    if res.get("code") == 0:
                        messagebox.showinfo("DMZ", "Strefa DMZ została pomyślnie wyłączona.")
                        self._fetch_data_thread()
                    else:
                        messagebox.showwarning("Uwaga", f"Odpowiedź routera: {res}")
                except Exception as e:
                    messagebox.showerror("Błąd", f"Błąd wyłączania DMZ: {e}")
            threading.Thread(target=run, daemon=True).start()

    def _action_toggle_upnp(self):
        if not self.client.connected: return
        is_on = self.switch_upnp.get() == 1
        switch_val = 1 if is_on else 0
        def run():
            try:
                res = self.client.set_upnp(switch_val)
                if res.get("code") == 0:
                    txt = "WŁĄCZONA" if is_on else "WYŁĄCZONA"
                    messagebox.showinfo("UPnP", f"Usługa UPnP została: {txt}")
                    self._fetch_data_thread()
                else:
                    messagebox.showwarning("Uwaga", f"Odpowiedź routera: {res}")
            except Exception as e:
                messagebox.showerror("Błąd", f"Błąd przełączania UPnP: {e}")
        threading.Thread(target=run, daemon=True).start()

    def _render_nat_tables(self, nat_data):
        lg = self.current_lang
        single_list = nat_data.get("single", []) if isinstance(nat_data, dict) else []
        range_list = nat_data.get("range", []) if isinstance(nat_data, dict) else []
        dmz_info = nat_data.get("dmz", {}) if isinstance(nat_data, dict) else {}
        upnp_info = nat_data.get("upnp", {}) if isinstance(nat_data, dict) else {}

        self.lbl_count_nat_single.configure(text=f"{t('nat_count_active', lg)} {len(single_list)}")
        self.lbl_count_nat_range.configure(text=f"{t('nat_count_active', lg)} {len(range_list)}")

        has_rules = (len(single_list) > 0) or (len(range_list) > 0)
        if has_rules:
            self.lbl_dmz_collision.configure(
                text=t("nat_dmz_collision_warn", lg)
            )
            self.switch_dmz.configure(state="disabled")
        else:
            self.lbl_dmz_collision.configure(text="")
            self.switch_dmz.configure(state="normal")

        dmz_st = safe_int(dmz_info.get("status", 2))
        dmz_ip = dmz_info.get("ip") or dmz_info.get("lanip") or ""
        if dmz_st == 1:
            self.switch_dmz.select()
        else:
            self.switch_dmz.deselect()
        if dmz_ip and not self.entry_dmz_ip.get():
            self.entry_dmz_ip.insert(0, dmz_ip)

        upnp_st = safe_int(upnp_info.get("status", 0))
        if upnp_st == 1:
            self.switch_upnp.select()
        else:
            self.switch_upnp.deselect()

        for w in self.nat_single_list_frame.winfo_children(): w.destroy()
        for w in self.nat_range_list_frame.winfo_children(): w.destroy()
        for w in self.upnp_list_frame.winfo_children(): w.destroy()

        proto_names = {1: "TCP", 2: "UDP", 3: "TCP/UDP"}
        proto_colors = {1: "#2563eb", 2: "#16a34a", 3: "#d97706"}
        lg = self.current_lang

        if not single_list:
            ctk.CTkLabel(self.nat_single_list_frame, text=t("nat_no_single_rules", lg), text_color="#94a3b8").pack(pady=10)
        else:
            for r in single_list:
                rf = ctk.CTkFrame(self.nat_single_list_frame, fg_color="#1e293b", corner_radius=6)
                rf.pack(fill="x", pady=3)

                proto_code = safe_int(r.get("proto", 1))
                p_text = proto_names.get(proto_code, "TCP")
                p_color = proto_colors.get(proto_code, "#2563eb")

                r_name = r.get("name") or t("nat_rule_single", lg)
                sport = r.get("srcport", "?")
                destip = r.get("destip", "?")
                dport = r.get("destport", "?")

                # Przyciski akcji (pack side='right' jako pierwsze - gwarantuje widoczność)
                btn_del = ctk.CTkButton(
                    rf, text=t("btn_delete", lg), fg_color="#dc2626", hover_color="#991b1b", width=70, height=28,
                    command=lambda p=sport, pr=proto_code, n=r_name: self._action_delete_port_forward(p, pr, n)
                )
                btn_del.pack(side="right", padx=(5, 12), pady=6)

                btn_edit = ctk.CTkButton(
                    rf, text=t("btn_edit", lg), fg_color="#0284c7", hover_color="#0369a1", width=70, height=28,
                    command=lambda rule_data=r: self._dialog_port_forward(rule_data)
                )
                btn_edit.pack(side="right", padx=5, pady=6)

                # Szczegóły reguły (pack side='left')
                ctk.CTkLabel(rf, text=f" {p_text} ", fg_color=p_color, text_color="#ffffff", corner_radius=4, font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=(10, 8), pady=8)
                ctk.CTkLabel(rf, text=r_name, font=ctk.CTkFont(weight="bold"), width=160, anchor="w").pack(side="left", padx=5)
                ctk.CTkLabel(rf, text=f"WAN: {sport}  ➔  {destip}:{dport}", font=ctk.CTkFont(family="Consolas"), text_color="#38bdf8").pack(side="left", padx=10)

        if not range_list:
            ctk.CTkLabel(self.nat_range_list_frame, text=t("nat_no_range_rules", lg), text_color="#94a3b8").pack(pady=10)
        else:
            for r in range_list:
                rf = ctk.CTkFrame(self.nat_range_list_frame, fg_color="#1e293b", corner_radius=6)
                rf.pack(fill="x", pady=3)

                proto_code = safe_int(r.get("proto", 1))
                p_text = proto_names.get(proto_code, "TCP")
                p_color = proto_colors.get(proto_code, "#2563eb")

                src_obj = r.get("srcport", {})
                f_port = src_obj.get("f", "?") if isinstance(src_obj, dict) else src_obj
                t_port = src_obj.get("t", "?") if isinstance(src_obj, dict) else src_obj
                destip = r.get("destip", "?")
                r_name = r.get("name") or t("nat_rule_range", lg)
                lbl_rng = t("nat_label_range", lg)

                # Przyciski akcji (pack side='right' jako pierwsze)
                btn_del = ctk.CTkButton(
                    rf, text=t("btn_delete", lg), fg_color="#dc2626", hover_color="#991b1b", width=70, height=28,
                    command=lambda p=f_port, pr=proto_code, n=r_name: self._action_delete_range_forward(p, pr, n)
                )
                btn_del.pack(side="right", padx=(5, 12), pady=6)

                btn_edit = ctk.CTkButton(
                    rf, text=t("btn_edit", lg), fg_color="#0284c7", hover_color="#0369a1", width=70, height=28,
                    command=lambda rule_data=r: self._dialog_range_forward(rule_data)
                )
                btn_edit.pack(side="right", padx=5, pady=6)

                # Szczegóły zakresu (pack side='left')
                ctk.CTkLabel(rf, text=f" {p_text} ", fg_color=p_color, text_color="#ffffff", corner_radius=4, font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=(10, 8), pady=8)
                ctk.CTkLabel(rf, text=r_name, font=ctk.CTkFont(weight="bold"), width=160, anchor="w").pack(side="left", padx=5)
                ctk.CTkLabel(rf, text=f"{lbl_rng} {f_port} - {t_port}  ➔  {destip}", font=ctk.CTkFont(family="Consolas"), text_color="#38bdf8").pack(side="left", padx=10)

        upnp_rules = upnp_info.get("list", []) if isinstance(upnp_info, dict) else []
        if not upnp_rules:
            ctk.CTkLabel(self.upnp_list_frame, text=t("nat_no_upnp", lg), text_color="#94a3b8").pack(pady=5)
        else:
            for u in upnp_rules:
                uf = ctk.CTkFrame(self.upnp_list_frame, fg_color="#1e293b", corner_radius=6)
                uf.pack(fill="x", pady=2)
                u_app = u.get("desc") or u.get("name") or "UPnP App"
                u_ip = u.get("ip") or u.get("destip") or ""
                u_port = u.get("ext_port") or u.get("srcport") or ""
                ctk.CTkLabel(uf, text=f"● {u_app}", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=10, pady=4)
                ctk.CTkLabel(uf, text=f"{u_ip} : Port {u_port}", text_color="#38bdf8", font=ctk.CTkFont(family="Consolas")).pack(side="right", padx=10, pady=4)

    # =========================================================================
    # ZAKŁADKA 7: QOS, DDNS I VPN (Z PODMENU SEGMENTEDBUTTON)
    # =========================================================================

    def _build_qos_vpn_tab(self):
        lg = self.current_lang
        tab = self.tab_qos_vpn
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(1, weight=1)

        top_bar = ctk.CTkFrame(tab, fg_color="transparent")
        top_bar.grid(row=0, column=0, padx=15, pady=(15, 10), sticky="ew")

        ctk.CTkLabel(top_bar, text=("Wybierz moduł:" if lg == "pl" else "Select Module:"), font=ctk.CTkFont(weight="bold")).pack(side="left", padx=(0, 10))
        vals = [
            ("Inteligentny QoS i Kontrola Pasma" if lg == "pl" else "Smart QoS & Bandwidth"),
            ("Dynamiczny DNS (DDNS)" if lg == "pl" else "Dynamic DNS (DDNS)"),
            ("Klient VPN i Smart VPN" if lg == "pl" else "VPN Client & Smart VPN")
        ]
        self.seg_qos_vpn = ctk.CTkOptionMenu(
            top_bar,
            values=vals,
            command=self._on_qos_vpn_tab_change
        )
        self.seg_qos_vpn.set(vals[0])
        self.seg_qos_vpn.pack(side="left", fill="x", expand=True)

        self.container_qos_vpn = ctk.CTkFrame(tab, corner_radius=10)
        self.container_qos_vpn.grid(row=1, column=0, padx=15, pady=(0, 15), sticky="nsew")
        self.container_qos_vpn.grid_columnconfigure(0, weight=1)
        self.container_qos_vpn.grid_rowconfigure(0, weight=1)

        self.view_qos = ctk.CTkScrollableFrame(self.container_qos_vpn)
        self._build_subview_qos()

        self.view_ddns = ctk.CTkScrollableFrame(self.container_qos_vpn)
        self._build_subview_ddns()

        self.view_vpn = ctk.CTkScrollableFrame(self.container_qos_vpn)
        self._build_subview_vpn()

        self.view_qos.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

    def _on_qos_vpn_tab_change(self, choice):
        self.view_qos.grid_forget()
        self.view_ddns.grid_forget()
        self.view_vpn.grid_forget()

        c_low = choice.lower()
        if "qos" in c_low:
            self.view_qos.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        elif "ddns" in c_low:
            self.view_ddns.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        elif "vpn" in c_low:
            self.view_vpn.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

    def _build_subview_qos(self):
        lg = self.current_lang
        f = self.view_qos
        f.grid_columnconfigure((0, 1), weight=1)

        card_l = ctk.CTkFrame(f)
        card_l.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

        top_q = ctk.CTkFrame(card_l, fg_color="transparent")
        top_q.pack(fill="x", padx=15, pady=(15, 8))
        ctk.CTkLabel(top_q, text=t("qos_title", lg), font=ctk.CTkFont(size=15, weight="bold")).pack(side="left")
        self.switch_qos = ctk.CTkSwitch(top_q, text=t("status_enabled", lg), command=self._action_toggle_qos)
        self.switch_qos.pack(side="right")

        ctk.CTkLabel(
            card_l,
            text=t("qos_desc", lg),
            text_color="#94a3b8",
            wraplength=460,
            justify="left"
        ).pack(anchor="w", padx=15, pady=(0, 10))

        ctk.CTkLabel(card_l, text=t("qos_lbl_priorities", lg), font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=15, pady=(5, 3))
        qos_modes = [t("qos_mode_smart", lg), t("qos_mode_game", lg), t("qos_mode_web", lg), t("qos_mode_video", lg)]
        self.seg_qos_mode = ctk.CTkSegmentedButton(
            card_l,
            values=qos_modes,
            command=self._action_change_qos_mode
        )
        self.seg_qos_mode.set(qos_modes[0])
        self.seg_qos_mode.pack(fill="x", padx=15, pady=(0, 15))

        ctk.CTkLabel(card_l, text=t("qos_lbl_band", lg), font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=15, pady=(5, 3))
        f_band = ctk.CTkFrame(card_l, fg_color="transparent")
        f_band.pack(fill="x", padx=15, pady=4)
        ctk.CTkLabel(f_band, text=t("qos_lbl_down", lg)).pack(side="left")
        self.entry_qos_down = ctk.CTkEntry(f_band, width=120, placeholder_text="Mbps")
        self.entry_qos_down.pack(side="right")

        f_up = ctk.CTkFrame(card_l, fg_color="transparent")
        f_up.pack(fill="x", padx=15, pady=4)
        ctk.CTkLabel(f_up, text=t("qos_lbl_up", lg)).pack(side="left")
        self.entry_qos_up = ctk.CTkEntry(f_up, width=120, placeholder_text="Mbps")
        self.entry_qos_up.pack(side="right")

        btn_save_band = ctk.CTkButton(card_l, text=t("qos_btn_save_band", lg), fg_color="#2563eb", hover_color="#1d4ed8", command=self._action_save_qos_band)
        btn_save_band.pack(fill="x", padx=15, pady=(10, 15))

        card_r = ctk.CTkFrame(f)
        card_r.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")

        ctk.CTkLabel(card_r, text=t("qos_card_limits", lg), font=ctk.CTkFont(size=15, weight="bold")).pack(anchor="w", padx=15, pady=(15, 6))
        ctk.CTkLabel(card_r, text=t("qos_desc_limits", lg), text_color="#94a3b8", wraplength=460, justify="left").pack(anchor="w", padx=15, pady=(0, 10))

        self.qos_dev_list_frame = ctk.CTkFrame(card_r, fg_color="transparent")
        self.qos_dev_list_frame.pack(fill="both", expand=True, padx=15, pady=(0, 15))

    def _build_subview_ddns(self):
        lg = self.current_lang
        f = self.view_ddns
        f.grid_columnconfigure(0, weight=1)

        card = ctk.CTkFrame(f)
        card.pack(fill="both", expand=True, padx=5, pady=5)

        top = ctk.CTkFrame(card, fg_color="transparent")
        top.pack(fill="x", padx=15, pady=(15, 8))
        ctk.CTkLabel(top, text=t("ddns_title", lg), font=ctk.CTkFont(size=16, weight="bold")).pack(side="left")
        ctk.CTkButton(top, text=t("ddns_btn_add", lg), fg_color="#2563eb", hover_color="#1d4ed8", width=160, command=self._dialog_add_ddns).pack(side="right")

        ctk.CTkLabel(
            card,
            text=t("ddns_desc", lg),
            text_color="#94a3b8",
            wraplength=800,
            justify="left"
        ).pack(anchor="w", padx=15, pady=(0, 12))

        self.ddns_list_frame = ctk.CTkFrame(card, fg_color="transparent")
        self.ddns_list_frame.pack(fill="both", expand=True, padx=15, pady=(0, 15))

    def _build_subview_vpn(self):
        lg = self.current_lang
        f = self.view_vpn
        f.grid_columnconfigure((0, 1), weight=1)

        card_l = ctk.CTkFrame(f)
        card_l.grid(row=0, column=0, padx=5, pady=5, sticky="nsew")

        top_v = ctk.CTkFrame(card_l, fg_color="transparent")
        top_v.pack(fill="x", padx=15, pady=(15, 8))
        ctk.CTkLabel(top_v, text=t("vpn_title", lg), font=ctk.CTkFont(size=15, weight="bold")).pack(side="left")
        ctk.CTkButton(top_v, text=t("vpn_btn_add", lg), fg_color="#2563eb", hover_color="#1d4ed8", width=140, command=self._dialog_add_vpn).pack(side="right")

        self.lbl_vpn_conn_status = ctk.CTkLabel(card_l, text=t("vpn_status_disconnected", lg), font=ctk.CTkFont(weight="bold"), text_color="#94a3b8")
        self.lbl_vpn_conn_status.pack(anchor="w", padx=15, pady=(0, 10))

        self.vpn_profile_list_frame = ctk.CTkFrame(card_l, fg_color="transparent")
        self.vpn_profile_list_frame.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        card_r = ctk.CTkFrame(f)
        card_r.grid(row=0, column=1, padx=5, pady=5, sticky="nsew")

        top_sv = ctk.CTkFrame(card_r, fg_color="transparent")
        top_sv.pack(fill="x", padx=15, pady=(15, 8))
        ctk.CTkLabel(top_sv, text=t("smartvpn_title", lg), font=ctk.CTkFont(size=15, weight="bold")).pack(side="left")
        self.switch_smartvpn = ctk.CTkSwitch(top_sv, text=t("status_enabled", lg), command=self._action_toggle_smartvpn)
        self.switch_smartvpn.pack(side="right")

        ctk.CTkLabel(
            card_r,
            text=t("smartvpn_desc", lg),
            text_color="#94a3b8",
            wraplength=460,
            justify="left"
        ).pack(anchor="w", padx=15, pady=(0, 10))

        ctk.CTkLabel(card_r, text=t("smartvpn_mode_lbl", lg), font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=15, pady=(5, 3))
        smartvpn_modes = [t("smartvpn_mode_domain", lg), t("smartvpn_mode_device", lg)]
        self.seg_smartvpn_mode = ctk.CTkSegmentedButton(card_r, values=smartvpn_modes, command=self._action_change_smartvpn_mode)
        self.seg_smartvpn_mode.set(smartvpn_modes[0])
        self.seg_smartvpn_mode.pack(fill="x", padx=15, pady=(0, 15))

    # --- AKCJE I DIALOGI DLA QOS, DDNS, VPN ---

    def _action_toggle_qos(self):
        if not self.client.connected: return
        is_on = 1 if self.switch_qos.get() == 1 else 0
        def run():
            try:
                res = self.client.set_qos_switch(is_on)
                if res.get("code") == 0:
                    txt = "WŁĄCZONE" if is_on == 1 else "WYŁĄCZONE"
                    if is_on == 1:
                        # 1. Zastosuj zapamiętany lub aktualnie wybrany w UI tryb priorytetów
                        m_val = getattr(self, "_staged_qos_mode", None)
                        if m_val is None:
                            cur_mode = self.seg_qos_mode.get().lower()
                            if "gry" in cur_mode or "gam" in cur_mode or "ping" in cur_mode:
                                m_val = 1
                            elif "web" in cur_mode or "stron" in cur_mode or "brows" in cur_mode:
                                m_val = 2
                            elif "wideo" in cur_mode or "video" in cur_mode or "stream" in cur_mode:
                                m_val = 3
                            else:
                                m_val = 0
                        try:
                            self.client.set_qos_mode(m_val)
                        except Exception:
                            pass

                        # 2. Zastosuj zapamiętane lub wpisane w polach pasmo
                        b_val = getattr(self, "_staged_qos_band", None)
                        if b_val:
                            try:
                                self.client.set_qos_band(upload=b_val[0], download=b_val[1])
                            except Exception:
                                pass
                        else:
                            try:
                                d_str = self.entry_qos_down.get().strip()
                                u_str = self.entry_qos_up.get().strip()
                                if d_str and u_str:
                                    d_int = int(d_str)
                                    u_int = int(u_str)
                                    if d_int > 0 and u_int > 0:
                                        self.client.set_qos_band(upload=u_int, download=d_int)
                            except Exception:
                                pass

                        messagebox.showinfo("QoS", f"Zarządzanie pasmem zostało {txt} wraz z wybranym trybem i pasmem!")
                    else:
                        messagebox.showinfo("QoS", f"Zarządzanie pasmem zostało {txt}.")
                    self._fetch_data_thread()
                else:
                    messagebox.showwarning("Uwaga", f"Odpowiedź routera: {res}")
            except Exception as e:
                messagebox.showerror("Błąd", f"Błąd przełączania QoS: {e}")
        threading.Thread(target=run, daemon=True).start()

    def _action_change_qos_mode(self, mode_str):
        if not self.client.connected: return
        m_low = mode_str.lower()
        if "gry" in m_low or "gam" in m_low or "ping" in m_low:
            mode_val = 1
        elif "web" in m_low or "stron" in m_low or "brows" in m_low:
            mode_val = 2
        elif "wideo" in m_low or "video" in m_low or "stream" in m_low:
            mode_val = 3
        else:
            mode_val = 0

        self._staged_qos_mode = mode_val

        # Jeśli przełącznik QoS jest wyłączony, zapamiętaj tryb bez wysyłania do routera (zapobiega błędom 1607)
        if self.switch_qos.get() == 0:
            return

        def run():
            try:
                res = self.client.set_qos_mode(mode_val)
                if res.get("code") == 0:
                    messagebox.showinfo("QoS", f"Ustawiono tryb priorytetów: {mode_str}")
                    self._fetch_data_thread()
                elif res.get("code") == 1607:
                    messagebox.showinfo("QoS", "QoS jest wyłączony w routerze. Wybrany tryb zostanie aktywowany po włączeniu przełącznika QoS.")
                else:
                    messagebox.showwarning("Uwaga", f"Odpowiedź routera: {res}")
            except Exception as e:
                messagebox.showerror("Błąd", f"Błąd zmiany trybu QoS: {e}")
        threading.Thread(target=run, daemon=True).start()

    def _action_change_smartvpn_mode(self, mode_str):
        if not self.client.connected: return
        mode_val = 1 if ("domeny" in mode_str.lower() or "domain" in mode_str.lower()) else 2
        def run():
            try:
                res = self.client.set_smartvpn_switch(enable=1, mode=mode_val)
                if res.get("code") == 0:
                    messagebox.showinfo("Smart VPN", f"Zmieniono tryb dzielenia tunelu na: {mode_str}")
                    self._fetch_data_thread()
                else:
                    messagebox.showwarning("Uwaga", f"Odpowiedź routera: {res}")
            except Exception as e:
                messagebox.showerror("Błąd", f"Błąd zmiany trybu: {e}")
        threading.Thread(target=run, daemon=True).start()

    def _action_save_qos_band(self):
        if not self.client.connected: return
        try:
            down = int(self.entry_qos_down.get().strip())
            up = int(self.entry_qos_up.get().strip())
            if down <= 0 or up <= 0: raise ValueError()
        except ValueError:
            messagebox.showerror("Błąd", "Wprowadź poprawne dodatnie liczby dla prędkości pobierania i wysyłania (w Mbps).")
            return

        self._staged_qos_band = (up, down)

        # Jeśli QoS jest wyłączony, zapamiętaj lokalnie i poinformuj użytkownika
        if self.switch_qos.get() == 0:
            messagebox.showinfo(
                "QoS",
                f"Wartości pasma zapamiętane ({down} Mbps pobieranie / {up} Mbps wysyłanie).\n\n"
                "Zostaną one przesłane do routera w momencie włączenia przełącznika QoS."
            )
            return

        def run():
            try:
                res = self.client.set_qos_band(upload=up, download=down)
                if res.get("code") == 0:
                    messagebox.showinfo("Sukces", f"Zapisano pasmo łącza: {down} Mbps pobieranie, {up} Mbps wysyłanie!")
                    self._fetch_data_thread()
                elif res.get("code") == 1607:
                    messagebox.showinfo("QoS", "QoS jest wyłączony w routerze. Wartości pasma zostaną aktywowane po włączeniu przełącznika QoS.")
                else:
                    messagebox.showwarning("Uwaga", f"Odpowiedź routera: {res}")
            except Exception as e:
                messagebox.showerror("Błąd", f"Błąd zapisu pasma: {e}")
        threading.Thread(target=run, daemon=True).start()

    def _dialog_add_ddns(self):
        if not self.client.connected: return
        lg = self.current_lang
        dialog = ctk.CTkToplevel(self)
        dialog.title(t("ddns_dlg_title", lg))
        dialog.geometry("480x420")
        dialog.resizable(False, False)
        dialog.grab_set()

        f = ctk.CTkFrame(dialog, corner_radius=10)
        f.pack(fill="both", expand=True, padx=15, pady=15)

        ctk.CTkLabel(f, text=t("ddns_dlg_heading", lg), font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(10, 15))

        f_prov = ctk.CTkFrame(f, fg_color="transparent")
        f_prov.pack(fill="x", padx=15, pady=5)
        ctk.CTkLabel(f_prov, text=t("ddns_dlg_provider", lg), width=140, anchor="w").pack(side="left")
        providers = ["oray.com", "pubyun.com", "3322.org", "dyndns.com", "no-ip.com"]
        combo_prov = ctk.CTkComboBox(f_prov, values=providers, width=250)
        combo_prov.set("no-ip.com")
        combo_prov.pack(side="right")

        f_dom = ctk.CTkFrame(f, fg_color="transparent")
        f_dom.pack(fill="x", padx=15, pady=5)
        ctk.CTkLabel(f_dom, text=t("ddns_dlg_domain", lg), width=140, anchor="w").pack(side="left")
        e_dom = ctk.CTkEntry(f_dom, width=250, placeholder_text="np. twojadomena.ddns.net")
        e_dom.pack(side="right")

        f_user = ctk.CTkFrame(f, fg_color="transparent")
        f_user.pack(fill="x", padx=15, pady=5)
        ctk.CTkLabel(f_user, text=t("ddns_dlg_user", lg), width=140, anchor="w").pack(side="left")
        e_user = ctk.CTkEntry(f_user, width=250)
        e_user.pack(side="right")

        f_pwd = ctk.CTkFrame(f, fg_color="transparent")
        f_pwd.pack(fill="x", padx=15, pady=5)
        ctk.CTkLabel(f_pwd, text=t("ddns_dlg_pwd", lg), width=140, anchor="w").pack(side="left")
        e_pwd = ctk.CTkEntry(f_pwd, width=250, show="•")
        e_pwd.pack(side="right")

        def do_save():
            prov = combo_prov.get()
            dom = e_dom.get().strip()
            user = e_user.get().strip()
            pwd = e_pwd.get().strip()
            if not dom or not user or not pwd:
                messagebox.showerror("Błąd", "Wszystkie pola są wymagane.", parent=dialog)
                return
            def run():
                try:
                    res = self.client.add_ddns(service=prov, domain=dom, username=user, password=pwd)
                    if res.get("code") == 0:
                        messagebox.showinfo("Sukces", f"Pomyślnie dodano usługę DDNS dla {dom}!", parent=dialog)
                        dialog.destroy()
                        self._fetch_data_thread()
                    else:
                        messagebox.showwarning("Uwaga", f"Odpowiedź routera: {res}", parent=dialog)
                except Exception as e:
                    messagebox.showerror("Błąd", f"Nie udało się dodać usługi DDNS: {e}", parent=dialog)
            threading.Thread(target=run, daemon=True).start()

        btn_box = ctk.CTkFrame(f, fg_color="transparent")
        btn_box.pack(fill="x", padx=15, pady=(20, 10))
        ctk.CTkButton(btn_box, text=t("ddns_dlg_save", lg), fg_color="#16a34a", hover_color="#15803d", width=140, command=do_save).pack(side="left")
        ctk.CTkButton(btn_box, text=t("btn_cancel", lg), fg_color="#475569", width=100, command=dialog.destroy).pack(side="right")

    def _dialog_add_vpn(self):
        if not self.client.connected: return
        lg = self.current_lang
        dialog = ctk.CTkToplevel(self)
        dialog.title(t("vpn_dlg_title", lg))
        dialog.geometry("480x420")
        dialog.resizable(False, False)
        dialog.grab_set()

        f = ctk.CTkFrame(dialog, corner_radius=10)
        f.pack(fill="both", expand=True, padx=15, pady=15)

        ctk.CTkLabel(f, text=t("vpn_dlg_heading", lg), font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(10, 15))

        f_proto = ctk.CTkFrame(f, fg_color="transparent")
        f_proto.pack(fill="x", padx=15, pady=5)
        ctk.CTkLabel(f_proto, text=t("vpn_dlg_proto", lg), width=140, anchor="w").pack(side="left")
        combo_proto = ctk.CTkComboBox(f_proto, values=["pptp", "l2tp"], width=250)
        combo_proto.set("l2tp")
        combo_proto.pack(side="right")

        f_srv = ctk.CTkFrame(f, fg_color="transparent")
        f_srv.pack(fill="x", padx=15, pady=5)
        ctk.CTkLabel(f_srv, text=t("vpn_dlg_srv", lg), width=140, anchor="w").pack(side="left")
        e_srv = ctk.CTkEntry(f_srv, width=250, placeholder_text="np. vpn.domena.pl lub IP")
        e_srv.pack(side="right")

        f_user = ctk.CTkFrame(f, fg_color="transparent")
        f_user.pack(fill="x", padx=15, pady=5)
        ctk.CTkLabel(f_user, text=t("vpn_dlg_user", lg), width=140, anchor="w").pack(side="left")
        e_user = ctk.CTkEntry(f_user, width=250)
        e_user.pack(side="right")

        f_pwd = ctk.CTkFrame(f, fg_color="transparent")
        f_pwd.pack(fill="x", padx=15, pady=5)
        ctk.CTkLabel(f_pwd, text=t("vpn_dlg_pwd", lg), width=140, anchor="w").pack(side="left")
        e_pwd = ctk.CTkEntry(f_pwd, width=250, show="•")
        e_pwd.pack(side="right")

        f_auto = ctk.CTkFrame(f, fg_color="transparent")
        f_auto.pack(fill="x", padx=15, pady=5)
        ctk.CTkLabel(f_auto, text="Automatyczne łączenie:", width=140, anchor="w").pack(side="left")
        sw_auto = ctk.CTkSwitch(f_auto, text="Włączone")
        sw_auto.pack(side="right")

        def do_save():
            proto = combo_proto.get()
            srv = e_srv.get().strip()
            user = e_user.get().strip()
            pwd = e_pwd.get().strip()
            auto_val = 1 if sw_auto.get() == 1 else 0
            if not srv or not user or not pwd:
                messagebox.showerror("Błąd", "Wszystkie pola są wymagane.", parent=dialog)
                return
            def run():
                try:
                    res = self.client.set_vpn(proto=proto, server=srv, username=user, password=pwd, auto=auto_val)
                    if res.get("code") == 0:
                        messagebox.showinfo("Sukces", f"Pomyślnie dodano profil VPN dla {srv}!", parent=dialog)
                        dialog.destroy()
                        self._fetch_data_thread()
                    else:
                        messagebox.showwarning("Uwaga", f"Odpowiedź routera: {res}", parent=dialog)
                except Exception as e:
                    messagebox.showerror("Błąd", f"Nie udało się dodać profilu VPN: {e}", parent=dialog)
            threading.Thread(target=run, daemon=True).start()

        btn_box = ctk.CTkFrame(f, fg_color="transparent")
        btn_box.pack(fill="x", padx=15, pady=(20, 10))
        ctk.CTkButton(btn_box, text=t("vpn_dlg_save", lg), fg_color="#16a34a", hover_color="#15803d", width=140, command=do_save).pack(side="left")
        ctk.CTkButton(btn_box, text=t("btn_cancel", lg), fg_color="#475569", width=100, command=dialog.destroy).pack(side="right")

    def _action_toggle_smartvpn(self):
        if not self.client.connected: return
        is_on = 1 if self.switch_smartvpn.get() == 1 else 0
        def run():
            try:
                res = self.client.set_smartvpn_switch(enable=is_on)
                if res.get("code") == 0:
                    txt = "WŁĄCZONE" if is_on == 1 else "WYŁĄCZONE"
                    messagebox.showinfo("Smart VPN", f"Dzielone tunelowanie zostało: {txt}")
                    self._fetch_data_thread()
                else:
                    messagebox.showwarning("Uwaga", f"Odpowiedź routera: {res}")
            except Exception as e:
                messagebox.showerror("Błąd", f"Błąd przełączania Smart VPN: {e}")
        threading.Thread(target=run, daemon=True).start()

    def _action_change_smartvpn_mode(self, mode_str):
        if not self.client.connected: return
        mode_val = 1 if "domeny" in mode_str else 2
        def run():
            try:
                res = self.client.set_smartvpn_switch(enable=1, mode=mode_val)
                if res.get("code") == 0:
                    messagebox.showinfo("Smart VPN", f"Zmieniono tryb dzielenia tunelu na: {mode_str}")
                    self._fetch_data_thread()
                else:
                    messagebox.showwarning("Uwaga", f"Odpowiedź routera: {res}")
            except Exception as e:
                messagebox.showerror("Błąd", f"Błąd zmiany trybu: {e}")
        threading.Thread(target=run, daemon=True).start()

    def _render_qos_vpn(self, qos_data, ddns_data, vpn_data, vpn_status):
        lg = self.current_lang
        if isinstance(qos_data, dict):
            st = qos_data.get("status", {})
            if safe_int(st.get("on", 0)) == 1:
                self.switch_qos.select()
            else:
                self.switch_qos.deselect()

            mode_val = safe_int(st.get("mode", 0))
            mode_names = {
                0: t("qos_mode_smart", lg),
                1: t("qos_mode_game", lg),
                2: t("qos_mode_web", lg),
                3: t("qos_mode_video", lg)
            }
            if self.switch_qos.get() == 0 and getattr(self, "_staged_qos_mode", None) is not None:
                staged_m = self._staged_qos_mode
                self.seg_qos_mode.set(mode_names.get(staged_m, mode_names[0]))
            else:
                self.seg_qos_mode.set(mode_names.get(mode_val, mode_names[0]))

            band = qos_data.get("band", {})
            cur_down = band.get("download", 0)
            cur_up = band.get("upload", 0)
            if not self.entry_qos_down.get() and cur_down:
                self.entry_qos_down.insert(0, str(cur_down))
            if not self.entry_qos_up.get() and cur_up:
                self.entry_qos_up.insert(0, str(cur_up))

        for w in self.ddns_list_frame.winfo_children(): w.destroy()
        ddns_list = ddns_data.get("list", []) if isinstance(ddns_data, dict) else []
        if not ddns_list:
            ctk.CTkLabel(self.ddns_list_frame, text=t("ddns_no_services", lg), text_color="#94a3b8").pack(pady=10)
        else:
            for d in ddns_list:
                df = ctk.CTkFrame(self.ddns_list_frame, fg_color="#1e293b", corner_radius=6)
                df.pack(fill="x", pady=3)

                d_id = d.get("id")
                d_srv = d.get("service") or "DDNS"
                d_dom = d.get("domain") or "-"
                d_on = d.get("on") == 1

                st_color = "#22c55e" if d_on else "#94a3b8"
                st_txt = t("status_enabled", lg) if d_on else t("status_disabled", lg)
                ctk.CTkLabel(df, text=f" {d_srv} ", fg_color="#2563eb", text_color="#ffffff", corner_radius=4, font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=(10, 8), pady=8)
                ctk.CTkLabel(df, text=d_dom, font=ctk.CTkFont(weight="bold"), width=220, anchor="w").pack(side="left", padx=5)
                ctk.CTkLabel(df, text=f"● {st_txt}", text_color=st_color).pack(side="left", padx=10)

                btn_del = ctk.CTkButton(df, text=t("btn_delete", lg), fg_color="#dc2626", hover_color="#991b1b", width=65, height=28, command=lambda did=d_id: self._action_del_ddns(did))
                btn_del.pack(side="right", padx=(5, 10), pady=6)
                btn_rel = ctk.CTkButton(df, text=t("btn_refresh", lg), fg_color="#3b82f6", width=70, height=28, command=lambda did=d_id: self._action_reload_ddns(did))
                btn_rel.pack(side="right", padx=5, pady=6)
                btn_sw = ctk.CTkButton(df, text=t("btn_disable", lg) if d_on else t("btn_enable", lg), fg_color="#475569", width=70, height=28, command=lambda did=d_id, cur=d_on: self._action_switch_ddns(did, 0 if cur else 1))
                btn_sw.pack(side="right", padx=5, pady=6)

        for w in self.vpn_profile_list_frame.winfo_children(): w.destroy()
        vpn_st_val = safe_int(vpn_status.get("status", 0)) if isinstance(vpn_status, dict) else 0
        if vpn_st_val == 1:
            self.lbl_vpn_conn_status.configure(text=t("vpn_status_connected", lg), text_color="#22c55e")
        else:
            self.lbl_vpn_conn_status.configure(text=t("vpn_status_disconnected", lg), text_color="#94a3b8")

        vpn_list = vpn_data.get("list", []) if isinstance(vpn_data, dict) else []
        if not vpn_list:
            ctk.CTkLabel(self.vpn_profile_list_frame, text=t("vpn_no_profiles", lg), text_color="#94a3b8").pack(pady=10)
        else:
            for v in vpn_list:
                vf = ctk.CTkFrame(self.vpn_profile_list_frame, fg_color="#1e293b", corner_radius=6)
                vf.pack(fill="x", pady=3)

                v_id = v.get("id")
                v_srv = v.get("server") or "Serwer VPN"
                v_proto = (v.get("proto") or "pptp").upper()
                v_auto = t("mode_auto", lg) if v.get("auto") == "1" else t("mode_manual", lg)

                ctk.CTkLabel(vf, text=f" {v_proto} ", fg_color="#7c3aed", text_color="#ffffff", corner_radius=4, font=ctk.CTkFont(size=11, weight="bold")).pack(side="left", padx=(10, 8), pady=8)
                ctk.CTkLabel(vf, text=v_srv, font=ctk.CTkFont(weight="bold"), width=160, anchor="w").pack(side="left", padx=5)
                ctk.CTkLabel(vf, text=f"{t('mode_label', lg)} {v_auto}", text_color="#94a3b8").pack(side="left", padx=5)

                btn_del = ctk.CTkButton(vf, text=t("btn_delete", lg), fg_color="#dc2626", hover_color="#991b1b", width=65, height=28, command=lambda vid=v_id: self._action_del_vpn(vid))
                btn_del.pack(side="right", padx=(5, 10), pady=6)
                btn_conn = ctk.CTkButton(vf, text=t("vpn_btn_connect", lg), fg_color="#16a34a", hover_color="#15803d", width=70, height=28, command=lambda vid=v_id: self._action_conn_vpn(vid))
                btn_conn.pack(side="right", padx=5, pady=6)

    def _action_del_ddns(self, ddns_id):
        if not messagebox.askyesno("Usuń DDNS", "Czy na pewno chcesz usunąć tę usługę DDNS?"): return
        def run():
            try:
                res = self.client.delete_ddns(ddns_id)
                if res.get("code") == 0:
                    messagebox.showinfo("Sukces", "Usunięto usługę DDNS.")
                    self._fetch_data_thread()
                else: messagebox.showwarning("Uwaga", f"Odpowiedź routera: {res}")
            except Exception as e: messagebox.showerror("Błąd", f"Nie udało się usunąć: {e}")
        threading.Thread(target=run, daemon=True).start()

    def _action_reload_ddns(self, ddns_id):
        def run():
            try:
                res = self.client.reload_ddns(ddns_id)
                if res.get("code") == 0:
                    messagebox.showinfo("DDNS", "Wymuszono synchronizację adresu IP z serwerem DDNS!")
                    self._fetch_data_thread()
                else: messagebox.showwarning("Uwaga", f"Odpowiedź routera: {res}")
            except Exception as e: messagebox.showerror("Błąd", f"Błąd synchronizacji: {e}")
        threading.Thread(target=run, daemon=True).start()

    def _action_switch_ddns(self, ddns_id, on_val):
        def run():
            try:
                res = self.client.set_ddns_switch(ddns_id, on_val)
                if res.get("code") == 0:
                    txt = "Włączono" if on_val == 1 else "Wyłączono"
                    messagebox.showinfo("DDNS", f"{txt} usługę DDNS.")
                    self._fetch_data_thread()
                else: messagebox.showwarning("Uwaga", f"Odpowiedź routera: {res}")
            except Exception as e: messagebox.showerror("Błąd", f"Błąd przełączania: {e}")
        threading.Thread(target=run, daemon=True).start()

    def _action_del_vpn(self, vpn_id):
        if not messagebox.askyesno("Usuń VPN", "Czy na pewno chcesz usunąć ten profil VPN?"): return
        def run():
            try:
                res = self.client.delete_vpn(vpn_id)
                if res.get("code") == 0:
                    messagebox.showinfo("Sukces", "Usunięto profil VPN.")
                    self._fetch_data_thread()
                else: messagebox.showwarning("Uwaga", f"Odpowiedź routera: {res}")
            except Exception as e: messagebox.showerror("Błąd", f"Błąd usuwania: {e}")
        threading.Thread(target=run, daemon=True).start()

    def _action_conn_vpn(self, vpn_id):
        def run():
            try:
                res = self.client.connect_vpn(vpn_id)
                if res.get("code") == 0:
                    messagebox.showinfo("VPN", "Wysłano polecenie połączenia z tunelem VPN!")
                    self._fetch_data_thread()
                else: messagebox.showwarning("Uwaga", f"Odpowiedź routera: {res}")
            except Exception as e: messagebox.showerror("Błąd", f"Błąd łączenia z VPN: {e}")
        threading.Thread(target=run, daemon=True).start()

    # =========================================================================
    # ZAKŁADKA 8: PORTY FIZYCZNE I FUNKCJE SPRZĘTOWE (DUAL WAN, LAG, IPTV, GRA)
    # =========================================================================

    def _build_ports_tab(self):
        lg = self.current_lang
        tab = self.tab_ports
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(2, weight=1)

        card_visual = ctk.CTkFrame(tab, corner_radius=10)
        card_visual.grid(row=0, column=0, padx=15, pady=(15, 10), sticky="ew")

        top_v = ctk.CTkFrame(card_visual, fg_color="transparent")
        top_v.pack(fill="x", padx=15, pady=(12, 6))
        ctk.CTkLabel(top_v, text=t("ports_hw_title", lg), font=ctk.CTkFont(size=16, weight="bold")).pack(side="left")

        self.ports_hardware_box = ctk.CTkFrame(card_visual, fg_color="transparent")
        self.ports_hardware_box.pack(fill="x", padx=15, pady=(0, 15))
        self.ports_hardware_box.grid_columnconfigure((0, 1, 2, 3), weight=1)

        top_bar = ctk.CTkFrame(tab, fg_color="transparent")
        top_bar.grid(row=1, column=0, padx=15, pady=(5, 10), sticky="ew")

        ctk.CTkLabel(top_bar, text=("⚡ Konfiguracja Zaawansowanej Roli Portów" if lg == "pl" else "⚡ Hardware Port Role Setup"), font=ctk.CTkFont(size=14, weight="bold")).pack(side="left", padx=(0, 15))
        ctk.CTkLabel(top_bar, text=("Wybierz funkcję:" if lg == "pl" else "Select Feature:"), font=ctk.CTkFont(weight="bold")).pack(side="left", padx=(0, 8))
        ports_tabs = [
            ("Dual WAN (Drugi dostawca Internetu)" if lg == "pl" else "Dual WAN (Secondary ISP)"),
            ("Agregacja LAN (LAG - łączenie portów)" if lg == "pl" else "LAN Aggregation (LAG 802.3ad)"),
            ("Telewizja IP (IPTV Bridge VLAN)" if lg == "pl" else "IP Television (IPTV Bridge)"),
            ("Port Sieciowy Gry (Gaming QoS VIP)" if lg == "pl" else "Gaming Port (VIP QoS)")
        ]
        self.seg_ports = ctk.CTkOptionMenu(
            top_bar,
            values=ports_tabs,
            command=self._on_ports_tab_change
        )
        self.seg_ports.set(ports_tabs[0])
        self.seg_ports.pack(side="left", fill="x", expand=True)

        self.container_ports = ctk.CTkFrame(tab, corner_radius=10)
        self.container_ports.grid(row=2, column=0, padx=15, pady=(0, 15), sticky="nsew")
        self.container_ports.grid_columnconfigure(0, weight=1)
        self.container_ports.grid_rowconfigure(0, weight=1)

        self.view_dualwan = ctk.CTkScrollableFrame(self.container_ports)
        self._build_subview_dualwan()

        self.view_lag = ctk.CTkScrollableFrame(self.container_ports)
        self._build_subview_lag()

        self.view_iptv = ctk.CTkScrollableFrame(self.container_ports)
        self._build_subview_iptv()

        self.view_game = ctk.CTkScrollableFrame(self.container_ports)
        self._build_subview_game()

        self.view_dualwan.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

    def _on_ports_tab_change(self, choice):
        self.view_dualwan.grid_forget()
        self.view_lag.grid_forget()
        self.view_iptv.grid_forget()
        self.view_game.grid_forget()

        c_low = choice.lower()
        if "dual" in c_low or "wan" in c_low:
            self.view_dualwan.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        elif "lag" in c_low or "agreg" in c_low:
            self.view_lag.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        elif "iptv" in c_low or "telew" in c_low or "tv" in c_low:
            self.view_iptv.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        elif "gry" in c_low or "game" in c_low or "gaming" in c_low:
            self.view_game.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)

    def _build_subview_dualwan(self):
        lg = self.current_lang
        f = self.view_dualwan
        f.grid_columnconfigure(0, weight=1)

        card = ctk.CTkFrame(f)
        card.pack(fill="both", expand=True, padx=5, pady=5)

        top = ctk.CTkFrame(card, fg_color="transparent")
        top.pack(fill="x", padx=15, pady=(15, 8))
        ctk.CTkLabel(top, text=t("ports_dualwan_title", lg), font=ctk.CTkFont(size=16, weight="bold")).pack(side="left")
        self.switch_dualwan = ctk.CTkSwitch(top, text=t("status_enabled", lg))
        self.switch_dualwan.pack(side="right")

        ctk.CTkLabel(
            card,
            text=t("ports_dualwan_desc", lg),
            text_color="#94a3b8",
            wraplength=800,
            justify="left"
        ).pack(anchor="w", padx=15, pady=(0, 15))

        f_port = ctk.CTkFrame(card, fg_color="transparent")
        f_port.pack(fill="x", padx=15, pady=6)
        ctk.CTkLabel(f_port, text=t("ports_dualwan_lbl_port", lg), width=220, anchor="w").pack(side="left")
        self.combo_dualwan_port = ctk.CTkComboBox(f_port, values=["Port 2 (2.5G)", "Port 3 (2.5G)", "Port 4 (2.5G)"], width=240)
        self.combo_dualwan_port.set("Port 2 (2.5G)")
        self.combo_dualwan_port.pack(side="left")

        f_mode = ctk.CTkFrame(card, fg_color="transparent")
        f_mode.pack(fill="x", padx=15, pady=6)
        ctk.CTkLabel(f_mode, text=t("ports_dualwan_lbl_mode", lg), width=220, anchor="w").pack(side="left")
        dual_modes = [t("ports_dualwan_mode_load", lg), t("ports_dualwan_mode_fail", lg)]
        self.combo_dualwan_mode = ctk.CTkComboBox(f_mode, values=dual_modes, width=240)
        self.combo_dualwan_mode.set(dual_modes[0])
        self.combo_dualwan_mode.pack(side="left")

        btn_save = ctk.CTkButton(card, text=t("ports_dualwan_btn_save", lg), fg_color="#2563eb", hover_color="#1d4ed8", width=220, command=self._action_save_dualwan)
        btn_save.pack(anchor="w", padx=15, pady=(15, 15))

    def _build_subview_lag(self):
        lg = self.current_lang
        f = self.view_lag
        f.grid_columnconfigure(0, weight=1)

        card = ctk.CTkFrame(f)
        card.pack(fill="both", expand=True, padx=5, pady=5)

        top = ctk.CTkFrame(card, fg_color="transparent")
        top.pack(fill="x", padx=15, pady=(15, 8))
        ctk.CTkLabel(top, text=t("ports_lag_title", lg), font=ctk.CTkFont(size=16, weight="bold")).pack(side="left")
        self.switch_lag = ctk.CTkSwitch(top, text=t("status_enabled", lg))
        self.switch_lag.pack(side="right")

        ctk.CTkLabel(
            card,
            text=t("ports_lag_desc", lg),
            text_color="#94a3b8",
            wraplength=800,
            justify="left"
        ).pack(anchor="w", padx=15, pady=(0, 15))

        f_ports = ctk.CTkFrame(card, fg_color="transparent")
        f_ports.pack(fill="x", padx=15, pady=6)
        ctk.CTkLabel(f_ports, text=t("ports_lag_lbl_ports", lg), width=220, anchor="w").pack(side="left")
        self.combo_lag_ports = ctk.CTkComboBox(f_ports, values=["Port 3 + Port 4", "Port 2 + Port 3"], width=240)
        self.combo_lag_ports.set("Port 3 + Port 4")
        self.combo_lag_ports.pack(side="left")

        f_mode = ctk.CTkFrame(card, fg_color="transparent")
        f_mode.pack(fill="x", padx=15, pady=6)
        ctk.CTkLabel(f_mode, text=t("ports_lag_lbl_mode", lg), width=220, anchor="w").pack(side="left")
        lag_modes = [t("ports_lag_mode_lacp", lg), t("ports_lag_mode_static", lg)]
        self.combo_lag_mode = ctk.CTkComboBox(f_mode, values=lag_modes, width=240)
        self.combo_lag_mode.set(lag_modes[0])
        self.combo_lag_mode.pack(side="left")

        btn_save = ctk.CTkButton(card, text=t("ports_lag_btn_save", lg), fg_color="#2563eb", hover_color="#1d4ed8", width=220, command=self._action_save_lag)
        btn_save.pack(anchor="w", padx=15, pady=(15, 15))

    def _build_subview_iptv(self):
        lg = self.current_lang
        f = self.view_iptv
        f.grid_columnconfigure(0, weight=1)

        card = ctk.CTkFrame(f)
        card.pack(fill="both", expand=True, padx=5, pady=5)

        top = ctk.CTkFrame(card, fg_color="transparent")
        top.pack(fill="x", padx=15, pady=(15, 8))
        ctk.CTkLabel(top, text=t("ports_iptv_title", lg), font=ctk.CTkFont(size=16, weight="bold")).pack(side="left")
        self.switch_iptv = ctk.CTkSwitch(top, text=t("status_enabled", lg))
        self.switch_iptv.pack(side="right")

        ctk.CTkLabel(
            card,
            text=t("ports_iptv_desc", lg),
            text_color="#94a3b8",
            wraplength=800,
            justify="left"
        ).pack(anchor="w", padx=15, pady=(0, 15))

        f_port = ctk.CTkFrame(card, fg_color="transparent")
        f_port.pack(fill="x", padx=15, pady=6)
        ctk.CTkLabel(f_port, text=t("ports_iptv_lbl_port", lg), width=220, anchor="w").pack(side="left")
        self.combo_iptv_port = ctk.CTkComboBox(f_port, values=["Port 2 (2.5G)", "Port 3 (2.5G)", "Port 4 (2.5G)"], width=240)
        self.combo_iptv_port.set("Port 2 (2.5G)")
        self.combo_iptv_port.pack(side="left")

        f_vlan = ctk.CTkFrame(card, fg_color="transparent")
        f_vlan.pack(fill="x", padx=15, pady=6)
        ctk.CTkLabel(f_vlan, text=t("ports_iptv_lbl_vid", lg), width=220, anchor="w").pack(side="left")
        self.entry_iptv_vid = ctk.CTkEntry(f_vlan, width=240, placeholder_text=t("ports_iptv_ph_vid", lg))
        self.entry_iptv_vid.pack(side="left")

        btn_save = ctk.CTkButton(card, text=t("ports_iptv_btn_save", lg), fg_color="#2563eb", hover_color="#1d4ed8", width=220, command=self._action_save_iptv)
        btn_save.pack(anchor="w", padx=15, pady=(15, 15))

    def _build_subview_game(self):
        lg = self.current_lang
        f = self.view_game
        f.grid_columnconfigure(0, weight=1)

        card = ctk.CTkFrame(f)
        card.pack(fill="both", expand=True, padx=5, pady=5)

        top = ctk.CTkFrame(card, fg_color="transparent")
        top.pack(fill="x", padx=15, pady=(15, 8))
        ctk.CTkLabel(top, text=t("ports_game_title", lg), font=ctk.CTkFont(size=16, weight="bold")).pack(side="left")
        self.switch_game = ctk.CTkSwitch(top, text=t("status_enabled", lg))
        self.switch_game.pack(side="right")

        ctk.CTkLabel(
            card,
            text=t("ports_game_desc", lg),
            text_color="#94a3b8",
            wraplength=800,
            justify="left"
        ).pack(anchor="w", padx=15, pady=(0, 15))

        f_port = ctk.CTkFrame(card, fg_color="transparent")
        f_port.pack(fill="x", padx=15, pady=6)
        ctk.CTkLabel(f_port, text=t("ports_game_lbl_port", lg), width=220, anchor="w").pack(side="left")
        self.combo_game_port = ctk.CTkComboBox(f_port, values=["Port 1 (2.5G)", "Port 2 (2.5G)", "Port 3 (2.5G)"], width=240)
        self.combo_game_port.set("Port 3 (2.5G)")
        self.combo_game_port.pack(side="left")

        btn_save = ctk.CTkButton(card, text=t("ports_game_btn_save", lg), fg_color="#2563eb", hover_color="#1d4ed8", width=220, command=self._action_save_game)
        btn_save.pack(anchor="w", padx=15, pady=(15, 15))

    # --- AKCJE PORTÓW FIZYCZNYCH ---

    def _action_save_dualwan(self):
        if not self.client.connected: return
        is_on = 1 if self.switch_dualwan.get() == 1 else 0
        p_txt = self.combo_dualwan_port.get()
        m = re.search(r'\d+', p_txt)
        p_num = m.group(0) if m else "2"
        m_txt = self.combo_dualwan_mode.get()
        mode_val = 0 if ("Agregacja" in m_txt or "Aggregation" in m_txt or "Load" in m_txt) else 1
        def run():
            try:
                res = self.client.set_ps_service("multiwan", enable=is_on, port=p_num, mode=mode_val)
                if res.get("code") == 0:
                    messagebox.showinfo("Dual WAN", "Zaktualizowano konfigurację Dual WAN!")
                    self._fetch_data_thread()
                else: messagebox.showwarning("Uwaga", f"Odpowiedź routera: {res}")
            except Exception as e: messagebox.showerror("Błąd", f"Błąd zapisu Dual WAN: {e}")
        threading.Thread(target=run, daemon=True).start()

    def _action_save_lag(self):
        if not self.client.connected: return
        is_on = 1 if self.switch_lag.get() == 1 else 0
        p_txt = self.combo_lag_ports.get()
        nums = re.findall(r'\d+', p_txt)
        ports_val = f"{nums[0]} {nums[1]}" if len(nums) >= 2 else "2 3"
        m_txt = self.combo_lag_mode.get()
        mode_val = 2 if "LACP" in m_txt else 1
        def run():
            try:
                res = self.client.set_ps_service("lag", enable=is_on, ports=ports_val, mode=mode_val)
                if res.get("code") == 0:
                    messagebox.showinfo("LAG", "Zaktualizowano konfigurację agregacji portów LAN!")
                    self._fetch_data_thread()
                else: messagebox.showwarning("Uwaga", f"Odpowiedź routera: {res}")
            except Exception as e: messagebox.showerror("Błąd", f"Błąd zapisu LAG: {e}")
        threading.Thread(target=run, daemon=True).start()

    def _action_save_iptv(self):
        if not self.client.connected: return
        is_on = 1 if self.switch_iptv.get() == 1 else 0
        p_txt = self.combo_iptv_port.get()
        m = re.search(r'\d+', p_txt)
        p_num = m.group(0) if m else "3"
        vid_str = self.entry_iptv_vid.get().strip()
        vid_val = safe_int(vid_str, -1) if vid_str else -1
        def run():
            try:
                res = self.client.set_ps_service("iptv", enable=is_on, ports=p_num, vid=vid_val)
                if res.get("code") == 0:
                    messagebox.showinfo("IPTV", "Zaktualizowano konfigurację portu IPTV!")
                    self._fetch_data_thread()
                else: messagebox.showwarning("Uwaga", f"Odpowiedź routera: {res}")
            except Exception as e: messagebox.showerror("Błąd", f"Błąd zapisu IPTV: {e}")
        threading.Thread(target=run, daemon=True).start()

    def _action_save_game(self):
        if not self.client.connected: return
        is_on = 1 if self.switch_game.get() == 1 else 0
        p_txt = self.combo_game_port.get()
        m = re.search(r'\d+', p_txt)
        p_num = m.group(0) if m else "3"
        def run():
            try:
                res = self.client.set_ps_service("game", enable=is_on, ports=p_num)
                if res.get("code") == 0:
                    messagebox.showinfo("Port Gry", "Zaktualizowano konfigurację portu gry!")
                    self._fetch_data_thread()
                else: messagebox.showwarning("Uwaga", f"Odpowiedź routera: {res}")
            except Exception as e: messagebox.showerror("Błąd", f"Błąd zapisu Portu Gry: {e}")
        threading.Thread(target=run, daemon=True).start()

    def _render_ports_tab(self, ps_map, ps_services):
        for w in self.ports_hardware_box.winfo_children(): w.destroy()

        ports_list = (ps_map.get("ports") or ps_map.get("list") or []) if isinstance(ps_map, dict) else []
        if not ports_list:
            ports_list = [
                {"port": 1, "service": "wan", "link": 1, "speed": "2.5G"},
                {"port": 2, "service": "lan", "link": 0, "speed": "2.5G"},
                {"port": 3, "service": "lan", "link": 0, "speed": "2.5G"},
                {"port": 4, "service": "lan", "link": 0, "speed": "2.5G"}
            ]

        lg = self.current_lang
        role_colors = {
            "wan": ("#2563eb", "port_role_wan1"),
            "wan2": ("#7c3aed", "port_role_wan2"),
            "lag": ("#d97706", "port_role_lag"),
            "iptv": ("#eab308", "port_role_iptv"),
            "game": ("#16a34a", "port_role_game"),
            "lan": ("#475569", "port_role_lan")
        }

        snap = self.snapshot if isinstance(self.snapshot, dict) else {}
        lan_links = snap.get("lan_info", {}).get("linkList", [])
        wan_link = safe_int(snap.get("wan_info", {}).get("info", {}).get("link", 1), 1)

        for idx, p in enumerate(ports_list):
            p_num = p.get("port", idx + 1)
            p_num_int = safe_int(p_num, idx + 1)
            idx_p = p_num_int - 1
            p_label = p.get("label") or f"PORT {p_num}"
            svc = str(p.get("service", "lan")).lower()
            speed = p.get("speed", "2.5G")

            if svc == "wan":
                is_linked = (wan_link == 1)
            else:
                if isinstance(lan_links, list) and 0 <= idx_p < len(lan_links) and lan_links[idx_p] is not None:
                    is_linked = (safe_int(lan_links[idx_p], 0) == 1)
                else:
                    is_linked = safe_int(p.get("link", 0)) == 1

            card_p = ctk.CTkFrame(self.ports_hardware_box, fg_color="#1e293b", corner_radius=8)
            card_p.grid(row=0, column=idx, padx=6, pady=5, sticky="nsew")

            ctk.CTkLabel(card_p, text=str(p_label).upper(), font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(12, 4))
            ctk.CTkLabel(card_p, text=f"{speed} RJ45", font=ctk.CTkFont(size=11), text_color="#94a3b8").pack(pady=(0, 6))

            badge_col, role_key = role_colors.get(svc, ("#475569", "port_role_lan"))
            badge_txt = t(role_key, lg)
            ctk.CTkLabel(card_p, text=f" {badge_txt} ", fg_color=badge_col, text_color="#ffffff", corner_radius=4, font=ctk.CTkFont(size=11, weight="bold")).pack(pady=4)

            link_txt = f"● {t('port_link_connected', lg)} ({speed})" if is_linked else f"○ {t('port_link_ready', lg)}"
            link_col = "#22c55e" if is_linked else "#94a3b8"
            ctk.CTkLabel(card_p, text=link_txt, text_color=link_col, font=ctk.CTkFont(size=12, weight="bold")).pack(pady=(6, 12))

        # Wykrycie portu WAN oraz wolnych portów LAN
        wan_port = 4
        for p in ports_list:
            if str(p.get("service", "")).lower() == "wan":
                wan_port = safe_int(p.get("port"), 4)
                break

        lan_ports = [safe_int(p.get("port"), 0) for p in ports_list if safe_int(p.get("port"), 0) != wan_port and safe_int(p.get("port"), 0) > 0]
        if not lan_ports:
            lan_ports = [p for p in [1, 2, 3, 4] if p != wan_port]

        lan_opts = [f"Port {p} (2.5G)" for p in lan_ports]
        if lan_opts:
            self.combo_dualwan_port.configure(values=lan_opts)
            self.combo_game_port.configure(values=lan_opts)
            self.combo_iptv_port.configure(values=lan_opts)

        lag_pairs = []
        for i in range(len(lan_ports)):
            for j in range(i + 1, len(lan_ports)):
                lag_pairs.append(f"Port {lan_ports[i]} + Port {lan_ports[j]}")
        if not lag_pairs:
            lag_pairs = ["Port 2 + Port 3"]
        self.combo_lag_ports.configure(values=lag_pairs)

        if isinstance(ps_services, dict):
            mwan = ps_services.get("multiwan", {}).get("multiwan", {})
            if mwan.get("enable") == 1: self.switch_dualwan.select()
            else: self.switch_dualwan.deselect()
            pmap = mwan.get("port_map", [])
            w2_p = None
            for item in pmap:
                if item.get("name") == "WAN2" and str(item.get("port")) not in ["-1", ""]:
                    w2_p = str(item.get("port"))
            if w2_p and any(str(p) == w2_p for p in lan_ports):
                self.combo_dualwan_port.set(f"Port {w2_p} (2.5G)")
            elif lan_opts and self.combo_dualwan_port.get() not in lan_opts:
                self.combo_dualwan_port.set(lan_opts[0])
            mwan_mode = safe_int(mwan.get("policy", {}).get("mode", 0))
            self.combo_dualwan_mode.set(t("ports_dualwan_mode_load", lg) if mwan_mode == 0 else t("ports_dualwan_mode_fail", lg))

            lag = ps_services.get("lag", {}).get("lag", {})
            if lag.get("enable") == 1: self.switch_lag.select()
            else: self.switch_lag.deselect()
            lag_p_str = str(lag.get("ports", ""))
            lag_nums = re.findall(r'\d+', lag_p_str)
            if len(lag_nums) >= 2:
                pair_candidate = f"Port {lag_nums[0]} + Port {lag_nums[1]}"
                pair_rev = f"Port {lag_nums[1]} + Port {lag_nums[0]}"
                if pair_candidate in lag_pairs: self.combo_lag_ports.set(pair_candidate)
                elif pair_rev in lag_pairs: self.combo_lag_ports.set(pair_rev)
            elif lag_pairs and self.combo_lag_ports.get() not in lag_pairs:
                self.combo_lag_ports.set(lag_pairs[0])
            lag_mode = safe_int(lag.get("mode", 2))
            self.combo_lag_mode.set(t("ports_lag_mode_lacp", lg) if lag_mode == 2 else t("ports_lag_mode_static", lg))

            iptv = ps_services.get("iptv", {}).get("iptv", {})
            if iptv.get("enable") == 1: self.switch_iptv.select()
            else: self.switch_iptv.deselect()
            iptv_p = str(iptv.get("ports", ""))
            if iptv_p and any(str(p) == iptv_p for p in lan_ports):
                self.combo_iptv_port.set(f"Port {iptv_p} (2.5G)")
            elif lan_opts and self.combo_iptv_port.get() not in lan_opts:
                self.combo_iptv_port.set(lan_opts[-1] if len(lan_opts) > 1 else lan_opts[0])
            vid_val = safe_int(iptv.get("vid", -1))
            self.entry_iptv_vid.delete(0, "end")
            if vid_val > 0:
                self.entry_iptv_vid.insert(0, str(vid_val))

            game = ps_services.get("game", {}).get("game", {})
            if game.get("enable") == 1: self.switch_game.select()
            else: self.switch_game.deselect()
            game_p = str(game.get("ports", ""))
            if game_p and any(str(p) == game_p for p in lan_ports):
                self.combo_game_port.set(f"Port {game_p} (2.5G)")
            elif lan_opts and self.combo_game_port.get() not in lan_opts:
                self.combo_game_port.set(lan_opts[-1])


    # --- NARZĘDZIA I STEROWANIE ---
    def _build_tools_tab(self):
        lg = self.current_lang
        tab = self.tab_tools
        tab.grid_columnconfigure((0, 1), weight=1)
        tab.grid_rowconfigure((0, 1), weight=1)

        # Karta 1: Strefa Bezpieczeństwa (Hasło i Dostęp)
        p_sec = ctk.CTkFrame(tab)
        p_sec.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.lbl_tools_sec_title = ctk.CTkLabel(p_sec, text=t("tools_card_sec", lg), font=ctk.CTkFont(size=15, weight="bold"))
        self.lbl_tools_sec_title.pack(anchor="w", padx=15, pady=(15, 8))
        self.lbl_tools_sec_desc = ctk.CTkLabel(
            p_sec,
            text=t("tools_desc_sec", lg),
            wraplength=480, justify="left", text_color="#94a3b8"
        )
        self.lbl_tools_sec_desc.pack(anchor="w", padx=15, pady=(0, 15))

        self.btn_chpwd = ctk.CTkButton(
            p_sec, text=t("tools_btn_chpwd", lg),
            fg_color="#2563eb", hover_color="#1d4ed8", height=34,
            command=self._dialog_change_password
        )
        self.btn_chpwd.pack(fill="x", padx=15, pady=6)

        # Karta 2: Kopia Zapasowa i Selektywne Przywracanie
        p_bak = ctk.CTkFrame(tab)
        p_bak.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        self.lbl_tools_bak_title = ctk.CTkLabel(p_bak, text=t("tools_card_bak", lg), font=ctk.CTkFont(size=15, weight="bold"))
        self.lbl_tools_bak_title.pack(anchor="w", padx=15, pady=(15, 8))
        self.lbl_tools_bak_desc = ctk.CTkLabel(
            p_bak,
            text=t("tools_desc_bak", lg),
            wraplength=480, justify="left", text_color="#94a3b8"
        )
        self.lbl_tools_bak_desc.pack(anchor="w", padx=15, pady=(0, 10))

        self.btn_bak_json = ctk.CTkButton(
            p_bak, text=t("tools_btn_bak_json", lg),
            fg_color="#16a34a", hover_color="#15803d", height=34,
            command=self._action_create_json_backup
        )
        self.btn_bak_json.pack(fill="x", padx=15, pady=4)

        self.btn_rest_json = ctk.CTkButton(
            p_bak, text=t("tools_btn_rest_json", lg),
            fg_color="#0284c7", hover_color="#0369a1", height=34,
            command=self._dialog_selective_restore
        )
        self.btn_rest_json.pack(fill="x", padx=15, pady=4)

        self.btn_bak_official = ctk.CTkButton(
            p_bak, text=t("tools_btn_bak_official", lg),
            fg_color="#475569", hover_color="#334155", height=32,
            command=self._action_download_official_backup
        )
        self.btn_bak_official.pack(fill="x", padx=15, pady=4)

        # Karta 3: Raporty i Diagnostyka
        p_rep = ctk.CTkFrame(tab)
        p_rep.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        self.lbl_tools_rep_title = ctk.CTkLabel(p_rep, text=t("tools_card_rep", lg), font=ctk.CTkFont(size=15, weight="bold"))
        self.lbl_tools_rep_title.pack(anchor="w", padx=15, pady=(15, 8))
        self.lbl_tools_rep_desc = ctk.CTkLabel(
            p_rep,
            text=t("tools_desc_rep", lg),
            wraplength=480, justify="left", text_color="#94a3b8"
        )
        self.lbl_tools_rep_desc.pack(anchor="w", padx=15, pady=(0, 15))

        self.btn_export = ctk.CTkButton(
            p_rep, text=t("tools_btn_export_full", lg),
            fg_color="#2b7a4b", hover_color="#205c38", height=34,
            command=self._export_to_md
        )
        self.btn_export.pack(fill="x", padx=15, pady=6)

        f_about = ctk.CTkFrame(p_rep, fg_color="#1e293b", corner_radius=6)
        f_about.pack(fill="x", padx=15, pady=(15, 10))
        ctk.CTkLabel(
            f_about,
            text=f"Xiaomi Router Manager (XRM) v{APP_VERSION}",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#38bdf8"
        ).pack(anchor="w", padx=12, pady=(8, 2))
        ctk.CTkLabel(
            f_about,
            text=f"{t('about_desc', lg)}\nMIT License • 2026",
            font=ctk.CTkFont(size=11),
            text_color="#94a3b8",
            justify="left"
        ).pack(anchor="w", padx=12, pady=(0, 8))

        # Karta 4: Konserwacja Sprzętowa i Reset
        p_hw = ctk.CTkFrame(tab)
        p_hw.grid(row=1, column=1, padx=10, pady=10, sticky="nsew")
        self.lbl_tools_hw_title = ctk.CTkLabel(p_hw, text=t("tools_card_hw", lg), font=ctk.CTkFont(size=15, weight="bold"))
        self.lbl_tools_hw_title.pack(anchor="w", padx=15, pady=(15, 6))

        led_row = ctk.CTkFrame(p_hw, fg_color="transparent")
        led_row.pack(fill="x", padx=15, pady=2)
        self.lbl_led_title = ctk.CTkLabel(led_row, text=t("tools_led_label", lg))
        self.lbl_led_title.pack(side="left")
        self.switch_led = ctk.CTkSwitch(led_row, text=t("status_enabled", lg), command=self._toggle_led)
        self.switch_led.pack(side="right")

        nfc_row = ctk.CTkFrame(p_hw, fg_color="transparent")
        nfc_row.pack(fill="x", padx=15, pady=2)
        self.lbl_nfc_title = ctk.CTkLabel(nfc_row, text=t("tools_nfc_label", lg))
        self.lbl_nfc_title.pack(side="left")
        self.switch_nfc = ctk.CTkSwitch(nfc_row, text=t("status_enabled", lg), command=self._toggle_nfc)
        self.switch_nfc.select()
        self.switch_nfc.pack(side="right")

        time_row = ctk.CTkFrame(p_hw, fg_color="transparent")
        time_row.pack(fill="x", padx=15, pady=3)
        self.lbl_sys_time = ctk.CTkLabel(time_row, text=f"{t('tools_time_label', lg)} --:--:--", text_color="#94a3b8")
        self.lbl_sys_time.pack(side="left")
        self.btn_sync_time = ctk.CTkButton(time_row, text=t("tools_time_sync", lg), width=110, height=26, fg_color="#0284c7", hover_color="#0369a1", command=self._action_sync_time)
        self.btn_sync_time.pack(side="right")

        tz_row = ctk.CTkFrame(p_hw, fg_color="transparent")
        tz_row.pack(fill="x", padx=15, pady=3)
        self.lbl_tools_tz = ctk.CTkLabel(tz_row, text=("Timezone:" if lg == "en" else "Strefa czasowa:"))
        self.lbl_tools_tz.pack(side="left")
        self.btn_save_tools_tz = ctk.CTkButton(tz_row, text=("Save" if lg == "en" else "Zapisz"), width=80, height=26, fg_color="#0284c7", hover_color="#0369a1", command=self._action_save_tools_timezone)
        self.btn_save_tools_tz.pack(side="right", padx=(6, 0))
        tz_labels = [lbl for _, lbl in TZ_DISPLAY_LIST]
        self.combo_tools_tz = ctk.CTkComboBox(tz_row, values=tz_labels, width=250, height=26)
        self.combo_tools_tz.set(tz_labels[0])
        self.combo_tools_tz.pack(side="right")

        self.btn_ota = ctk.CTkButton(p_hw, text=t("btn_check_ota", lg), fg_color="#2563eb", hover_color="#1d4ed8", height=30, command=self._action_check_firmware_update)
        self.btn_ota.pack(fill="x", padx=15, pady=3)

        self.btn_reboot = ctk.CTkButton(p_hw, text=t("tools_btn_reboot", lg), fg_color="#d97706", hover_color="#b45309", height=30, command=self._reboot_router)
        self.btn_reboot.pack(fill="x", padx=15, pady=3)

        self.btn_factory = ctk.CTkButton(p_hw, text=t("tools_btn_factory", lg), fg_color="#dc2626", hover_color="#991b1b", height=30, command=self._prompt_factory_reset)
        self.btn_factory.pack(fill="x", padx=15, pady=(3, 10))

    def _toggle_nfc(self):
        is_on = self.switch_nfc.get() == 1
        def run():
            res = self.client.set_nfc_status(is_on)
            if res.get("code") == 0:
                self.after(0, lambda: messagebox.showinfo("NFC", f"Moduł NFC został {'WŁĄCZONY' if is_on else 'WYŁĄCZONY'}."))
            else:
                self.after(0, lambda: messagebox.showerror("NFC", f"Błąd ustawiania NFC: {res}"))
        threading.Thread(target=run, daemon=True).start()

    def _get_selected_tools_tz(self):
        sel_label = self.combo_tools_tz.get() if hasattr(self, "combo_tools_tz") else ""
        for iana, lbl in TZ_DISPLAY_LIST:
            if lbl == sel_label:
                return iana, TZ_POSIX_MAP.get(iana, "CET-1CEST,M3.5.0,M10.5.0/3"), TZ_INDEX_MAP.get(iana, "2.54")
        return "Europe/Warsaw", TZ_POSIX_MAP.get("Europe/Warsaw", "CET-1CEST,M3.5.0,M10.5.0/3"), TZ_INDEX_MAP.get("Europe/Warsaw", "2.54")

    def _action_sync_time(self):
        import datetime
        lg = self.current_lang
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        iana_tz, posix_tz, tz_idx = self._get_selected_tools_tz()
        def run():
            res = self.client.set_sys_time(time_str=now_str, timezone_str=posix_tz, tz_index=tz_idx)
            if res.get("code") == 0:
                msg = (
                    f"Synchronized router time with PC ({now_str}) and timezone {iana_tz} ({posix_tz})."
                    if lg == "en"
                    else f"Zsynchronizowano czas routera z PC ({now_str}) oraz strefę {iana_tz} ({posix_tz})."
                )
                self.after(0, lambda: messagebox.showinfo(t("succ_title", lg), msg))
                self._fetch_data_thread()
            else:
                err_m = f"Time synchronization error: {res}" if lg == "en" else f"Błąd synchronizacji czasu: {res}"
                self.after(0, lambda: messagebox.showerror(t("err_title", lg), err_m))
        threading.Thread(target=run, daemon=True).start()

    def _action_save_tools_timezone(self):
        lg = self.current_lang
        iana_tz, posix_tz, tz_idx = self._get_selected_tools_tz()
        prompt = (
            f"Set router timezone to {iana_tz} ({posix_tz})?"
            if lg == "en"
            else f"Ustawić strefę czasową routera na {iana_tz} ({posix_tz})?"
        )
        if not messagebox.askyesno(t("info_title", lg), prompt):
            return
        def run():
            res = self.client.set_sys_time(timezone_str=posix_tz, tz_index=tz_idx)
            if res.get("code") == 0:
                msg = (
                    f"Router timezone updated to {iana_tz} ({posix_tz})."
                    if lg == "en"
                    else f"Zapisano strefę czasową routera: {iana_tz} ({posix_tz})."
                )
                self.after(0, lambda: messagebox.showinfo(t("succ_title", lg), msg))
                self._fetch_data_thread()
            else:
                err_m = f"Failed to set timezone: {res}" if lg == "en" else f"Nie udało się ustawić strefy czasowej: {res}"
                self.after(0, lambda: messagebox.showerror(t("err_title", lg), err_m))
        threading.Thread(target=run, daemon=True).start()

    def _action_check_firmware_update(self):
        lg = self.current_lang
        def run():
            res = self.client.check_firmware_update()
            if res.get("code") == 0:
                cur_v = res.get("version", "-")
                need = res.get("needUpdate", 0)
                if need == 1:
                    clog = res.get("changeLog", "")
                    if lg == "en":
                        msg = f"A new firmware version is available!\n\nCurrent version: {cur_v}\nNew version available on Xiaomi OTA servers.\n\nChangelog:\n{clog}"
                        title = "OTA Update"
                    else:
                        msg = f"Dostępna jest nowa wersja oprogramowania!\n\nAktualna wersja: {cur_v}\nNowa wersja dostępna na serwerach Xiaomi OTA.\n\nLista zmian (Changelog):\n{clog}"
                        title = "Aktualizacja OTA"
                    self.after(0, lambda: messagebox.showinfo(title, msg))
                else:
                    if lg == "en":
                        msg = f"Router firmware is up to date.\nInstalled version: {cur_v}\nNo newer OTA updates found."
                        title = "OTA Update"
                    else:
                        msg = f"Oprogramowanie routera jest aktualne.\nWersja zainstalowana: {cur_v}\nBrak nowszych wydań OTA."
                        title = "Aktualizacja OTA"
                    self.after(0, lambda: messagebox.showinfo(title, msg))
            else:
                err_m = f"Failed to check updates: {res.get('error') or res}" if lg == "en" else f"Nie udało się sprawdzić aktualizacji: {res.get('error') or res}"
                self.after(0, lambda: messagebox.showerror(t("msg_error_title", lg), err_m))
        threading.Thread(target=run, daemon=True).start()

    def _dialog_change_password(self):
        lg = self.current_lang
        if not self.client.connected:
            messagebox.showwarning(t("msg_no_conn_title", lg), t("msg_no_conn_body", lg))
            return

        dialog = ctk.CTkToplevel(self)
        dialog.title(t("pwd_dlg_title", lg))
        dialog.geometry("480x380")
        dialog.resizable(False, False)
        dialog.grab_set()

        f = ctk.CTkFrame(dialog, corner_radius=10)
        f.pack(fill="both", expand=True, padx=15, pady=15)

        ctk.CTkLabel(f, text=t("pwd_dlg_heading", lg), font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(15, 5))
        ctk.CTkLabel(f, text=t("pwd_dlg_sub", lg), text_color="#94a3b8", font=ctk.CTkFont(size=12)).pack(pady=(0, 15))

        f_old = ctk.CTkFrame(f, fg_color="transparent")
        f_old.pack(fill="x", padx=15, pady=6)
        ctk.CTkLabel(f_old, text=t("pwd_dlg_old", lg), width=160, anchor="w").pack(side="left")
        e_old = ctk.CTkEntry(f_old, width=220, show="•", placeholder_text=t("pwd_placeholder", lg))
        e_old.pack(side="right")

        f_new1 = ctk.CTkFrame(f, fg_color="transparent")
        f_new1.pack(fill="x", padx=15, pady=6)
        ctk.CTkLabel(f_new1, text=t("pwd_dlg_new1", lg), width=160, anchor="w").pack(side="left")
        e_new1 = ctk.CTkEntry(f_new1, width=220, show="•", placeholder_text="Min. 8...")
        e_new1.pack(side="right")

        f_new2 = ctk.CTkFrame(f, fg_color="transparent")
        f_new2.pack(fill="x", padx=15, pady=6)
        ctk.CTkLabel(f_new2, text=t("pwd_dlg_new2", lg), width=160, anchor="w").pack(side="left")
        e_new2 = ctk.CTkEntry(f_new2, width=220, show="•", placeholder_text="Min. 8...")
        e_new2.pack(side="right")

        def do_change():
            old_p = e_old.get().strip()
            new_p1 = e_new1.get().strip()
            new_p2 = e_new2.get().strip()

            if not old_p or not new_p1 or not new_p2:
                err_m = "Please fill in all fields." if lg == "en" else "Wszystkie pola są wymagane."
                messagebox.showerror(t("msg_error_title", lg), err_m, parent=dialog)
                return
            if new_p1 != new_p2:
                err_m = "New passwords are not identical." if lg == "en" else "Nowe hasła nie są identyczne."
                messagebox.showerror(t("msg_error_title", lg), err_m, parent=dialog)
                return
            if len(new_p1) < 8:
                err_m = "New password must have at least 8 characters." if lg == "en" else "Nowe hasło powinno mieć co najmniej 8 znaków."
                messagebox.showerror(t("msg_error_title", lg), err_m, parent=dialog)
                return
            if old_p == new_p1:
                err_m = "New password must be different from current password." if lg == "en" else "Nowe hasło musi być inne niż dotychczasowe."
                messagebox.showerror(t("msg_error_title", lg), err_m, parent=dialog)
                return

            def run():
                try:
                    res = self.client.set_router_password(old_p, new_p1)
                    if res.get("code") == 0:
                        def on_success():
                            succ_msg = "Router administrator password successfully changed!\nPlease save your new password in a safe place." if lg == "en" else "Hasło administratora routera zostało pomyślnie zmienione!\nZapisz nowe hasło w bezpiecznym miejscu."
                            messagebox.showinfo(t("msg_saved_title", lg), succ_msg, parent=dialog)
                            dialog.destroy()
                        self.after(0, on_success)
                    else:
                        err_m = f"Router rejected password change:\n{res}" if lg == "en" else f"Router odrzucił zmianę hasła:\n{res}"
                        self.after(0, lambda: messagebox.showerror(t("msg_error_title", lg), err_m, parent=dialog))
                except Exception as ex:
                    err_m = f"Failed to change password: {ex}" if lg == "en" else f"Nie udało się zmienić hasła: {ex}"
                    self.after(0, lambda: messagebox.showerror(t("msg_error_title", lg), err_m, parent=dialog))

            threading.Thread(target=run, daemon=True).start()

        btn_box = ctk.CTkFrame(f, fg_color="transparent")
        btn_box.pack(fill="x", padx=15, pady=(20, 10))
        ctk.CTkButton(btn_box, text=t("pwd_dlg_save", lg), fg_color="#16a34a", hover_color="#15803d", width=140, command=do_change).pack(side="left")
        ctk.CTkButton(btn_box, text=t("btn_cancel", lg), fg_color="#475569", width=100, command=dialog.destroy).pack(side="right")

    def _action_create_json_backup(self):
        lg = self.current_lang
        if not self.client.connected:
            messagebox.showwarning(t("msg_no_conn_title", lg), t("msg_no_conn_body", lg))
            return

        rname = self.snapshot.get("init_info", {}).get("routername") or "xiaomi"
        date_str = time.strftime("%Y%m%d_%H%M%S")
        def_name = f"backup_miwifi_{rname}_{date_str}.json"

        out_path = filedialog.asksaveasfilename(
            title="Save JSON Backup (.json)" if lg == "en" else "Zapisz kopię zapasową (.json)",
            initialfile=def_name,
            defaultextension=".json",
            filetypes=[("JSON files", "*.json") if lg == "en" else ("Pliki JSON", "*.json"), ("All files", "*.*") if lg == "en" else ("Wszystkie pliki", "*.*")]
        )
        if not out_path:
            return

        def run():
            try:
                snap = self.client.fetch_full_snapshot()
                with open(out_path, "w", encoding="utf-8") as f:
                    json.dump(snap, f, ensure_ascii=False, indent=2)
                succ_msg = f"Full configuration backup was successfully created and saved to:\n{out_path}" if lg == "en" else f"Pełna kopia konfiguracji została pomyślnie utworzona i zapisana w:\n{out_path}"
                self.after(0, lambda: messagebox.showinfo("Backup" if lg == "en" else "Kopia Zapasowa", succ_msg))
            except Exception as e:
                err_m = f"Failed to create backup: {e}" if lg == "en" else f"Nie udało się utworzyć kopii zapasowej: {e}"
                self.after(0, lambda: messagebox.showerror(t("msg_error_title", lg), err_m))

        threading.Thread(target=run, daemon=True).start()

    def _dialog_selective_restore(self):
        lg = self.current_lang
        if not self.client.connected:
            messagebox.showwarning(t("msg_no_conn_title", lg), t("msg_no_conn_body", lg))
            return

        file_path = filedialog.askopenfilename(
            title=t("rest_dlg_title", lg),
            filetypes=[("JSON files", "*.json") if lg == "en" else ("Pliki JSON", "*.json"), ("All files", "*.*") if lg == "en" else ("Wszystkie pliki", "*.*")]
        )
        if not file_path:
            return

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                snap = json.load(f)
        except Exception as e:
            err_m = f"Failed to read JSON file: {e}" if lg == "en" else f"Nie udało się odczytać pliku JSON: {e}"
            messagebox.showerror(t("msg_error_title", lg), err_m)
            return

        r_name = snap.get("init_info", {}).get("routername") or ("Unknown" if lg == "en" else "Nieznany")
        r_model = clean_model_name(snap.get("init_info", {}).get("displayName") or "Xiaomi")
        r_date = snap.get("fetch_date") or ("no date" if lg == "en" else "brak daty")

        bind_cnt = len(snap.get("mac_bind", {}).get("list", []))
        pf_single_cnt = len(snap.get("port_forward", {}).get("single", []))
        pf_range_cnt = len(snap.get("port_forward", {}).get("range", []))
        wifi_cnt = len(snap.get("wifi_detail", {}).get("info", []))

        dialog = ctk.CTkToplevel(self)
        dialog.title(t("rest_dlg_title", lg))
        dialog.geometry("540x500")
        dialog.resizable(False, False)
        dialog.grab_set()

        f = ctk.CTkFrame(dialog, corner_radius=10)
        f.pack(fill="both", expand=True, padx=15, pady=15)

        ctk.CTkLabel(f, text=t("rest_dlg_heading", lg), font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(12, 4))
        source_txt = t("rest_dlg_source_date", lg).format(model=r_model, name=r_name, date=r_date)
        ctk.CTkLabel(f, text=source_txt, font=ctk.CTkFont(size=11), text_color="#38bdf8").pack(pady=(0, 10))

        ctk.CTkLabel(f, text=t("rest_dlg_prompt", lg), font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=15, pady=(5, 10))

        cb_mac_text = t("rest_dlg_cb_mac", lg).format(cnt=bind_cnt)
        cb_mac = ctk.CTkCheckBox(f, text=cb_mac_text)
        if bind_cnt > 0: cb_mac.select()
        else: cb_mac.deselect()
        cb_mac.pack(anchor="w", padx=20, pady=6)

        cb_pf_text = t("rest_dlg_cb_pf", lg).format(s=pf_single_cnt, r=pf_range_cnt)
        cb_pf = ctk.CTkCheckBox(f, text=cb_pf_text)
        if (pf_single_cnt + pf_range_cnt) > 0: cb_pf.select()
        else: cb_pf.deselect()
        cb_pf.pack(anchor="w", padx=20, pady=6)

        cb_wifi_text = t("rest_dlg_cb_wifi", lg).format(cnt=wifi_cnt)
        cb_wifi = ctk.CTkCheckBox(f, text=cb_wifi_text)
        cb_wifi.deselect()
        cb_wifi.pack(anchor="w", padx=20, pady=6)

        cb_ps = ctk.CTkCheckBox(f, text=t("rest_dlg_cb_ports", lg))
        cb_ps.deselect()
        cb_ps.pack(anchor="w", padx=20, pady=6)

        cb_qos = ctk.CTkCheckBox(f, text=t("rest_dlg_cb_qos", lg))
        cb_qos.deselect()
        cb_qos.pack(anchor="w", padx=20, pady=6)

        lbl_warn = ctk.CTkLabel(
            f,
            text=t("rest_dlg_hint", lg),
            text_color="#94a3b8", font=ctk.CTkFont(size=11), wraplength=480, justify="left"
        )
        lbl_warn.pack(padx=15, pady=(15, 15), anchor="w")

        def do_restore():
            sections = {
                "mac_bind": cb_mac.get() == 1,
                "port_forward": cb_pf.get() == 1,
                "wifi": cb_wifi.get() == 1,
                "ps_services": cb_ps.get() == 1,
                "qos": cb_qos.get() == 1
            }

            if not any(sections.values()):
                err_m = "Select at least one module to restore." if lg == "en" else "Zaznacz co najmniej jeden moduł do przywrócenia."
                messagebox.showwarning(t("msg_warning_title", lg) if "msg_warning_title" in i18n.TRANSLATIONS[lg] else "Selection", err_m, parent=dialog)
                return

            confirm_prompt = "Are you sure you want to restore the selected modules to the router?" if lg == "en" else "Czy na pewno chcesz wgrać wybrane moduły do routera?"
            if not messagebox.askyesno(t("btn_confirm", lg) if "btn_confirm" in i18n.TRANSLATIONS[lg] else "Confirmation", confirm_prompt, parent=dialog):
                return

            def run():
                try:
                    res = self.client.restore_selective_snapshot(snap, sections)
                    succ_txt = "\n".join(res.get("success", [])) or ("No changes" if lg == "en" else "Brak zmian")
                    err_txt = "\n".join(res.get("errors", []))
                    if lg == "en":
                        msg = f"Restore Summary:\n\nSUCCESS:\n{succ_txt}"
                        if err_txt:
                            msg += f"\n\nERRORS / WARNINGS:\n{err_txt}"
                    else:
                        msg = f"Podsumowanie przywracania:\n\nSUKCES:\n{succ_txt}"
                        if err_txt:
                            msg += f"\n\nBŁĘDY / OSTRZEŻENIA:\n{err_txt}"
                    def notify():
                        title = "Restore Completed" if lg == "en" else "Przywracanie Ukończone"
                        messagebox.showinfo(title, msg, parent=dialog)
                        dialog.destroy()
                        self._fetch_data_thread()
                    self.after(0, notify)
                except Exception as ex:
                    err_m = f"Restore error: {ex}" if lg == "en" else f"Wystąpił błąd podczas wgrywania: {ex}"
                    self.after(0, lambda: messagebox.showerror(t("msg_error_title", lg), err_m, parent=dialog))

            threading.Thread(target=run, daemon=True).start()

        btn_box = ctk.CTkFrame(f, fg_color="transparent")
        btn_box.pack(fill="x", padx=15, pady=(10, 5))
        ctk.CTkButton(btn_box, text=t("rest_dlg_btn_restore", lg), fg_color="#16a34a", hover_color="#15803d", width=160, command=do_restore).pack(side="left")
        ctk.CTkButton(btn_box, text=t("btn_cancel", lg), fg_color="#475569", width=100, command=dialog.destroy).pack(side="right")

    def _action_download_official_backup(self):
        lg = self.current_lang
        if not self.client.connected:
            messagebox.showwarning(t("msg_no_conn_title", lg), t("msg_no_conn_body", lg))
            return

        date_str = time.strftime("%Y%m%d_%H%M%S")
        def_name = f"xiaomi_official_backup_{date_str}.tar.gz"

        out_path = filedialog.asksaveasfilename(
            title="Download Xiaomi Official Backup (.tar.gz)" if lg == "en" else "Pobierz oficjalną kopię routera (.tar.gz)",
            initialfile=def_name,
            defaultextension=".tar.gz",
            filetypes=[("Xiaomi Archive", "*.tar.gz") if lg == "en" else ("Archiwum Xiaomi", "*.tar.gz"), ("All files", "*.*") if lg == "en" else ("Wszystkie pliki", "*.*")]
        )
        if not out_path:
            return

        def run():
            try:
                res = self.client.create_official_backup()
                if res.get("code") == 0:
                    filename = res.get("file")
                    ok = self.client.download_official_backup(filename, out_path)
                    if ok:
                        succ_m = f"Successfully downloaded official Xiaomi backup to:\n{out_path}" if lg == "en" else f"Pomyślnie pobrano oficjalną kopię Xiaomi do pliku:\n{out_path}"
                        self.after(0, lambda: messagebox.showinfo("Backup" if lg == "en" else "Kopia Zapasowa", succ_m))
                    else:
                        err_m = "Failed to save downloaded backup file." if lg == "en" else "Nie udało się zapisać pobranego pliku."
                        self.after(0, lambda: messagebox.showerror(t("msg_error_title", lg), err_m))
                else:
                    err_m = f"Router error: {res}" if lg == "en" else f"Router zgłosił błąd: {res}"
                    self.after(0, lambda: messagebox.showerror(t("msg_error_title", lg), err_m))
            except Exception as e:
                err_m = f"Failed to download official backup: {e}" if lg == "en" else f"Błąd pobierania kopii oficjalnej: {e}"
                self.after(0, lambda: messagebox.showerror(t("msg_error_title", lg), err_m))

        threading.Thread(target=run, daemon=True).start()
    # --- KREATOR KONFIGURACJI ---
    def _build_wizard_tab(self):
        lg = self.current_lang
        tab = self.tab_wizard
        tab.grid_columnconfigure(0, weight=1)

        wiz_frame = ctk.CTkFrame(tab)
        wiz_frame.pack(padx=20, pady=20, fill="both", expand=True)

        ctk.CTkLabel(wiz_frame, text=t("wiz_tab_title", lg), font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(20, 10))
        ctk.CTkLabel(wiz_frame, text=t("wiz_tab_desc", lg), justify="center").pack(pady=(0, 20))

        self.lbl_wiz_status = ctk.CTkLabel(wiz_frame, text=t("wiz_tab_status_ready", lg), font=ctk.CTkFont(weight="bold"))
        self.lbl_wiz_status.pack(pady=10)

        ctk.CTkButton(wiz_frame, text=t("wiz_tab_btn_check", lg), width=240, command=self._check_wizard_state).pack(pady=10)

        ctk.CTkButton(
            wiz_frame,
            text=t("wiz_tab_btn_run", lg),
            width=340,
            height=36,
            fg_color="#16a34a",
            hover_color="#15803d",
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self._open_setup_wizard
        ).pack(pady=10)

    def _open_setup_wizard(self):
        """Otwiera 4-krokowy Kreator Pierwszej Konfiguracji w oknie dialogowym."""
        SetupWizardDialog(self)

    def _on_language_change(self, choice):
        self.current_lang = choice.lower()
        self.settings["lang"] = self.current_lang
        save_settings(self.settings)
        self._apply_language()

    def _apply_language(self):
        lg = self.current_lang
        self.title(t("app_title", lg))
        
        # 1. Top Bar
        if hasattr(self, "lbl_gateway_ip"):
            self.lbl_gateway_ip.configure(text=t("gateway_ip", lg))
        if hasattr(self, "auth_mode") and hasattr(self.auth_mode, "_buttons_dict"):
            if "Hasło" in self.auth_mode._buttons_dict:
                self.auth_mode._buttons_dict["Hasło"].configure(text=t("auth_pwd", lg))
            if "Link / Stok" in self.auth_mode._buttons_dict:
                self.auth_mode._buttons_dict["Link / Stok"].configure(text=t("auth_stok", lg))
        if hasattr(self, "auth_entry"):
            is_pwd = (self.auth_mode.get() in ("Hasło", "Password"))
            self.auth_entry.configure(placeholder_text=t("pwd_placeholder", lg) if is_pwd else t("stok_placeholder", lg))
        if hasattr(self, "lbl_auth_hint"):
            is_pwd = (self.auth_mode.get() in ("Hasło", "Password"))
            self.lbl_auth_hint.configure(text=t("hint_pwd", lg) if is_pwd else t("hint_stok", lg))
        if hasattr(self, "btn_connect"):
            self.btn_connect.configure(text=t("disconnect", lg) if self.client.connected else t("connect", lg))
        if hasattr(self, "status_indicator"):
            self.status_indicator.configure(text=t("status_connected", lg) if self.client.connected else t("status_disconnected", lg))
        if hasattr(self, "btn_wizard"):
            self.btn_wizard.configure(text=t("btn_wizard", lg))
            
        # 2. Main Tabview Tabs
        if hasattr(self, "tabs") and hasattr(self.tabs, "_segmented_button"):
            btns = getattr(self.tabs._segmented_button, "_buttons_dict", {})
            if "Pulpit i Urządzenia" in btns:
                btns["Pulpit i Urządzenia"].configure(text=t("tab_dashboard", lg))
            if "Konfiguracja Sieci" in btns:
                btns["Konfiguracja Sieci"].configure(text=t("tab_network", lg))
            if "Porty i Usługi" in btns:
                btns["Porty i Usługi"].configure(text=t("tab_ports", lg))
            if "System i Narzędzia" in btns:
                btns["System i Narzędzia"].configure(text=t("tab_system", lg))

        # 3. Subbars Labels
        if hasattr(self, "lbl_sub_dash"):
            self.lbl_sub_dash.configure(text=t("sub_view_label", lg))
        if hasattr(self, "lbl_sub_net"):
            self.lbl_sub_net.configure(text=t("sub_net_label", lg))
        if hasattr(self, "lbl_sub_ports"):
            self.lbl_sub_ports.configure(text=t("sub_ports_label", lg))
        if hasattr(self, "lbl_sub_sys"):
            self.lbl_sub_sys.configure(text=t("sub_sys_label", lg))

        # 4. Subbars Segmented Buttons
        if hasattr(self, "seg_sub_dashboard"):
            cur_dash = self.seg_sub_dashboard.get()
            vals_dash = [t("sub_dash_live", lg), t("sub_dash_devices", lg), t("sub_dash_mesh", lg)]
            self.seg_sub_dashboard.configure(values=vals_dash)
            if "Mesh" in cur_dash: self.seg_sub_dashboard.set(vals_dash[2])
            elif "Urządz" in cur_dash or "Device" in cur_dash: self.seg_sub_dashboard.set(vals_dash[1])
            else: self.seg_sub_dashboard.set(vals_dash[0])

        if hasattr(self, "seg_sub_network"):
            cur_net = self.seg_sub_network.get()
            vals_net = [t("sub_net_wan", lg), t("sub_net_lan", lg), t("sub_net_wifi", lg)]
            self.seg_sub_network.configure(values=vals_net)
            if "WAN" in cur_net: self.seg_sub_network.set(vals_net[0])
            elif "LAN" in cur_net: self.seg_sub_network.set(vals_net[1])
            else: self.seg_sub_network.set(vals_net[2])

        if hasattr(self, "seg_sub_ports"):
            cur_p = self.seg_sub_ports.get()
            vals_p = [t("sub_ports_nat", lg), t("sub_ports_hw", lg), t("sub_ports_qos", lg)]
            self.seg_sub_ports.configure(values=vals_p)
            if "NAT" in cur_p or "Port" in cur_p: self.seg_sub_ports.set(vals_p[0])
            elif "fizycz" in cur_p or "Phys" in cur_p: self.seg_sub_ports.set(vals_p[1])
            else: self.seg_sub_ports.set(vals_p[2])

        if hasattr(self, "seg_sub_system"):
            cur_s = self.seg_sub_system.get()
            vals_s = [t("sub_sys_tools", lg), t("sub_sys_wizard", lg)]
            self.seg_sub_system.configure(values=vals_s)
            if "Kreator" in cur_s or "Wizard" in cur_s: self.seg_sub_system.set(vals_s[1])
            else: self.seg_sub_system.set(vals_s[0])

        # 5. Dashboard Cards & Controls
        if hasattr(self, "card1_title"):
            self.card1_title.configure(text=t("card_hw_sys", lg))
        if hasattr(self, "card2_title"):
            self.card2_title.configure(text=t("card_cpu_ram", lg))
        if hasattr(self, "card3_title"):
            self.card3_title.configure(text=t("card_wan_speed", lg))
        if hasattr(self, "card_sum_title"):
            self.card_sum_title.configure(text=t("card_summary", lg))
        if hasattr(self, "btn_export_md"):
            self.btn_export_md.configure(text=t("btn_export_md", lg))
        if hasattr(self, "btn_refresh"):
            self.btn_refresh.configure(text=t("btn_refresh", lg))
        if hasattr(self, "switch_autorefresh"):
            self.switch_autorefresh.configure(text=t("autorefresh", lg))

        # 6. Dashboard dynamic labels (snapshot or defaults)
        if hasattr(self, "lbl_model"):
            if not self.snapshot:
                self.lbl_model.configure(text=f"{t('lbl_model', lg)} -")
                self.lbl_rom.configure(text=f"{t('lbl_rom', lg)} -")
                self.lbl_uptime.configure(text=f"{t('lbl_uptime', lg)} -")
                self.lbl_router_id.configure(text=f"{t('lbl_router_id', lg)} -")
                self.lbl_cpu.configure(text=f"{t('lbl_cpu', lg)} --")
                self.lbl_ram.configure(text=f"{t('lbl_ram', lg)} 0 MB / 0 MB (0%)")
                self.lbl_down.configure(text=f"{t('lbl_down', lg)} 0 KB/s")
                self.lbl_up.configure(text=f"{t('lbl_up', lg)} 0 KB/s")
                self.lbl_wan_ip.configure(text=f"{t('lbl_wan_ip', lg)} -")
                self.lbl_wan_dns.configure(text=f"{t('lbl_wan_dns', lg)} -")
                self.lbl_summary_devs.configure(text=f"{t('active_devs', lg)} 0  |  {t('led_status', lg)} -")
                if hasattr(self, "_detected_info") and self._detected_info and not self.client.connected:
                    m, r, g = self._detected_info
                    self.lbl_router_title.configure(text=t("detected_router", lg).format(model=m, name=r, ip=g))
                elif not self.client.connected:
                    self.lbl_router_title.configure(text=t("waiting_connection", lg))

        # 7. Devices tab elements
        if hasattr(self, "lbl_dev_heading"):
            self.lbl_dev_heading.configure(text=t("dev_heading", lg))
        if hasattr(self, "entry_filter_devices"):
            self.entry_filter_devices.configure(placeholder_text=t("dev_search_placeholder", lg))
        if hasattr(self, "switch_show_offline"):
            self.switch_show_offline.configure(text=t("dev_show_offline", lg))
        if hasattr(self, "combo_dev_sort"):
            sort_vals = ["Sort: Default", "Alphabetical (A-Z)", "IP Address", "Connection Type", "Connection Time"] if lg == "en" else ["Sortuj: Domyślnie", "Alfabetycznie (A-Z)", "Adres IP", "Rodzaj połączenia", "Czas połączenia"]
            self.combo_dev_sort.configure(values=sort_vals)
            self.combo_dev_sort.set(sort_vals[0])
        if hasattr(self, "scroll_devices"):
            self._render_devices_list()

        # 8. Mesh tab
        if hasattr(self, "lbl_mesh_title"):
            self.lbl_mesh_title.configure(text=t("sub_dash_mesh", lg))
        if hasattr(self, "btn_ref_mesh"):
            self.btn_ref_mesh.configure(text="🔄 " + t("btn_refresh", lg))
        if hasattr(self, "scroll_mesh"):
            self._render_mesh_tab()

        # 9. Dynamic Rebuild of all subtab views (Network, Ports, Tools, Wizard)
        for f, build_fn in [
            (getattr(self, "tab_wan", None), self._build_wan_tab),
            (getattr(self, "tab_lan", None), self._build_lan_tab),
            (getattr(self, "tab_wifi", None), self._build_wifi_tab),
            (getattr(self, "tab_nat", None), self._build_nat_tab),
            (getattr(self, "tab_ports", None), self._build_ports_tab),
            (getattr(self, "tab_qos_vpn", None), self._build_qos_vpn_tab),
            (getattr(self, "tab_tools", None), self._build_tools_tab),
            (getattr(self, "tab_wizard", None), self._build_wizard_tab),
        ]:
            if f is not None:
                for w in f.winfo_children():
                    w.destroy()
                build_fn()

        if hasattr(self, "seg_sub_network"):
            self._on_sub_network_change(self.seg_sub_network.get())
        if hasattr(self, "seg_sub_ports"):
            self._on_sub_ports_change(self.seg_sub_ports.get())
        if hasattr(self, "seg_sub_system"):
            self._on_sub_system_change(self.seg_sub_system.get())

        if self.snapshot:
            self._update_ui_with_snapshot(self.snapshot)

    # --- LOGIKA APLIKACJI ---

    def _auto_detect(self):
        def run():
            try:
                gw = self.client.discover_gateway()
                info = self.client.probe()
                model = clean_model_name(info.get("displayName") or info.get("hardware") or "Xiaomi")
                rname = info.get("routername") or ""
                def update_gw():
                    try:
                        self.ip_entry.delete(0, "end")
                        self.ip_entry.insert(0, gw)
                        self.client.ip = gw
                        self._detected_info = (model, rname, gw)
                        lg = self.current_lang
                        self.lbl_router_title.configure(text=t("detected_router", lg).format(model=model, name=rname, ip=gw))
                    except Exception:
                        pass
                try:
                    self.after(0, update_gw)
                except Exception:
                    pass
            except Exception as e:
                try:
                    self.after(0, lambda: self.lbl_router_title.configure(text=f"Błąd wykrywania bramy: {e}"))
                except Exception:
                    pass
        threading.Thread(target=run, daemon=True).start()

    def _reset_disconnected_state(self, clear_password: bool = False):
        lg = self.current_lang
        self.client.connected = False
        self.client.stok = None
        self.client.init_info = {}
        self.client.device_id = None
        self.snapshot = {}
        self.raw_devices = []
        self.raw_binds = []
        if clear_password and hasattr(self, "auth_entry"):
            self.auth_entry.delete(0, "end")
        self.status_indicator.configure(text=t("status_disconnected", lg), text_color="#ff5555")
        self.btn_connect.configure(text=t("connect", lg))
        if hasattr(self, "lbl_router_title"):
            self.lbl_router_title.configure(text=t("waiting_connection", lg))
        if hasattr(self, "lbl_model"):
            self.lbl_model.configure(text=f"{t('lbl_model', lg)} -")
        if hasattr(self, "lbl_rom"):
            self.lbl_rom.configure(text=f"{t('lbl_rom', lg)} -")
        if hasattr(self, "lbl_uptime"):
            self.lbl_uptime.configure(text=f"{t('lbl_uptime', lg)} -")
        if hasattr(self, "lbl_router_id"):
            self.lbl_router_id.configure(text=f"{t('lbl_router_id', lg)} -")
        if hasattr(self, "lbl_wan_ip"):
            self.lbl_wan_ip.configure(text=f"{t('lbl_wan_ip', lg)} -")
        if hasattr(self, "lbl_wan_dns"):
            self.lbl_wan_dns.configure(text=f"{t('lbl_wan_dns', lg)} -")
        for attr in ("entry_wan_mtu", "entry_wan_user", "entry_wan_pwd", "entry_wan_dns1", "entry_wan_dns2", "entry_clone_mac"):
            w = getattr(self, attr, None)
            if w is not None:
                try:
                    w.configure(state="normal")
                    w.delete(0, "end")
                except Exception:
                    pass

    def _toggle_connect(self):
        lg = self.current_lang
        if self.client.connected:
            self._reset_disconnected_state(clear_password=False)
            return

        ip = self.ip_entry.get().strip()
        self.client.ip = ip
        self.client.init_info = {}
        self.client.device_id = None
        self.snapshot = {}
        auth_val = self.auth_entry.get().strip()
        mode = self.auth_mode.get()

        def do_login():
            self.after(0, lambda: self.status_indicator.configure(text=t("status_connecting", lg), text_color="#eab308"))
            self.after(0, lambda: self.btn_connect.configure(state="disabled"))

            success = False
            if mode == "Link / Stok":
                success = self.client.login_with_stok(auth_val)
            else:
                success = self.client.login_with_password(auth_val)

            def finish_login():
                self.btn_connect.configure(state="normal")
                if success:
                    self.status_indicator.configure(text=t("status_connected", lg), text_color="#22c55e")
                    self.btn_connect.configure(text=t("disconnect", lg))
                    self._fetch_data_thread()
                else:
                    self.status_indicator.configure(text=t("status_auth_err", lg), text_color="#ef4444")
                    messagebox.showerror(
                        "Error" if lg == "en" else "Błąd",
                        "Failed to connect to router.\nCheck your password or stok link." if lg == "en" else "Nie udało się połączyć z routerem.\nSprawdź poprawność hasła lub linku ze stok."
                    )
            self.after(0, finish_login)

        threading.Thread(target=do_login, daemon=True).start()

    def _fetch_data_thread(self):
        if not self.client.connected:
            return
        threading.Thread(target=self._fetch_data, daemon=True).start()

    def _fetch_data(self):
        try:
            snap = self.client.fetch_full_snapshot()
            self.snapshot = snap

            # Zapisz pełny snapshot do pliku JSON w celu diagnostyki
            try:
                debug_path = os.path.join(APP_DIR, "last_snapshot.json")
                with open(debug_path, "w", encoding="utf-8") as f:
                    json.dump(snap, f, indent=2, ensure_ascii=False)
            except Exception:
                pass

            self.after(0, lambda: self._update_ui_with_snapshot(snap))
        except Exception as e:
            with open(os.path.join(APP_DIR, "gui_errors.log"), "a", encoding="utf-8") as f:
                f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] _fetch_data error: {traceback.format_exc()}\n")

    def _update_ui_with_snapshot(self, snap):
        lg = self.current_lang
        init = snap.get("init_info", {})
        status = snap.get("status", {})
        wan = snap.get("wan_info", {})
        dev_list = snap.get("device_list", {})
        wifi = snap.get("wifi_detail", {})
        led = snap.get("led_status", {})

        # 1. Informacje ogólne
        try:
            raw_model = init.get("displayName") or init.get("hardware") or "Xiaomi"
            model = str(raw_model).replace("Xiaomi路由器", "Xiaomi Router ").strip()
            rname = init.get("routername") or ""
            self.lbl_router_title.configure(text=f"Router: {model} - '{rname}' ({self.client.ip})")
            self.lbl_model.configure(text=f"{t('lbl_model', lg)} {model} (kod {init.get('hardware', '-')})")
            self.lbl_rom.configure(text=f"{t('lbl_rom', lg)} {init.get('romversion', '-')} ({init.get('countrycode', '-')})")
            
            raw_up = status.get("upTime") or status.get("uptime") or 0
            self.lbl_uptime.configure(text=f"{t('lbl_uptime', lg)} {format_uptime(safe_int(raw_up), lang=lg)}")
            self.lbl_router_id.configure(text=f"{t('lbl_router_id', lg)} {init.get('routerId') or init.get('id') or '-'}")
        except Exception as e:
            print("Błąd sekcji systemowej:", e)

        # 2. CPU i RAM
        try:
            cpu_obj = status.get("cpu", {})
            cpu_load = cpu_obj.get("load")
            if cpu_load is not None:
                c_val = safe_float(cpu_load)
                if c_val > 1.0:
                    c_val = c_val / 100.0
                pct = c_val * 100.0
                if pct < 1.0:
                    self.pb_cpu.set(0.01)
                    self.lbl_cpu.configure(text=f"{t('lbl_cpu', lg)} < 1%")
                else:
                    self.pb_cpu.set(min(c_val, 1.0))
                    self.lbl_cpu.configure(text=f"{t('lbl_cpu', lg)} {pct:.1f}%")
            else:
                self.lbl_cpu.configure(text=f"{t('lbl_cpu', lg)} {('no data' if lg == 'en' else 'brak danych')}")

            mem = status.get("mem", {})
            mem_usage = safe_float(mem.get("usage"))
            mem_total = parse_mem_total_bytes(mem.get("total"))
            if mem_total > 0:
                if mem_usage > 1.0:
                    m_percent = mem_usage / 100.0
                    used_b = m_percent * mem_total
                else:
                    m_percent = mem_usage
                    used_b = m_percent * mem_total
                self.pb_ram.set(min(m_percent, 1.0))
                self.lbl_ram.configure(text=f"{t('lbl_ram', lg)} {format_bytes(used_b)} / {format_bytes(mem_total)} ({m_percent*100:.1f}%)")
            else:
                self.lbl_ram.configure(text=f"{t('lbl_ram', lg)} {('no data' if lg == 'en' else 'brak danych')}")
        except Exception as e:
            print("Błąd sekcji CPU/RAM:", e)

        # 3. WAN transfer i Ustawienia WAN
        try:
            wan_speed = status.get("wan", {})
            self.lbl_down.configure(text=f"{t('lbl_down', lg)} {format_speed(safe_float(wan_speed.get('downspeed', 0)))}")
            self.lbl_up.configure(text=f"{t('lbl_up', lg)} {format_speed(safe_float(wan_speed.get('upspeed', 0)))}")

            wan_details = wan.get("info", {}) if isinstance(wan.get("info"), dict) else wan
            if wan_details:
                ipv4 = wan_details.get("ipv4", [{}])
                w_ip = (ipv4[0].get("ip") if isinstance(ipv4, list) and ipv4 else wan_details.get("ip")) or "-"
                w_mask = (ipv4[0].get("mask") if isinstance(ipv4, list) and ipv4 else "") or "-"
                w_gw = wan_details.get("gateWay") or "-"
                dns_list = []
                raw_dns = wan_details.get("dnsServer") or wan_details.get("details", {}).get("dns") or []
                if isinstance(raw_dns, list):
                    for d_item in raw_dns:
                        s_item = str(d_item).strip()
                        if s_item and s_item not in dns_list:
                            dns_list.append(s_item)
                elif isinstance(raw_dns, str) and raw_dns.strip():
                    for part in raw_dns.replace(";", ",").split(","):
                        s_item = part.strip()
                        if s_item and s_item not in dns_list:
                            dns_list.append(s_item)
                for dk in ("dnsAddrs", "dnsAddrs1", "dnsAddrs2"):
                    dv = wan_details.get(dk)
                    if isinstance(dv, list):
                        for d_item in dv:
                            s_item = str(d_item).strip()
                            if s_item and s_item not in dns_list:
                                dns_list.append(s_item)
                    elif isinstance(dv, str) and dv.strip():
                        for part in dv.replace(";", ",").split(","):
                            s_item = part.strip()
                            if s_item and s_item not in dns_list:
                                dns_list.append(s_item)
                dns = dns_list
                dns_str = ", ".join(dns_list)
                w_mac = wan_details.get("mac") or "-"
                w_uptime = format_uptime(safe_int(wan_details.get("uptime", 0)), lang=lg)
                link_status = ("● Connected (Link UP)" if lg == "en" else "● Połączony (Link UP)") if str(wan_details.get("link")) == "1" else ("○ Disconnected / No cable" if lg == "en" else "○ Rozłączony / Brak kabla")

                self.lbl_wan_ip.configure(text=f"{t('lbl_wan_ip', lg)} {w_ip}")
                self.lbl_wan_dns.configure(text=f"{t('lbl_wan_dns', lg)} {dns_str or '-'}")

                # Karta Ustawienia WAN
                self.lbl_wan_link.configure(text=f"{('Link status:' if lg == 'en' else 'Stan łącza:')} {link_status}", text_color="#22c55e" if "Połączony" in link_status or "Connected" in link_status else "#ef4444")
                self.lbl_wan_uptime.configure(text=f"{('Uptime:' if lg == 'en' else 'Czas połączenia (uptime):')} {w_uptime}")
                det = wan_details.get("details", {})
                w_type = det.get("wanType", "pppoe").upper()
                self.lbl_wan_type_info.configure(text=f"{('Connection type:' if lg == 'en' else 'Typ połączenia:')} {w_type}")
                self.lbl_wan_ip_val.configure(text=f"{('External IP:' if lg == 'en' else 'Zewnętrzny IP:')} {w_ip}")
                self.lbl_wan_mask_val.configure(text=f"{('Subnet mask:' if lg == 'en' else 'Maska podsieci:')} {w_mask}")
                self.lbl_wan_gw_val.configure(text=f"{('Default gateway:' if lg == 'en' else 'Brama domyślna:')} {w_gw}")
                self.lbl_wan_dns_val.configure(text=f"{('DNS servers:' if lg == 'en' else 'Serwery DNS:')} {dns_str or '-'}")
                self.lbl_wan_mac_val.configure(text=f"{('WAN MAC address:' if lg == 'en' else 'Adres MAC WAN:')} {w_mac}")
                w_mtu = str(det.get("mtu") or wan_details.get("mtu") or "-")
                self.lbl_wan_mtu_val.configure(text=f"{('MTU size:' if lg == 'en' else 'Rozmiar MTU:')} {w_mtu}")

                if hasattr(self, "seg_wan_mode"):
                    vals = self.seg_wan_mode.cget("values")
                    target_val = None
                    if "DHCP" in w_type:
                        target_val = next((v for v in vals if "dhcp" in v.lower()), None)
                    elif "STAT" in w_type:
                        target_val = next((v for v in vals if "stat" in v.lower()), None)
                    elif "PPPOE" in w_type:
                        target_val = next((v for v in vals if "pppoe" in v.lower()), None)
                    if target_val and target_val != self.seg_wan_mode.get():
                        self.seg_wan_mode.set(target_val)
                        self._on_wan_mode_change(target_val)

                ipv6_info = wan_details.get("ipv6_info", {})
                ipv6_mode = str(ipv6_info.get("ipv6_mode") or ipv6_info.get("wanType") or "").strip()
                if not ipv6_mode or ipv6_mode.lower() in ("off", "disabled", "none", "0"):
                    ipv6_txt = "Disabled" if lg == "en" else "Wyłączony"
                else:
                    ipv6_txt = f"{ipv6_mode.capitalize()} ({'enabled' if lg == 'en' else 'aktywny'})"
                self.lbl_wan_ipv6_val.configure(text=f"{('IPv6 Protocol:' if lg == 'en' else 'Protokół IPv6:')} {ipv6_txt}")

                # Pre-fill pól formularza WAN jeśli nie były jeszcze wypełnione
                if not self.entry_wan_user.get() and det.get("username"):
                    self.entry_wan_user.insert(0, det.get("username"))
                if not self.entry_wan_pwd.get() and det.get("password"):
                    self.entry_wan_pwd.insert(0, det.get("password"))
                if w_mtu and w_mtu != "-":
                    if not self.entry_wan_mtu.get().strip():
                        self.entry_wan_mtu.delete(0, "end")
                        self.entry_wan_mtu.insert(0, w_mtu)
                # Sprawdzenie czy w routerze włączone są własne serwery DNS
                peerdns = str(det.get("peerdns", ""))
                is_custom_dns = (peerdns == "0") or (bool(dns) and peerdns != "1")
                if is_custom_dns:
                    self.switch_wan_custom_dns.select()
                else:
                    self.switch_wan_custom_dns.deselect()
                self._toggle_custom_dns()

                if isinstance(dns, list) and len(dns) >= 1:
                    if not self.entry_wan_dns1.get() or self.entry_wan_dns1.get() != dns[0]:
                        self.entry_wan_dns1.delete(0, "end")
                        self.entry_wan_dns1.insert(0, dns[0])
                    if len(dns) >= 2:
                        if not self.entry_wan_dns2.get() or self.entry_wan_dns2.get() != dns[1]:
                            self.entry_wan_dns2.delete(0, "end")
                            self.entry_wan_dns2.insert(0, dns[1])
                if not self.entry_clone_mac.get() and w_mac:
                    self.entry_clone_mac.insert(0, w_mac)
        except Exception as e:
            print("Błąd sekcji WAN:", e)

        # 3b. Ustawienia LAN i Rezerwacje IP (macbind_info)
        try:
            lan = snap.get("lan_info", {}).get("info", {})
            dhcp = snap.get("lan_dhcp", {}).get("info", {})
            mac_b = snap.get("mac_bind", {})

            # IP routera
            lan_ipv4 = lan.get("ipv4", [{}])
            if isinstance(lan_ipv4, list) and lan_ipv4:
                l_ip = lan_ipv4[0].get("ip", "192.168.31.1")
                l_mask = lan_ipv4[0].get("mask", "255.255.255.0")
                if not self.entry_lan_ip.get() or self.entry_lan_ip.get() == "192.168.31.1":
                    self.entry_lan_ip.delete(0, "end")
                    self.entry_lan_ip.insert(0, l_ip)
                if not self.entry_lan_mask.get() or self.entry_lan_mask.get() == "255.255.255.0":
                    self.entry_lan_mask.delete(0, "end")
                    self.entry_lan_mask.insert(0, l_mask)

            # Serwer DHCP
            if dhcp:
                d_start = str(dhcp.get("start", "5"))
                d_limit = str(dhcp.get("limit", "250"))
                d_lease_raw = str(dhcp.get("leasetime", "720m")).strip()
                m_l = re.match(r"^(\d+)\s*([mhsd]?)$", d_lease_raw, re.IGNORECASE)
                if m_l:
                    l_num = int(m_l.group(1))
                    l_unit = m_l.group(2).lower() if m_l.group(2) else "m"
                    if l_unit == "h": d_lease_min = str(l_num * 60)
                    elif l_unit == "d": d_lease_min = str(l_num * 1440)
                    elif l_unit == "s": d_lease_min = str(max(2, l_num // 60))
                    else: d_lease_min = str(l_num)
                else:
                    d_lease_min = "720"
                d_dns1 = str(dhcp.get("dns1", ""))
                d_dns2 = str(dhcp.get("dns2", ""))

                self.entry_dhcp_start.delete(0, "end")
                self.entry_dhcp_start.insert(0, d_start)
                self.entry_dhcp_limit.delete(0, "end")
                self.entry_dhcp_limit.insert(0, d_limit)
                self.entry_dhcp_lease.delete(0, "end")
                self.entry_dhcp_lease.insert(0, d_lease_min)
                if d_dns1:
                    self.entry_dhcp_dns1.delete(0, "end")
                    self.entry_dhcp_dns1.insert(0, d_dns1)
                if d_dns2:
                    self.entry_dhcp_dns2.delete(0, "end")
                    self.entry_dhcp_dns2.insert(0, d_dns2)

            # Rezerwacje IP (macbind_info)
            self.raw_binds = mac_b.get("list", [])
            self._render_mac_bind_list(self.entry_filter_bind.get().strip().lower())
        except Exception as e:
            print("Błąd sekcji LAN:", e)

        # 4. Lista urządzeń
        try:
            self.raw_devices = dev_list.get("list", [])
            led_txt = ("ON" if str(led.get('status')) == '1' else "OFF") if lg == "en" else ("Włączone" if str(led.get('status')) == '1' else "Wyłączone")
            self.lbl_summary_devs.configure(text=f"{t('active_devs', lg)} {len(self.raw_devices)}  |  {t('led_status', lg)} {led_txt}")
            self._render_devices_list()
        except Exception as e:
            print("Błąd renderowania listy urządzeń:", e)

        # 5. Wi-Fi
        try:
            wifi_list = wifi.get("info", [])
            bsd_on = wifi.get("bsd") == 1

            if bsd_on:
                self.switch_bsd.select()
            else:
                self.switch_bsd.deselect()
            self._update_smartconnect_layout(bsd_on)

            for idx, w in enumerate(wifi_list):
                w_idx = safe_int(w.get("wifiIndex", idx + 1))
                ssid = w.get("ssid", "")
                pwd = w.get("password", "")
                enc = str(w.get("encryption", "psk2"))
                tx = str(w.get("txpwr", "max"))
                hidden = safe_int(w.get("hidden", 0))
                status_on = safe_int(w.get("status", 1)) == 1
                channel = str(w.get("channel", "Auto"))
                ch_info = w.get("channelInfo", {})
                b_list = ch_info.get("bandList", [])
                width_str = "do 160 MHz" if ("160" in b_list or "80" in b_list) else "do 40 MHz"

                if w_idx == 1:
                    # Pasmo 2.4G
                    if ssid:
                        self.entry_wifi_ssid_2g.delete(0, "end")
                        self.entry_wifi_ssid_2g.insert(0, ssid)
                    if not self.entry_wifi_pwd_2g.get() or pwd:
                        self.entry_wifi_pwd_2g.delete(0, "end")
                        self.entry_wifi_pwd_2g.insert(0, pwd)
                    self.combo_wifi_enc_2g.set(code_to_enc(enc, self.current_lang))
                    self.combo_wifi_tx_2g.set(code_to_tx(tx, self.current_lang))

                    if hasattr(self, "entry_wifi_ssid_common"):
                        if ssid:
                            self.entry_wifi_ssid_common.delete(0, "end")
                            self.entry_wifi_ssid_common.insert(0, ssid)
                    if hasattr(self, "entry_wifi_pwd_common"):
                        if not self.entry_wifi_pwd_common.get() or pwd:
                            self.entry_wifi_pwd_common.delete(0, "end")
                            self.entry_wifi_pwd_common.insert(0, pwd)
                    if hasattr(self, "combo_wifi_enc_common"):
                        self.combo_wifi_enc_common.set(code_to_enc(enc, self.current_lang))
                    
                    ch_code = w.get("channel", "0")
                    bw_code = w.get("bandwidth", "0")
                    self.combo_wifi_ch_2g.set(code_to_channel(ch_code))
                    self.combo_wifi_bw_2g.set(code_to_bandwidth(bw_code, "2g"))
                    cur_ch = ch_info.get("channel", ch_code)
                    cur_txt = t("wifi_cur_tag", self.current_lang).format(ch=cur_ch) if str(ch_code) == "0" else ""

                    if hidden:
                        self.switch_wifi_hidden_2g.select()
                        self.switch_wifi_hidden_2g.configure(text=t("wifi_hidden_switch_on", self.current_lang))
                    else:
                        self.switch_wifi_hidden_2g.deselect()
                        self.switch_wifi_hidden_2g.configure(text=t("wifi_hidden_switch_off", self.current_lang))
                    if status_on:
                        self.switch_wifi_on_2g.select()
                    else:
                        self.switch_wifi_on_2g.deselect()
                    self.lbl_wifi_status_2g.configure(
                        text=t("wifi_status_channel", self.current_lang).format(
                            ch=code_to_channel(ch_code),
                            cur=cur_txt,
                            width=t("wifi_width_160", self.current_lang) if ("160" in b_list or "80" in b_list) else t("wifi_width_40", self.current_lang),
                            status=t("status_enabled", self.current_lang) if status_on else t("status_disabled", self.current_lang)
                        )
                    )
                elif w_idx == 2:
                    # Pasmo 5G
                    if ssid:
                        self.entry_wifi_ssid_5g.delete(0, "end")
                        self.entry_wifi_ssid_5g.insert(0, ssid)
                    if not self.entry_wifi_pwd_5g.get() or pwd:
                        self.entry_wifi_pwd_5g.delete(0, "end")
                        self.entry_wifi_pwd_5g.insert(0, pwd)
                    self.combo_wifi_enc_5g.set(code_to_enc(enc, self.current_lang))
                    self.combo_wifi_tx_5g.set(code_to_tx(tx, self.current_lang))
                    
                    ch_code = w.get("channel", "0")
                    bw_code = w.get("bandwidth", "0")
                    self.combo_wifi_ch_5g.set(code_to_channel(ch_code))
                    self.combo_wifi_bw_5g.set(code_to_bandwidth(bw_code, "5g"))
                    cur_ch = ch_info.get("channel", ch_code)
                    cur_txt = t("wifi_cur_tag", self.current_lang).format(ch=cur_ch) if str(ch_code) == "0" else ""

                    if hidden:
                        self.switch_wifi_hidden_5g.select()
                        self.switch_wifi_hidden_5g.configure(text=t("wifi_hidden_switch_on", self.current_lang))
                    else:
                        self.switch_wifi_hidden_5g.deselect()
                        self.switch_wifi_hidden_5g.configure(text=t("wifi_hidden_switch_off", self.current_lang))
                    if status_on:
                        self.switch_wifi_on_5g.select()
                    else:
                        self.switch_wifi_on_5g.deselect()
                    self.lbl_wifi_status_5g.configure(
                        text=t("wifi_status_channel_5g", self.current_lang).format(
                            ch=code_to_channel(ch_code),
                            cur=cur_txt,
                            width=t("wifi_width_160", self.current_lang) if ("160" in b_list or "80" in b_list) else t("wifi_width_40", self.current_lang),
                            status=t("status_enabled", self.current_lang) if status_on else t("status_disabled", self.current_lang)
                        )
                    )

            # Zaawansowane opcje Wi-Fi
            first_w = wifi_list[0] if wifi_list else {}
            # 1. Wi-Fi 5 Kompatybilność (ax == 0 oznacza włączony tryb zgodności Wi-Fi 5)
            ax_val = safe_int(first_w.get("ax", 1))
            if ax_val == 0:
                self.switch_wifi5_compat.select()
                self.switch_wifi5_compat.configure(text=t("status_enabled", self.current_lang))
            else:
                self.switch_wifi5_compat.deselect()
                self.switch_wifi5_compat.configure(text=t("status_disabled", self.current_lang))

            # 2. TWT
            twt_data = self.snapshot.get("twt", {})
            if isinstance(twt_data, dict) and safe_int(twt_data.get("status", 0)) == 1:
                self.switch_twt.select()
                self.switch_twt.configure(text=t("status_enabled", self.current_lang))
            else:
                self.switch_twt.deselect()
                self.switch_twt.configure(text=t("status_disabled", self.current_lang))

            # 3. MU-MIMO (txbf)
            txbf_val = safe_int(first_w.get("txbf", 0))
            if txbf_val in (1, 3):
                self.switch_mumimo.select()
                self.switch_mumimo.configure(text=t("status_enabled", self.current_lang))
            else:
                self.switch_mumimo.deselect()
                self.switch_mumimo.configure(text=t("status_disabled", self.current_lang))

            # 4. Miot Relay (Changkuailian)
            miot_data = self.snapshot.get("miotrelay", {})
            if isinstance(miot_data, dict) and str(miot_data.get("switch", "0")) == "1":
                self.switch_miotrelay.select()
                self.switch_miotrelay.configure(text=t("status_enabled", self.current_lang))
            else:
                self.switch_miotrelay.deselect()
                self.switch_miotrelay.configure(text=t("status_disabled", self.current_lang))

            # 5. Wi-Fi Silence
            silence_data = self.snapshot.get("wifi_silence", {})
            if isinstance(silence_data, dict) and str(silence_data.get("status", "0")) == "1":
                self.switch_wifi_silence.select()
                self.switch_wifi_silence.configure(text=t("status_enabled", self.current_lang))
            else:
                self.switch_wifi_silence.deselect()
                self.switch_wifi_silence.configure(text=t("status_disabled", self.current_lang))

            # 6. Roaming Mesh (Aimesh)
            aimesh_data = self.snapshot.get("aimesh", {})
            if isinstance(aimesh_data, dict):
                m_roam = safe_int(aimesh_data.get("manual_roaming_setting", 0))
                if m_roam == 1:
                    self.switch_roam_manual.select()
                    self.switch_roam_manual.configure(text=t("wifi_adv_roam_manual", self.current_lang))
                else:
                    self.switch_roam_manual.deselect()
                    self.switch_roam_manual.configure(text=t("status_disabled", self.current_lang))

                r1 = aimesh_data.get("roam_rssi_threshold1")
                r2 = aimesh_data.get("roam_rssi_threshold2")
                if r1 is not None and str(r1) != "":
                    self.entry_roam_2g.delete(0, "end")
                    self.entry_roam_2g.insert(0, str(r1))
                if r2 is not None and str(r2) != "":
                    self.entry_roam_5g.delete(0, "end")
                    self.entry_roam_5g.insert(0, str(r2))
        except Exception as e:
            print("Błąd aktualizacji parametrów Wi-Fi:", e)

        # 6. LED
        try:
            if isinstance(led, dict) and "status" in led:
                self.switch_led.select() if str(led.get("status")) == "1" else self.switch_led.deselect()
        except Exception as e:
            print("Błąd aktualizacji LED:", e)

        # 7. Porty i NAT
        try:
            nat_data = snap.get("port_forward", {})
            self._render_nat_tables(nat_data)
        except Exception as e:
            print("Błąd aktualizacji NAT:", e)

        # 8. QoS, DDNS i VPN
        try:
            self._render_qos_vpn(
                qos_data=snap.get("qos", {}),
                ddns_data=snap.get("ddns", {}),
                vpn_data=snap.get("vpn", {}),
                vpn_status=snap.get("vpn_status", {})
            )
        except Exception as e:
            print("Błąd aktualizacji QoS/DDNS/VPN:", e)

        # 9. Porty Fizyczne i Usługi Sprzętowe
        try:
            self._render_ports_tab(
                ps_map=snap.get("ps_map", {}),
                ps_services=snap.get("ps_services", {})
            )
        except Exception as e:
            print("Błąd aktualizacji portów fizycznych:", e)

        # 10. Topologia i Węzły Mesh
        try:
            self._render_mesh_tab()
        except Exception as e:
            print("Błąd aktualizacji topologii Mesh:", e)

        # 11. Czas i Strefa Czasowa
        try:
            st = snap.get("sys_time", {}).get("time", {})
            if st and "hour" in st:
                t_str = f"{st.get('year')}-{safe_int(st.get('month')):02d}-{safe_int(st.get('day')):02d} {safe_int(st.get('hour')):02d}:{safe_int(st.get('min')):02d}:{safe_int(st.get('sec')):02d}"
                tz_str = str(st.get('timezone', 'CST-8') or 'CST-8')
                tz_idx_cur = str(st.get('index', '') or '')
                tz_short = tz_str.split(",")[0]
                self.lbl_sys_time.configure(text=f"{t('tools_time_label', self.current_lang)} {t_str} ({tz_short})")
                if hasattr(self, "combo_tools_tz") and (tz_str or tz_idx_cur):
                    matched = False
                    if tz_idx_cur:
                        for iana, lbl in TZ_DISPLAY_LIST:
                            if TZ_INDEX_MAP.get(iana) == tz_idx_cur:
                                self.combo_tools_tz.set(lbl)
                                matched = True
                                break
                    if not matched:
                        for iana, lbl in TZ_DISPLAY_LIST:
                            posix = TZ_POSIX_MAP.get(iana, "")
                            if posix == tz_str or (tz_str and posix.startswith(tz_str)):
                                self.combo_tools_tz.set(lbl)
                                break
        except Exception as e:
            print("Błąd aktualizacji czasu systemowego:", e)

    def _toggle_autorefresh(self):
        self.auto_refresh_running = self.switch_autorefresh.get() == 1
        if self.auto_refresh_running:
            def loop():
                while self.auto_refresh_running and self.client.connected:
                    self._fetch_data()
                    time.sleep(3)
            threading.Thread(target=loop, daemon=True).start()

    def _export_to_md(self):
        lg = self.current_lang
        if not self.snapshot:
            messagebox.showinfo(t("info_title", lg), "Najpierw połącz się z routerem, aby pobrać konfigurację." if lg == "pl" else "Please connect to the router first to fetch configuration.")
            return

        rname = self.snapshot.get("init_info", {}).get("routername") or "xiaomi_router"
        default_name = f"raport_{rname}_{time.strftime('%Y%m%d_%H%M%S')}.md"
        out_path = filedialog.asksaveasfilename(
            defaultextension=".md",
            initialfile=default_name,
            filetypes=[("Markdown files", "*.md"), ("All files", "*.*")]
        )
        if out_path:
            try:
                export_snapshot_to_markdown(self.snapshot, out_path)
                messagebox.showinfo(t("export_md_succ_title", lg), t("export_md_succ_body", lg).format(path=out_path))
            except Exception as e:
                messagebox.showerror(t("export_md_err_title", lg), t("export_md_err_body", lg).format(err=e))

    def _toggle_led(self):
        if not self.client.connected:
            return
        state = 1 if self.switch_led.get() == 1 else 0
        def run():
            try:
                self.client.set_led(state)
            except Exception as e:
                print("Błąd sterowania LED:", e)
        threading.Thread(target=run, daemon=True).start()

    def _optimize_wifi(self):
        if not self.client.connected:
            return
        lg = self.current_lang
        self.btn_opt_wifi.configure(state="disabled", text=t("opt_wifi_busy_btn", lg))
        if hasattr(self, "frame_opt_progress"):
            self.frame_opt_progress.grid(row=1, column=0, columnspan=2, padx=10, pady=(0, 6), sticky="ew")
        if hasattr(self, "pbar_opt"):
            self.pbar_opt.start()

        def run():
            try:
                res = self.client.scan_wifi_channels(poll_timeout=35)
                if not isinstance(res, dict) or res.get("code") != 0:
                    raise RuntimeError(f"Router response: {res}")
                if res.get("status") != 0:
                    raise RuntimeError("Scan did not finish in time." if lg == "en" else "Skanowanie kanałów nie zakończyło się w limicie czasu.")

                bands = []
                rec_2g = None
                rec_5g = None
                for key, label in [("2G", "2.4 GHz"), ("5G", "5 GHz")]:
                    info = res.get(key)
                    if isinstance(info, dict) and info.get("code") == 0:
                        cc = str(info.get("cchannel", "")).strip()
                        sc = str(info.get("schannel", "")).strip()
                        cscore = info.get("cscore", "-")
                        sscore = info.get("sscore", "-")
                        if cc and cc.lower() != "nil":
                            if sc and sc.lower() != "nil" and sc.isdigit() and sc != "0" and sc != cc:
                                bands.append(
                                    f"- {label}: current ch {cc} (score {cscore}) -> recommended ch {sc} (score {sscore})"
                                    if lg == "en"
                                    else f"- {label}: bieżący kanał {cc} (wynik {cscore}) -> zalecany kanał {sc} (wynik {sscore})"
                                )
                                if key == "2G":
                                    rec_2g = int(sc)
                                elif key == "5G":
                                    rec_5g = int(sc)
                            else:
                                bands.append(
                                    f"- {label}: channel {cc} is already optimal (score {cscore})"
                                    if lg == "en"
                                    else f"- {label}: kanał {cc} jest już optymalny (wynik {cscore})"
                                )
                if "5G" not in res:
                    bands.append(
                        "- 5 GHz: router API does not provide 5 GHz spectrum scan (unchanged)"
                        if lg == "en"
                        else "- 5 GHz: brak skanu tego pasma w API routera (bez zmian)"
                    )

                def on_done():
                    if hasattr(self, "pbar_opt"):
                        self.pbar_opt.stop()
                    if hasattr(self, "frame_opt_progress"):
                        self.frame_opt_progress.grid_forget()
                    self.btn_opt_wifi.configure(state="normal", text=t("wifi_btn_opt", lg))

                    details = "\n".join(bands) if bands else (
                        "Router finished spectrum scan." if lg == "en" else "Router zakończył skanowanie pasma."
                    )
                    if rec_2g is not None or rec_5g is not None:
                        ask = (
                            f"Wi-Fi spectrum scan complete:\n\n{details}\n\n"
                            "Apply recommended channel(s) now? (Wi-Fi will reconnect for ~10s)"
                            if lg == "en"
                            else f"Skanowanie eteru Wi-Fi zakończone:\n\n{details}\n\n"
                            "Czy ustawić zalecany kanał teraz? (Wi-Fi rozłączy się na ok. 10 s)"
                        )
                        if messagebox.askyesno(t("opt_wifi_dlg_title", lg), ask):
                            if rec_2g is not None and str(rec_2g) in WIFI_2G_CHANNELS:
                                self.combo_wifi_ch_2g.set(str(rec_2g))
                            if rec_5g is not None and str(rec_5g) in WIFI_5G_CHANNELS:
                                self.combo_wifi_ch_5g.set(str(rec_5g))
                            self._apply_scanned_wifi_channels(rec_2g, rec_5g)
                    else:
                        msg = (
                            f"Wi-Fi spectrum scan complete:\n\n{details}"
                            if lg == "en"
                            else f"Skanowanie eteru Wi-Fi zakończone:\n\n{details}"
                        )
                        messagebox.showinfo(t("opt_wifi_dlg_title", lg), msg)
                        self._fetch_data_thread()
                self.after(0, on_done)
            except Exception as e:
                def on_err():
                    if hasattr(self, "pbar_opt"):
                        self.pbar_opt.stop()
                    if hasattr(self, "frame_opt_progress"):
                        self.frame_opt_progress.grid_forget()
                    self.btn_opt_wifi.configure(state="normal", text=t("wifi_btn_opt", lg))
                    messagebox.showerror(t("opt_wifi_dlg_title", lg), t("opt_wifi_dlg_err", lg).format(err=e))
                self.after(0, on_err)
        threading.Thread(target=run, daemon=True).start()

    def _apply_scanned_wifi_channels(self, rec_2g=None, rec_5g=None):
        lg = self.current_lang
        bsd = 1 if self.switch_bsd.get() == 1 else 0
        ssid_2g = self.entry_wifi_ssid_common.get().strip() if (bsd == 1 and hasattr(self, "entry_wifi_ssid_common") and self.entry_wifi_ssid_common.get().strip()) else self.entry_wifi_ssid_2g.get().strip()
        pwd_2g = self.entry_wifi_pwd_common.get().strip() if (bsd == 1 and hasattr(self, "entry_wifi_pwd_common") and self.entry_wifi_pwd_common.get().strip()) else self.entry_wifi_pwd_2g.get().strip()
        # Zachowaj surowy kod szyfrowania z aktualnej migawki routera, aby zmiana kanału nigdy nie zmieniła szyfrowania
        raw_enc_map = {}
        for idx, w in enumerate(self.snapshot.get("wifi_detail", {}).get("info", []) or []):
            w_idx = safe_int(w.get("wifiIndex", idx + 1))
            if w.get("encryption"):
                raw_enc_map[w_idx] = str(w.get("encryption"))
        enc_2g = raw_enc_map.get(1) or enc_to_code(self.combo_wifi_enc_common.get() if (bsd == 1 and hasattr(self, "combo_wifi_enc_common")) else self.combo_wifi_enc_2g.get())
        ssid_5g = ssid_2g if bsd == 1 else self.entry_wifi_ssid_5g.get().strip()
        pwd_5g = pwd_2g if bsd == 1 else self.entry_wifi_pwd_5g.get().strip()
        enc_5g = (raw_enc_map.get(2) or enc_2g) if bsd == 1 else (raw_enc_map.get(2) or enc_to_code(self.combo_wifi_enc_5g.get()))
        ch_2g = rec_2g if rec_2g is not None else channel_to_code(self.combo_wifi_ch_2g.get())
        ch_5g = rec_5g if rec_5g is not None else channel_to_code(self.combo_wifi_ch_5g.get())
        wifi1 = {
            "ssid": ssid_2g, "pwd": pwd_2g, "encryption": enc_2g,
            "channel": ch_2g, "bandwidth": bandwidth_to_code(self.combo_wifi_bw_2g.get()),
            "txpwr": WIFI_TX_MAP_CODE.get(self.combo_wifi_tx_2g.get(), "max"),
            "hidden": 1 if self.switch_wifi_hidden_2g.get() == 1 else 0,
            "on": 1 if self.switch_wifi_on_2g.get() == 1 else 0,
        }
        wifi2 = {
            "ssid": ssid_5g, "pwd": pwd_5g, "encryption": enc_5g,
            "channel": ch_5g, "bandwidth": bandwidth_to_code(self.combo_wifi_bw_5g.get()),
            "txpwr": WIFI_TX_MAP_CODE.get(self.combo_wifi_tx_5g.get(), "max"),
            "hidden": 1 if self.switch_wifi_hidden_5g.get() == 1 else 0,
            "on": 1 if self.switch_wifi_on_5g.get() == 1 else 0,
        }
        def run_save():
            try:
                r = self.client.set_all_wifi(bsd=bsd, wifi1=wifi1, wifi2=wifi2)
                if isinstance(r, dict) and r.get("code") == 0:
                    self.after(0, lambda: messagebox.showinfo(
                        t("opt_wifi_dlg_title", lg),
                        "Recommended Wi-Fi channel(s) applied!" if lg == "en" else "Zastosowano zalecane kanały Wi-Fi!"
                    ))
                    time.sleep(2)
                    self._fetch_data_thread()
                else:
                    resp_msg = str(r.get("msg") or r) if isinstance(r, dict) else str(r)
                    self.after(0, lambda m=resp_msg: messagebox.showerror(t("err_title", lg), m))
            except Exception as exc:
                err_msg = str(exc) or type(exc).__name__
                self.after(0, lambda m=err_msg: messagebox.showerror(t("err_title", lg), m))
        threading.Thread(target=run_save, daemon=True).start()

    def _reboot_router(self):
        if not self.client.connected:
            return
        lg = self.current_lang
        if messagebox.askyesno(t("reboot_title", lg), t("reboot_prompt", lg)):
            def run():
                try:
                    self.client.reboot()
                    messagebox.showinfo(t("reboot_title", lg), t("reboot_sent", lg))
                except Exception as e:
                    messagebox.showerror(t("err_title", lg), t("reboot_err", lg).format(err=e))
            threading.Thread(target=run, daemon=True).start()

    def _get_router_role_info(self):
        init = self.snapshot.get("init_info", {}) if isinstance(self.snapshot, dict) else {}
        topo = self.snapshot.get("topo_graph", {}) if isinstance(self.snapshot, dict) else {}
        graph = topo.get("graph", {}) if isinstance(topo, dict) else {}
        leafs = graph.get("leafs") or graph.get("re") or []
        has_satellites = bool(leafs) or any(safe_int(d.get("isap", 0)) > 0 for d in getattr(self, "raw_devices", []))
        netmode = safe_int(init.get("netmode", graph.get("mode", 0)), 0)
        if netmode in (1, 2, 3, 4):
            role = "SATELITA / AP"
        elif has_satellites:
            role = "MASTER (MESH)"
        else:
            role = "MASTER / STANDALONE"
        model = clean_model_name(init.get("displayName") or init.get("hardware") or "Xiaomi Router")
        rname = init.get("routername") or graph.get("name") or "-"
        return role, model, rname, self.client.ip

    def _prompt_factory_reset(self):
        if not self.client.connected:
            return

        lg = self.current_lang
        is_en = (lg == "en")
        role, model, rname, ip = self._get_router_role_info()

        dlg = ctk.CTkToplevel(self)
        dlg.title(t("reset_warn_title", lg))
        dlg.geometry("500x360")
        dlg.resizable(False, False)
        dlg.grab_set()

        banner = ctk.CTkFrame(dlg, fg_color="#7f1d1d", corner_radius=8, border_width=2, border_color="#ef4444")
        banner.pack(fill="x", padx=20, pady=(18, 12))
        ctk.CTkLabel(
            banner,
            text=f"⚠  {role}",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#fecaca"
        ).pack(pady=(10, 2))
        ctk.CTkLabel(
            banner,
            text=f"{model}  |  '{rname}'  |  IP: {ip}",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#ffffff"
        ).pack(pady=(0, 10))

        warn_txt = (
            "WARNING: This will erase all router settings, Wi-Fi networks and DHCP leases!\n"
            "Make sure you are NOT wiping your main production router by mistake."
            if is_en else
            "UWAGA: Ta operacja usunie wszystkie ustawienia, sieci Wi-Fi i konfigurację tego routera!\n"
            "Upewnij się, że NIE resetujesz przypadkiem głównego routera produkcyjnego."
        )
        ctk.CTkLabel(dlg, text=warn_txt, justify="left", wraplength=455, text_color="#fca5a5").pack(anchor="w", padx=20, pady=(0, 10))

        ctk.CTkLabel(dlg, text=t("reset_input_body", lg), justify="left", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=20, pady=(4, 4))
        e_conf = ctk.CTkEntry(dlg, placeholder_text="RESET", width=460)
        e_conf.pack(padx=20, pady=(0, 14))
        e_conf.focus_set()

        btn_row = ctk.CTkFrame(dlg, fg_color="transparent")
        btn_row.pack(fill="x", padx=20, pady=(0, 15))

        def do_confirm():
            if e_conf.get().strip() != "RESET":
                messagebox.showinfo(t("info_title", lg), t("reset_cancelled", lg), parent=dlg)
                return
            dlg.destroy()

            def run():
                try:
                    res = self.client.factory_reset(format_data=1)
                    if isinstance(res, dict) and res.get("code") not in (0, None):
                        self.after(0, lambda r=res: messagebox.showerror(t("err_title", lg), f"Router rejected reset: {r}"))
                        return
                    note = (
                        "\n\nFull factory reset (?format=1) sent. After ~60-90s the router will boot in factory state "
                        "(default password: admin). You can then run the First-Time Setup Wizard."
                        if is_en else
                        "\n\nWysłano pełny reset fabryczny (?format=1). Po ok. 60-90 s router uruchomi się w stanie fabrycznym "
                        "(domyślne hasło: admin). Możesz wtedy użyć Kreatora Pierwszej Konfiguracji."
                    )
                    self.after(0, lambda: self._reset_disconnected_state(clear_password=True))
                    self.after(0, lambda: messagebox.showinfo(t("info_title", lg), t("reset_in_progress", lg) + note))
                except Exception as e:
                    self.after(0, lambda err=e: messagebox.showerror(t("err_title", lg), f"{err}"))
            threading.Thread(target=run, daemon=True).start()

        ctk.CTkButton(btn_row, text=t("btn_cancel", lg), fg_color="#475569", hover_color="#334155", width=130, command=dlg.destroy).pack(side="left")
        ctk.CTkButton(btn_row, text=("Confirm RESET" if is_en else "Potwierdź RESET"), fg_color="#dc2626", hover_color="#991b1b", font=ctk.CTkFont(weight="bold"), width=180, command=do_confirm).pack(side="right")

    def _action_restart_pppoe(self):
        if not self.client.connected:
            return
        lg = self.current_lang
        if messagebox.askyesno(t("wan_pppoe_restart_title", lg), t("wan_pppoe_restart_prompt", lg)):
            def run():
                try:
                    res = self.client.pppoe_restart()
                    if res.get("code") == 0:
                        messagebox.showinfo(t("wan_pppoe_restart_title", lg), t("wan_pppoe_restart_sent", lg))
                        self._fetch_data_thread()
                    else:
                        messagebox.showwarning(t("wan_pppoe_restart_title", lg), f"Router: {res}")
                except Exception as e:
                    messagebox.showerror(t("err_title", lg), f"{e}")
            threading.Thread(target=run, daemon=True).start()

    def _action_clone_mac(self):
        if not self.client.connected:
            return
        lg = self.current_lang
        new_mac = self.entry_clone_mac.get().strip()
        prompt = t("wan_clone_mac_prompt", lg).format(mac=new_mac or t("wan_clone_mac_factory", lg))
        if not messagebox.askyesno(t("wan_clone_mac_title", lg), prompt):
            return
        def run():
            try:
                res = self.client.clone_mac(new_mac)
                if res.get("code") == 0:
                    messagebox.showinfo(t("wan_clone_mac_title", lg), t("wan_clone_mac_succ", lg))
                    self._fetch_data_thread()
                else:
                    messagebox.showwarning(t("notice_title", lg), f"Router: {res}")
            except Exception as e:
                messagebox.showerror(t("err_title", lg), f"{e}")
        threading.Thread(target=run, daemon=True).start()

    def _action_save_wan(self):
        if not self.client.connected:
            return

        mode = str(self.seg_wan_mode.get()).lower()
        wan_type = "pppoe" if "pppoe" in mode else ("static" if "stat" in mode else "dhcp")
        mtu_str = self.entry_wan_mtu.get().strip()
        if not mtu_str:
            mtu_str = "1472"
        lg = self.current_lang
        try:
            mtu_val = int(mtu_str)
            if not (576 <= mtu_val <= 1500):
                raise ValueError()
        except ValueError:
            messagebox.showerror(t("err_title", lg), t("wan_err_mtu", lg))
            return

        params = {"mtu": str(mtu_val)}
        if self.switch_wan_custom_dns.get() == 1:
            params["peerdns"] = "0"
            params["dns1"] = self.entry_wan_dns1.get().strip()
            params["dns2"] = self.entry_wan_dns2.get().strip()
        else:
            params["peerdns"] = "1"

        if wan_type == "pppoe":
            u = self.entry_wan_user.get().strip()
            p = self.entry_wan_pwd.get().strip()
            if not u:
                messagebox.showerror(t("err_title", lg), t("wan_err_user", lg))
                return
            params["pppoeName"] = u
            params["pppoePwd"] = p
        elif wan_type == "static":
            s_ip = self.entry_wan_static_ip.get().strip()
            s_mask = self.entry_wan_static_mask.get().strip()
            s_gw = self.entry_wan_static_gw.get().strip()
            if not s_ip or not s_mask or not s_gw:
                messagebox.showerror(t("err_title", lg), t("wan_err_static", lg))
                return
            params["staticIp"] = s_ip
            params["staticMask"] = s_mask
            params["staticGateway"] = s_gw

        if not messagebox.askyesno(t("wan_save_confirm_title", lg), t("wan_save_confirm_prompt", lg)):
            return

        def run():
            try:
                res = self.client.set_wan(wan_type, **params)
                if res.get("code") == 0:
                    messagebox.showinfo(t("succ_title", lg), t("wan_save_succ", lg))
                    time.sleep(2)
                    self._fetch_data_thread()
                else:
                    messagebox.showwarning("Uwaga", f"Odpowiedź routera: {res}")
            except Exception as e:
                messagebox.showerror("Błąd", f"Błąd zapisu WAN: {e}")
        threading.Thread(target=run, daemon=True).start()

    def _action_toggle_dev_wan(self, mac: str, current_allow: bool):
        if not self.client.connected:
            return
        lg = self.current_lang
        new_allow = not current_allow
        action_name = t("dev_acc_unblock" if new_allow else "dev_acc_block", lg)
        prompt = t("dev_acc_prompt", lg).format(action=action_name, mac=mac)
        if not messagebox.askyesno(t("dev_acc_title", lg), prompt):
            return
        def run():
            try:
                res = self.client.set_device_wan_access(mac, new_allow)
                if res.get("code") == 0:
                    messagebox.showinfo(t("dev_acc_title", lg), t("dev_acc_succ", lg).format(mac=mac))
                    self._fetch_data_thread()
                else:
                    messagebox.showwarning(t("notice_title", lg), f"Router: {res}")
            except Exception as e:
                messagebox.showerror(t("err_title", lg), t("dev_acc_err", lg).format(err=e))
        threading.Thread(target=run, daemon=True).start()

    def _action_delete_mac_bind(self, mac: str, name: str):
        if not self.client.connected:
            return
        lg = self.current_lang
        prompt = t("lan_del_bind_prompt", lg).format(name=name, mac=mac)
        if not messagebox.askyesno(t("lan_del_bind_title", lg), prompt):
            return
        def run():
            try:
                res = self.client.remove_mac_bind(mac)
                if res.get("code") == 0:
                    messagebox.showinfo(t("succ_title", lg), t("lan_del_bind_succ", lg).format(name=name))
                    self._fetch_data_thread()
                else:
                    messagebox.showwarning(t("notice_title", lg), f"Router: {res}")
            except Exception as e:
                messagebox.showerror(t("err_title", lg), f"{e}")
        threading.Thread(target=run, daemon=True).start()

    def _action_save_lan_ip(self):
        if not self.client.connected:
            return
        lg = self.current_lang
        ip = self.entry_lan_ip.get().strip()
        mask = self.entry_lan_mask.get().strip()
        if not ip or not mask:
            messagebox.showerror(t("err_title", lg), t("lan_save_ip_err_fields", lg))
            return
        prompt = t("lan_save_ip_prompt", lg).format(ip=ip)
        if not messagebox.askyesno(t("lan_save_ip_title", lg), prompt):
            return
        def run():
            try:
                res = self.client.set_lan_ip(ip, mask)
                if res.get("code") == 0:
                    messagebox.showinfo(t("succ_title", lg), t("lan_save_ip_succ", lg).format(ip=ip))
                else:
                    messagebox.showwarning("Uwaga", f"Odpowiedź routera: {res}")
            except Exception as e:
                messagebox.showerror("Błąd", f"Błąd zapisu IP LAN: {e}")
        threading.Thread(target=run, daemon=True).start()

    def _action_save_dhcp(self):
        if not self.client.connected:
            return
        start = safe_int(self.entry_dhcp_start.get().strip() or "5")
        limit = safe_int(self.entry_dhcp_limit.get().strip() or "250")
        lease_raw = self.entry_dhcp_lease.get().strip() or "720"
        dns1 = self.entry_dhcp_dns1.get().strip()
        dns2 = self.entry_dhcp_dns2.get().strip()

        # Walidacja: wyłącznie czysta liczba minut
        m = re.match(r"^(\d+)$", lease_raw)
        if not m:
            messagebox.showerror("Błąd", "Czas dzierżawy musi być liczbą całkowitą minut (np. 720 dla 12 godzin, 1440 dla 24 godzin).")
            return

        lease_mins = int(m.group(1))
        if lease_mins < 2:
            lease_mins = 2
        elif lease_mins > 2880:
            lease_mins = 2880

        clean_lease = f"{lease_mins}m"
        end_calc = min(254, start + limit - 1)
        lan_pfx = ".".join(self.client.ip.split(".")[:3])

        msg_confirm = (
            f"Czy na pewno chcesz zapisać nowe parametry serwera DHCP?\n\n"
            f"- Zakres puli IP: {lan_pfx}.{start} do {lan_pfx}.{end_calc} (limit: {limit})\n"
            f"- Czas dzierżawy: {lease_mins} minut ({clean_lease})\n"
            f"- Lokalny DNS 1: {dns1 or 'Domyślny'}\n"
            f"- Lokalny DNS 2: {dns2 or 'Brak'}"
        )

        if not messagebox.askyesno("Zapis DHCP", msg_confirm):
            return

        def run():
            try:
                res = self.client.set_lan_dhcp(
                    start=start,
                    limit=limit,
                    end=end_calc,
                    leasetime=clean_lease,
                    dns1=dns1,
                    dns2=dns2
                )
                code = res.get("code")
                if code == 0:
                    self.after(0, lambda: (messagebox.showinfo("Sukces", f"Pomyślnie zaktualizowano parametry serwera DHCP!\nCzas dzierżawy: {lease_mins} minut ({clean_lease})"), self._fetch_data_thread()))
                elif code == 1537:
                    self.after(0, lambda: messagebox.showwarning("Błąd parametrów (1537)", f"Router zgłosił błąd parametrów (kod 1537).\nOdpowiedź: {res}"))
                elif code == 1535:
                    self.after(0, lambda: messagebox.showwarning("Błąd zakresu (1535)", f"Nieprawidłowy zakres czasu dzierżawy (dozwolone 2-2880 minut) lub pula IP wykracza poza 254.\nOdpowiedź: {res}"))
                else:
                    self.after(0, lambda: messagebox.showwarning("Uwaga", f"Odpowiedź routera (kod {code}):\n{res}"))
            except Exception as e:
                self.after(0, lambda: messagebox.showerror("Błąd", f"Błąd zapisu DHCP: {e}"))
        threading.Thread(target=run, daemon=True).start()

    def _check_wizard_state(self):
        lg = self.current_lang
        def run():
            try:
                info = self.client.probe()
                inited = info.get("inited", 1)
                if inited == 0:
                    txt = t("wiz_s1_factory_yes", lg) if "wiz_s1_factory_yes" in i18n.TRANSLATIONS[lg] else ("Router is in factory state (inited=0).\nMożna rozpocząć konfigurację od zera!" if lg != "en" else "Router is in factory state (inited=0).\nYou can start fresh configuration!")
                    self.after(0, lambda: self.lbl_wiz_status.configure(text=txt, text_color="#22c55e"))
                else:
                    txt = t("wiz_s1_factory_no", lg).format(inited=inited) if "wiz_s1_factory_no" in i18n.TRANSLATIONS[lg] else (f"Router is already initialized (inited={inited}).\nSetup wizard not required." if lg == "en" else f"Router jest już skonfigurowany (inited={inited}).\nKreator fabryczny nie jest wymagany.")
                    self.after(0, lambda: self.lbl_wiz_status.configure(text=txt, text_color="#eab308"))
            except Exception as e:
                err_prefix = "Check error:" if lg == "en" else "Błąd sprawdzania:"
                self.after(0, lambda: self.lbl_wiz_status.configure(text=f"{err_prefix} {e}", text_color="#ef4444"))
        threading.Thread(target=run, daemon=True).start()

def main():
    app = MiWiFiManagerApp()
    app.mainloop()


if __name__ == "__main__":
    main()
