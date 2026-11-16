"""Moduł Kreatora Pierwszej Konfiguracji (Quick Setup Wizard) dla Xiaomi Router Manager.
Umożliwia 4-krokową, intuicyjną konfigurację nowego lub zresetowanego routera w języku polskim lub angielskim.
"""

import threading
import customtkinter as ctk
from tkinter import messagebox
from miwifi_core import MiWiFiClient
import i18n
try:
    from version import APP_VERSION
except ImportError:
    APP_VERSION = "1.0.0"


def safe_int(val, default=0):
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return default


class SetupWizardDialog(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.parent = parent
        self.lang = getattr(parent, "current_lang", "pl")
        self.title(f"{i18n.t('wiz_title', self.lang)} v{APP_VERSION}")
        self.geometry("640x720")
        self.minsize(580, 660)
        self.resizable(False, False)
        self.grab_set()

        self.current_step = 1
        self.probed_model = ""
        self.is_factory_reset = False

        # Header
        hdr = ctk.CTkFrame(self, fg_color="#1e293b", corner_radius=0, height=75)
        hdr.pack(fill="x")
        self.lbl_hdr_title = ctk.CTkLabel(hdr, text=i18n.t("wiz_title", self.lang), font=ctk.CTkFont(size=16, weight="bold"), text_color="#38bdf8")
        self.lbl_hdr_title.pack(anchor="w", padx=20, pady=(12, 2))
        self.lbl_hdr_sub = ctk.CTkLabel(hdr, text=i18n.t("wiz_subtitle", self.lang), font=ctk.CTkFont(size=11), text_color="#94a3b8")
        self.lbl_hdr_sub.pack(anchor="w", padx=20, pady=(0, 12))

        # Steps Progress Indicator
        self.prog_bar = ctk.CTkFrame(self, fg_color="#0f172a", height=38)
        self.prog_bar.pack(fill="x")
        self.step_badges = []
        for i, step_k in enumerate(["wiz_step1_badge", "wiz_step2_badge", "wiz_step3_badge", "wiz_step4_badge"]):
            lbl = ctk.CTkLabel(self.prog_bar, text=i18n.t(step_k, self.lang), font=ctk.CTkFont(size=11, weight="bold"), text_color="#64748b")
            lbl.pack(side="left", expand=True, pady=6)
            self.step_badges.append(lbl)

        # Main Container
        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.pack(fill="both", expand=True, padx=20, pady=15)
        self.container.grid_columnconfigure(0, weight=1)
        self.container.grid_rowconfigure(0, weight=1)

        # Bottom Bar
        bot_bar = ctk.CTkFrame(self, fg_color="#1e293b", height=54)
        bot_bar.pack(fill="x", side="bottom")

        self.btn_back = ctk.CTkButton(bot_bar, text=i18n.t("wiz_back", self.lang), fg_color="#475569", hover_color="#334155", width=110, command=self._prev_step)
        self.btn_back.pack(side="left", padx=20, pady=10)

        self.btn_next = ctk.CTkButton(bot_bar, text=i18n.t("wiz_next", self.lang), fg_color="#2563eb", hover_color="#1d4ed8", width=120, command=self._next_step)
        self.btn_next.pack(side="right", padx=20, pady=10)

        self.btn_finish = ctk.CTkButton(bot_bar, text=i18n.t("wiz_finish", self.lang), fg_color="#16a34a", hover_color="#15803d", width=240, command=self._apply_all)

        # Steps frames
        self.step_frames = []
        self._build_step1()
        self._build_step2()
        self._build_step3()
        self._build_step4()

        self._show_step(1)

    def _update_indicators(self):
        for idx, lbl in enumerate(self.step_badges):
            if idx + 1 == self.current_step:
                lbl.configure(text_color="#38bdf8")
            elif idx + 1 < self.current_step:
                lbl.configure(text_color="#22c55e")
            else:
                lbl.configure(text_color="#64748b")

    def _show_step(self, step: int):
        self.current_step = step
        for idx, f in enumerate(self.step_frames):
            if idx + 1 == step:
                f.grid(row=0, column=0, sticky="nsew")
            else:
                f.grid_forget()

        self._update_indicators()

        if step == 1:
            self.btn_back.configure(state="disabled")
            self.btn_next.pack(side="right", padx=20, pady=10)
            self.btn_finish.pack_forget()
        elif step == 4:
            self.btn_back.configure(state="normal")
            self.btn_next.pack_forget()
            self.btn_finish.pack(side="right", padx=20, pady=10)
            self._update_summary()
        else:
            self.btn_back.configure(state="normal")
            self.btn_next.pack(side="right", padx=20, pady=10)
            self.btn_finish.pack_forget()

    def _next_step(self):
        if self.current_step == 1:
            pwd = self.e_pwd.get().strip()
            if not pwd:
                title = "Password Required" if self.lang == "en" else "Brak hasła"
                msg = "Please enter administrator password to configure the router." if self.lang == "en" else "Wprowadź hasło administratora do konfiguracji routera."
                messagebox.showwarning(title, msg, parent=self)
                return
        if self.current_step == 3:
            w_pwd = self.e_wifi_pwd.get().strip()
            if len(w_pwd) < 8:
                title = "Wi-Fi Password Too Short" if self.lang == "en" else "Krótkie hasło Wi-Fi"
                msg = "Wi-Fi password must be at least 8 characters long." if self.lang == "en" else "Hasło do sieci Wi-Fi musi mieć co najmniej 8 znaków."
                messagebox.showwarning(title, msg, parent=self)
                return
        if self.current_step < 4:
            self._show_step(self.current_step + 1)

    def _prev_step(self):
        if self.current_step > 1:
            self._show_step(self.current_step - 1)

    # --- Krok 1: Weryfikacja i autoryzacja ---
    def _build_step1(self):
        f = ctk.CTkFrame(self.container, fg_color="transparent")
        self.step_frames.append(f)

        ctk.CTkLabel(f, text=i18n.t("wiz_step1_h", self.lang), font=ctk.CTkFont(size=15, weight="bold")).pack(anchor="w", pady=(0, 2))
        ctk.CTkLabel(f, text=i18n.t("wiz_step1_sub", self.lang), font=ctk.CTkFont(size=12), text_color="#94a3b8").pack(anchor="w", pady=(0, 15))

        # IP Box
        f_ip = ctk.CTkFrame(f)
        f_ip.pack(fill="x", pady=6)
        ctk.CTkLabel(f_ip, text=i18n.t("wiz_step1_ip", self.lang), width=180, anchor="w").pack(side="left", padx=15, pady=10)
        self.e_ip = ctk.CTkEntry(f_ip, width=150)
        parent_ip = getattr(self.parent.client, "ip", "192.168.31.1")
        self.e_ip.insert(0, parent_ip)
        self.e_ip.pack(side="left", padx=5)

        btn_probe = ctk.CTkButton(f_ip, text=i18n.t("wiz_step1_btn_probe", self.lang), width=160, fg_color="#0284c7", hover_color="#0369a1", command=self._probe_router)
        btn_probe.pack(side="right", padx=15)

        # Status probe box
        self.box_probe = ctk.CTkFrame(f, fg_color="#18202f")
        self.box_probe.pack(fill="x", pady=10)
        self.lbl_probe_status = ctk.CTkLabel(self.box_probe, text=i18n.t("wiz_probe_hint", self.lang), text_color="#94a3b8", justify="left")
        self.lbl_probe_status.pack(padx=15, pady=12, anchor="w")

        # Hasło administratora
        f_pwd = ctk.CTkFrame(f)
        f_pwd.pack(fill="x", pady=6)
        ctk.CTkLabel(f_pwd, text=i18n.t("wiz_step1_pwd", self.lang), width=180, anchor="w").pack(side="left", padx=15, pady=10)
        self.e_pwd = ctk.CTkEntry(f_pwd, width=220, show="•", placeholder_text=i18n.t("pwd_placeholder", self.lang))
        self.e_pwd.pack(side="left", padx=5)
        
        parent_pwd = getattr(self.parent, "auth_entry", None)
        if parent_pwd and parent_pwd.get():
            self.e_pwd.insert(0, parent_pwd.get())

        ctk.CTkLabel(f, text=i18n.t("wiz_step1_pwd_hint", self.lang), font=ctk.CTkFont(size=11), text_color="#64748b").pack(anchor="w", padx=5, pady=(2, 0))

    def _probe_router(self):
        target_ip = self.e_ip.get().strip()
        self.lbl_probe_status.configure(text=i18n.t("wiz_connecting", self.lang).format(ip=target_ip), text_color="#eab308")

        def run():
            cli = MiWiFiClient(target_ip)
            try:
                info = cli.probe()
                model = info.get("displayName") or info.get("hardware") or "Xiaomi Router"
                rname = info.get("routername") or ""
                init_state = info.get("init", True)
                self.probed_model = model
                self.is_factory_reset = not init_state

                model_lbl = "Detected router" if self.lang == "en" else "Wykryto router"
                ip_lbl = "IP Address" if self.lang == "en" else "Adres IP"
                rom_lbl = "ROM Version" if self.lang == "en" else "Wersja ROM"
                status_txt = f"✔ {model_lbl}: {model} ({rname})\n{ip_lbl}: {target_ip}  |  {rom_lbl}: {info.get('romversion', '-')}\n"
                if self.is_factory_reset:
                    status_txt += i18n.t("wiz_status_factory", self.lang)
                else:
                    status_txt += i18n.t("wiz_status_initialized", self.lang)

                self.after(0, lambda: self.lbl_probe_status.configure(text=status_txt, text_color="#22c55e"))
            except Exception as e:
                self.after(0, lambda: self.lbl_probe_status.configure(text=i18n.t("wiz_err_connect", self.lang).format(ip=target_ip, err=e), text_color="#ef4444"))

        threading.Thread(target=run, daemon=True).start()

    # --- Krok 2: WAN Internet ---
    def _build_step2(self):
        f = ctk.CTkFrame(self.container, fg_color="transparent")
        self.step_frames.append(f)

        ctk.CTkLabel(f, text=i18n.t("wiz_step2_h", self.lang), font=ctk.CTkFont(size=15, weight="bold")).pack(anchor="w", pady=(0, 2))
        ctk.CTkLabel(f, text=i18n.t("wiz_step2_sub", self.lang), font=ctk.CTkFont(size=12), text_color="#94a3b8").pack(anchor="w", pady=(0, 15))

        f_mode = ctk.CTkFrame(f)
        f_mode.pack(fill="x", pady=6)
        ctk.CTkLabel(f_mode, text=i18n.t("wiz_step2_mode", self.lang), width=180, anchor="w").pack(side="left", padx=15, pady=10)
        self.combo_wan_mode = ctk.CTkComboBox(
            f_mode,
            values=[i18n.t("wiz_step2_dhcp", self.lang), i18n.t("wiz_step2_pppoe", self.lang), i18n.t("wiz_step2_static", self.lang)],
            width=320, command=self._on_wan_mode_change
        )
        self.combo_wan_mode.set(i18n.t("wiz_step2_dhcp", self.lang))
        self.combo_wan_mode.pack(side="left", padx=5)

        # Pola PPPoE
        self.f_pppoe = ctk.CTkFrame(f)
        
        f_u = ctk.CTkFrame(self.f_pppoe, fg_color="transparent")
        f_u.pack(fill="x", padx=15, pady=4)
        ctk.CTkLabel(f_u, text=i18n.t("wiz_step2_user", self.lang), width=160, anchor="w").pack(side="left")
        self.e_pppoe_user = ctk.CTkEntry(f_u, width=220)
        self.e_pppoe_user.pack(side="right")

        f_p = ctk.CTkFrame(self.f_pppoe, fg_color="transparent")
        f_p.pack(fill="x", padx=15, pady=4)
        ctk.CTkLabel(f_p, text=i18n.t("wiz_step2_pwd", self.lang), width=160, anchor="w").pack(side="left")
        self.e_pppoe_pwd = ctk.CTkEntry(f_p, width=220, show="•")
        self.e_pppoe_pwd.pack(side="right")

        # WAN MTU Box
        f_mtu = ctk.CTkFrame(f)
        f_mtu.pack(fill="x", pady=6)
        ctk.CTkLabel(f_mtu, text=i18n.t("wiz_step2_mtu", self.lang), width=180, anchor="w").pack(side="left", padx=15, pady=10)
        mtu_vals = [i18n.t("wiz_mtu_fiber", self.lang), i18n.t("wiz_mtu_pppoe", self.lang), i18n.t("wiz_mtu_std", self.lang)]
        self.combo_mtu = ctk.CTkComboBox(f_mtu, values=mtu_vals, width=200)
        self.combo_mtu.set(mtu_vals[0])
        self.combo_mtu.pack(side="left", padx=5)

        ctk.CTkLabel(f, text=i18n.t("wiz_step2_mtu_hint", self.lang), font=ctk.CTkFont(size=11), text_color="#64748b").pack(anchor="w", padx=5, pady=(2, 0))

    def _on_wan_mode_change(self, choice):
        mtu_vals = [i18n.t("wiz_mtu_fiber", self.lang), i18n.t("wiz_mtu_pppoe", self.lang), i18n.t("wiz_mtu_std", self.lang)]
        if "PPPoE" in choice:
            self.f_pppoe.pack(fill="x", pady=6)
            self.combo_mtu.set(mtu_vals[1])
        else:
            self.f_pppoe.pack_forget()
            if "1492" in self.combo_mtu.get():
                self.combo_mtu.set(mtu_vals[0])

    # --- Krok 3: Wi-Fi ---
    def _build_step3(self):
        f = ctk.CTkFrame(self.container, fg_color="transparent")
        self.step_frames.append(f)

        ctk.CTkLabel(f, text=i18n.t("wiz_step3_h", self.lang), font=ctk.CTkFont(size=15, weight="bold")).pack(anchor="w", pady=(0, 2))
        ctk.CTkLabel(f, text=i18n.t("wiz_step3_sub", self.lang), font=ctk.CTkFont(size=12), text_color="#94a3b8").pack(anchor="w", pady=(0, 15))

        f_smart = ctk.CTkFrame(f)
        f_smart.pack(fill="x", pady=6)
        self.sw_smart = ctk.CTkSwitch(f_smart, text=i18n.t("wiz_step3_smart", self.lang))
        self.sw_smart.select()
        self.sw_smart.pack(padx=15, pady=10, anchor="w")

        f_ssid = ctk.CTkFrame(f)
        f_ssid.pack(fill="x", pady=6)
        ctk.CTkLabel(f_ssid, text=i18n.t("wiz_step3_ssid", self.lang), width=180, anchor="w").pack(side="left", padx=15, pady=10)
        self.e_wifi_ssid = ctk.CTkEntry(f_ssid, width=250)
        self.e_wifi_ssid.insert(0, "Xiaomi_Home_WiFi")
        self.e_wifi_ssid.pack(side="left", padx=5)

        f_wpwd = ctk.CTkFrame(f)
        f_wpwd.pack(fill="x", pady=6)
        ctk.CTkLabel(f_wpwd, text=i18n.t("wiz_step3_pwd", self.lang), width=180, anchor="w").pack(side="left", padx=15, pady=10)
        self.e_wifi_pwd = ctk.CTkEntry(f_wpwd, width=250, show="•")
        self.e_wifi_pwd.insert(0, "12345678")
        self.e_wifi_pwd.pack(side="left", padx=5)

        ctk.CTkLabel(f, text=i18n.t("wiz_step3_pwd_hint", self.lang), font=ctk.CTkFont(size=11), text_color="#64748b").pack(anchor="w", padx=5, pady=(2, 10))

        # Wi-Fi 7 i TWT
        f_adv = ctk.CTkFrame(f, fg_color="#18202f")
        f_adv.pack(fill="x", pady=6)
        self.sw_mlo = ctk.CTkSwitch(f_adv, text=i18n.t("wiz_step3_mlo", self.lang))
        self.sw_mlo.select()
        self.sw_mlo.pack(padx=15, pady=8, anchor="w")

        self.sw_twt = ctk.CTkSwitch(f_adv, text=i18n.t("wiz_step3_twt", self.lang))
        self.sw_twt.select()
        self.sw_twt.pack(padx=15, pady=(0, 8), anchor="w")

    # --- Krok 4: Podsumowanie i Uruchomienie ---
    def _build_step4(self):
        f = ctk.CTkFrame(self.container, fg_color="transparent")
        self.step_frames.append(f)

        ctk.CTkLabel(f, text=i18n.t("wiz_step4_h", self.lang), font=ctk.CTkFont(size=15, weight="bold")).pack(anchor="w", pady=(0, 2))
        ctk.CTkLabel(f, text=i18n.t("wiz_step4_sub", self.lang), font=ctk.CTkFont(size=12), text_color="#94a3b8").pack(anchor="w", pady=(0, 15))

        self.box_summary = ctk.CTkFrame(f, fg_color="#18202f")
        self.box_summary.pack(fill="both", expand=True, pady=6)

        self.lbl_sum_text = ctk.CTkLabel(self.box_summary, text="", justify="left", font=ctk.CTkFont(size=13))
        self.lbl_sum_text.pack(padx=20, pady=20, anchor="w")

        self.lbl_apply_status = ctk.CTkLabel(f, text="", font=ctk.CTkFont(size=13, weight="bold"))
        self.lbl_apply_status.pack(pady=10)

    def _update_summary(self):
        m_txt = self.combo_wan_mode.get()
        mtu_raw = self.combo_mtu.get().split()[0]
        is_en = (self.lang == "en")
        on_txt = "ENABLED" if is_en else "WŁĄCZONY"
        off_txt = "DISABLED" if is_en else "WYŁĄCZONY"
        on_f_txt = "ENABLED" if is_en else "WŁĄCZONE"
        off_f_txt = "DISABLED" if is_en else "WYŁĄCZONE"
        sum_txt = (
            f"📌 {'Router IP Address' if is_en else 'Adres IP Routera'}: {self.e_ip.get().strip()}\n"
            f"📌 {i18n.t('wiz_step1_pwd', self.lang)}: {'*' * len(self.e_pwd.get().strip())}\n\n"
            f"🌐 {i18n.t('wiz_step2_mode', self.lang)}: {m_txt}\n"
            f"🌐 {'WAN MTU Unit' if is_en else 'Jednostka MTU WAN'}: {mtu_raw}\n\n"
            f"📶 {i18n.t('wiz_step3_ssid', self.lang)}: {self.e_wifi_ssid.get().strip()}\n"
            f"📶 {i18n.t('wiz_step3_pwd', self.lang)}: {'*' * len(self.e_wifi_pwd.get().strip())}\n"
            f"📶 Smart Connect: {on_txt if self.sw_smart.get() == 1 else off_txt}\n"
            f"⚡ Wi-Fi 7 MLO: {on_txt if self.sw_mlo.get() == 1 else off_txt}\n"
            f"🔋 {'TWT Battery Saver' if is_en else 'TWT Oszczędzanie energii'}: {on_f_txt if self.sw_twt.get() == 1 else off_f_txt}"
        )
        self.lbl_sum_text.configure(text=sum_txt)

    def _apply_all(self):
        self.btn_finish.configure(state="disabled")
        self.btn_back.configure(state="disabled")
        self.lbl_apply_status.configure(text=i18n.t("wiz_applying", self.lang), text_color="#eab308")

        target_ip = self.e_ip.get().strip()
        admin_pwd = self.e_pwd.get().strip()
        wan_mode_str = self.combo_wan_mode.get()
        mtu_val = safe_int(self.combo_mtu.get().split()[0], 1472)
        pppoe_u = self.e_pppoe_user.get().strip()
        pppoe_p = self.e_pppoe_pwd.get().strip()
        ssid = self.e_wifi_ssid.get().strip()
        wifi_pwd = self.e_wifi_pwd.get().strip()
        is_smart = self.sw_smart.get() == 1
        is_mlo = self.sw_mlo.get() == 1
        is_twt = self.sw_twt.get() == 1

        def run_apply():
            cli = MiWiFiClient(target_ip)
            # 1. Logowanie lub inicjalizacja
            ok = cli.login_with_password(admin_pwd)
            if not ok:
                self.after(0, lambda: self.lbl_apply_status.configure(text=i18n.t("wiz_err_auth", self.lang), text_color="#ef4444"))
                self.after(0, lambda: self.btn_finish.configure(state="normal"))
                self.after(0, lambda: self.btn_back.configure(state="normal"))
                return

            # 2. WAN
            wan_type = "pppoe" if "PPPoE" in wan_mode_str else "dhcp"
            try:
                cli.set_wan(wan_type=wan_type, mtu=mtu_val, pppoe_user=pppoe_u if wan_type == "pppoe" else None, pppoe_pwd=pppoe_p if wan_type == "pppoe" else None)
            except Exception as e:
                print("WAN set warn:", e)

            # 3. Wi-Fi
            try:
                cli.set_all_wifi(ssid=ssid, pwd=wifi_pwd, encryption="sae-mixed", txpwr="max")
            except Exception as e:
                print("Wi-Fi set warn:", e)

            # 4. TWT
            try:
                cli.set_twt(enabled=is_twt)
            except Exception as e:
                pass

            def finish():
                self.lbl_apply_status.configure(text="✔ " + i18n.t("wiz_success", self.lang), text_color="#22c55e")
                msg_title = "Wizard Finished" if self.lang == "en" else "Kreator Zakończony"
                messagebox.showinfo(msg_title, i18n.t("wiz_success", self.lang), parent=self)
                # Zaktualizuj główne okno aplikacji
                self.parent.ip_entry.delete(0, "end")
                self.parent.ip_entry.insert(0, target_ip)
                self.parent.auth_mode.set(i18n.t("auth_pwd", self.lang))
                self.parent.auth_entry.delete(0, "end")
                self.parent.auth_entry.insert(0, admin_pwd)
                self.parent.client.ip = target_ip
                self.parent.client.stok = cli.stok
                self.parent.client.connected = True
                self.parent.status_indicator.configure(text=i18n.t("status_connected", self.lang), text_color="#22c55e")
                self.parent.btn_connect.configure(text=i18n.t("disconnect", self.lang))
                self.parent._fetch_data_thread()
                self.destroy()

            self.after(0, finish)

        threading.Thread(target=run_apply, daemon=True).start()
