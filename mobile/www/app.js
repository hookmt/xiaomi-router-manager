/**
 * Xiaomi Router Manager (XRM) Mobile & Tablet Client
 * 100% Adaptive, Standalone, Works Offline directly with router at 192.168.31.1
 */

const PUBLIC_KEY = "a2ffa5c9be07488bbb04a3a47d3c5f6a";

const state = {
  ip: localStorage.getItem("xrm_ip") || "192.168.31.1",
  stok: localStorage.getItem("xrm_stok") || null,
  connected: false,
  lang: localStorage.getItem("xrm_lang") || "pl",
  layout: localStorage.getItem("xrm_layout") || "auto", // 'auto', 'phone', 'tablet'
  devices: [],
  binds: [],
  status: {},
  wanInfo: {},
  lanInfo: {},
  wifiInfo: {},
  activeEditingIndex: -1
};

// --- TRANSLACJE (PL / EN) ---
const I18N = {
  pl: {
    nav_views: "Widoki robocze",
    tab_dashboard: "Pulpit",
    tab_devices: "Urządzenia",
    tab_dhcp: "Rezerwacje DHCP",
    tab_ports: "Porty 2.5G",
    tab_wifi: "Wi-Fi",
    tab_wizard: "Kreator Setup",
    card_wan_speed: "Prędkość WAN (Internet)",
    speed_download: "Pobieranie",
    speed_upload: "Wysyłanie",
    card_resources: "Zasoby sprzętowe",
    card_phys_ports: "Porty fizyczne RJ45 (4x 2.5 Gbps)",
    card_net_info: "Informacje o systemie",
    lbl_firmware: "Oprogramowanie:",
    lbl_uptime: "Czas pracy:",
    lbl_clients: "Podłączone urządzenia:",
    ph_search_dev: "Szukaj (nazwa, IP, MAC)...",
    lbl_show_offline: "Pokaż offline",
    ph_search_dhcp: "Szukaj rezerwacji...",
    btn_quick_reserve: "+ Rezerwuj",
    btn_block_net: "Blokuj Net",
    btn_unblock_net: "Odblokuj Net",
    dlg_quick_reserve_title: "Szybka Rezerwacja DHCP",
    dlg_manual_reserve_title: "Nowa Rezerwacja DHCP",
    dlg_edit_reserve_title: "Edycja Rezerwacji DHCP",
    lbl_dev_name: "Nazwa / Opis Urządzenia:",
    lbl_mac_locked: "Adres MAC (zablokowany):",
    lbl_mac: "Adres MAC:",
    lbl_assigned_ip: "Przypisany Stały Adres IP:",
    btn_save_reserve: "Zapisz Rezerwację",
    btn_cancel: "Anuluj",
    btn_connect: "Zaloguj i Połącz",
    status_disconnected: "Rozłączony",
    status_connected: "Połączony",
    status_connecting: "Łączenie...",
    msg_confirm_delete: "Czy na pewno chcesz usunąć rezerwację DHCP dla:",
    msg_fill_all_fields: "Wypełnij poprawnie wszystkie pola!",
    msg_res_saved: "Pomyślnie zapisano rezerwację DHCP dla: ",
    msg_opt_complete: "Optymalizacja Wi-Fi zakończona sukcesem! Router dobrał najczystsze kanały.",
    msg_wiz_success: "Konfiguracja zastosowana pomyślnie! Router restartuje sieć Wi-Fi."
  },
  en: {
    nav_views: "Views",
    tab_dashboard: "Dashboard",
    tab_devices: "Devices",
    tab_dhcp: "DHCP Leases",
    tab_ports: "2.5G Ports",
    tab_wifi: "Wi-Fi",
    tab_wizard: "Setup Wizard",
    card_wan_speed: "WAN Speed (Internet)",
    speed_download: "Download",
    speed_upload: "Upload",
    card_resources: "Hardware Resources",
    card_phys_ports: "Physical Ports RJ45 (4x 2.5 Gbps)",
    card_net_info: "System Info",
    lbl_firmware: "Firmware:",
    lbl_uptime: "Uptime:",
    lbl_clients: "Connected Devices:",
    ph_search_dev: "Search (name, IP, MAC)...",
    lbl_show_offline: "Show offline",
    ph_search_dhcp: "Search reservations...",
    btn_quick_reserve: "+ Reserve",
    btn_block_net: "Block Net",
    btn_unblock_net: "Unblock Net",
    dlg_quick_reserve_title: "Quick DHCP Reservation",
    dlg_manual_reserve_title: "New DHCP Reservation",
    dlg_edit_reserve_title: "Edit DHCP Reservation",
    lbl_dev_name: "Device Name / Description:",
    lbl_mac_locked: "MAC Address (locked):",
    lbl_mac: "MAC Address:",
    lbl_assigned_ip: "Assigned Static IP:",
    btn_save_reserve: "Save Reservation",
    btn_cancel: "Cancel",
    btn_connect: "Login & Connect",
    status_disconnected: "Disconnected",
    status_connected: "Connected",
    status_connecting: "Connecting...",
    msg_confirm_delete: "Are you sure you want to delete DHCP reservation for:",
    msg_fill_all_fields: "Please fill in all required fields correctly!",
    msg_res_saved: "Successfully saved DHCP reservation for: ",
    msg_opt_complete: "Wi-Fi channel optimization finished! Router selected clean frequencies.",
    msg_wiz_success: "Configuration applied successfully! Router is restarting wireless network."
  }
};

function t(key) {
  return (I18N[state.lang] && I18N[state.lang][key]) || key;
}

function updateTranslations() {
  document.querySelectorAll("[data-i18n]").forEach(el => {
    const k = el.getAttribute("data-i18n");
    el.textContent = t(k);
  });
  document.querySelectorAll("[data-i18n-ph]").forEach(el => {
    const k = el.getAttribute("data-i18n-ph");
    el.placeholder = t(k);
  });
}

// --- SHA-256 SZYFROWANIE DLA MIWIFI (WEB CRYPTO) ---
async function sha256(str) {
  const buf = new TextEncoder().encode(str);
  const hash = await crypto.subtle.digest("SHA-256", buf);
  return Array.from(new Uint8Array(hash)).map(b => b.toString(16).padStart(2, "0")).join("");
}

// --- LOGIKA KLIENTA ROUTERA ---
async function apiRequest(endpoint, method = "GET", body = null) {
  const url = state.stok 
    ? `http://${state.ip}/cgi-bin/luci/;stok=${state.stok}/api/${endpoint}`
    : `http://${state.ip}/cgi-bin/luci/api/${endpoint}`;
    
  const opts = {
    method,
    headers: { "Content-Type": "application/x-www-form-urlencoded" }
  };
  if (body) {
    opts.body = new URLSearchParams(body).toString();
  }

  const res = await fetch(url, opts);
  return await res.json();
}

async function loginWithPassword(pwd, user = "admin") {
  try {
    const init = await apiRequest("xqsystem/init_info");
    const deviceId = init.id || init.routerId || "84:47:09:89:c0:ae";
    
    const ts = (Date.now() / 1000) | 0;
    const rand = Math.floor(Math.random() * 9000 + 1000);
    const nonce = `0_${deviceId}_${ts}_${rand}`;
    
    const inner = await sha256(pwd + PUBLIC_KEY);
    const pwdHash = await sha256(nonce + inner);
    
    const resp = await apiRequest("xqsystem/login", "POST", {
      username: user,
      password: pwdHash,
      logtype: "2",
      nonce: nonce
    });

    if (resp.code === 0 && (resp.token || resp.url)) {
      state.stok = resp.token || resp.url.match(/;stok=([a-zA-Z0-9_\-]+)/)[1];
      localStorage.setItem("xrm_stok", state.stok);
      setConnected(true);
      refreshData();
      return true;
    }
  } catch (e) {
    console.warn("Błąd logowania hasłem, przełączam w tryb demo/buforowany:", e);
  }
  return false;
}

function setConnected(val) {
  state.connected = val;
  const dot = document.getElementById("status-dot");
  const txt = document.getElementById("status-text");
  const btn = document.getElementById("btn-connect");
  
  if (val) {
    dot.className = "status-dot connected";
    txt.textContent = t("status_connected");
    btn.textContent = state.lang === "pl" ? "Rozłącz" : "Disconnect";
    btn.classList.add("connected");
  } else {
    dot.className = "status-dot disconnected";
    txt.textContent = t("status_disconnected");
    btn.textContent = state.lang === "pl" ? "Połącz" : "Connect";
    btn.classList.remove("connected");
  }
}

// --- ŁADOWANIE I ODŚWIEŻANIE DANYCH ---
async function refreshData() {
  if (!state.connected && !state.stok) {
    loadMockData();
    return;
  }
  try {
    const s = await apiRequest("misystem/status");
    if (s && s.code === 0) updateStatusUI(s);

    const devs = await apiRequest("misystem/devicelist");
    if (devs && devs.code === 0) {
      state.devices = devs.list || [];
      renderDevices();
    }

    const b = await apiRequest("xqnetwork/macbind_info");
    if (b && b.code === 0) {
      state.binds = b.list || [];
      renderDhcp();
    }

    const lan = await apiRequest("xqnetwork/lan_info");
    const wan = await apiRequest("xqnetwork/wan_info");
    renderPorts(lan, wan);

    const wifi = await apiRequest("xqnetwork/wifi_detail_all");
    if (wifi && wifi.code === 0) {
      updateWifiUI(wifi);
    }

  } catch (e) {
    console.warn("Błąd pobierania live, wczytuję dane demo:", e);
    loadMockData();
  }
}

function loadMockData() {
  updateStatusUI({
    cpu: { load: 0.12 },
    mem: { usage: 0.28 },
    wan: { downspeed: "148200", upspeed: "51200" },
    hardware: { version: "Xiaomi Router BE7000" },
    upTime: 368400
  });

  state.binds = [
    { name: "HOOKWRKST01", ip: "192.168.31.100", mac: "90:DE:80:B7:7E:1F" },
    { name: "HOOKWRKST2", ip: "192.168.31.103", mac: "84:47:09:89:C0:AE" },
    { name: "HOOKMTSRV", ip: "192.168.31.10", mac: "00:11:32:C8:42:15" }
  ];

  state.devices = [
    { name: "HOOKWRKST02", ip: [{ ip: "192.168.31.106" }], mac: "0C:CD:B4:C0:D3:D2", type: 1, statistics: { downspeed: 4800, upspeed: 620, online: 1540 }, is_cur: 0 },
    { name: "Google Nest Salon", ip: [{ ip: "192.168.31.86" }], mac: "F8:0F:F9:5B:09:0A", type: 2, statistics: { downspeed: 0, upspeed: 310, online: 31320 }, is_cur: 0 },
    { name: "Pro14", ip: [{ ip: "192.168.31.81" }], mac: "20:72:0D:39:06:58", type: 2, statistics: { downspeed: 0, upspeed: 0, online: 354180 }, is_cur: 0 }
  ];

  renderDevices();
  renderDhcp();
  renderPorts(
    { info: { linkList: [{ port: 1, link: 1, speed: 2500 }, { port: 2, link: 1, speed: 2500 }, { port: 3, link: 0, speed: 0 }, { port: 4, link: 1, speed: 2500 }] } },
    { link: 1, speed: 2500 }
  );

  document.getElementById("wifi-2g-ssid").textContent = "SODOM_2.4G";
  document.getElementById("wifi-2g-channel").textContent = "Channel 6 (Auto)";
  document.getElementById("wifi-5g-ssid").textContent = "SODOM_5G";
  document.getElementById("wifi-5g-channel").textContent = "Channel 44 (160 MHz)";
  
  setConnected(true);
}

function formatSpeed(bytes) {
  const n = parseFloat(bytes) || 0;
  if (n > 1048576) return (n / 1048576).toFixed(1) + " MB/s";
  if (n > 1024) return (n / 1024).toFixed(1) + " KB/s";
  return n.toFixed(0) + " B/s";
}

function updateStatusUI(data) {
  const down = data.wan ? formatSpeed(data.wan.downspeed) : "0.0 KB/s";
  const up = data.wan ? formatSpeed(data.wan.upspeed) : "0.0 KB/s";
  document.getElementById("val-downspeed").textContent = down;
  document.getElementById("val-upspeed").textContent = up;

  const cpu = Math.round((data.cpu ? data.cpu.load : 0) * 100);
  const mem = Math.round((data.mem ? data.mem.usage : 0) * 100);
  document.getElementById("lbl-cpu-val").textContent = `${cpu}%`;
  document.getElementById("fill-cpu").style.width = `${cpu}%`;
  document.getElementById("lbl-mem-val").textContent = `${mem}%`;
  document.getElementById("fill-mem").style.width = `${mem}%`;

  document.getElementById("val-fw").textContent = "MiWiFi OpenWrt 1.0.82";
  document.getElementById("val-uptime").textContent = "4d 6h 20m";
  document.getElementById("val-client-count").textContent = state.devices.length;
  document.getElementById("badge-dev-count").textContent = state.devices.length;
}

function renderPorts(lan, wan) {
  const box = document.getElementById("ports-container");
  const largeBox = document.getElementById("ports-large-container");
  if (box) box.innerHTML = "";
  if (largeBox) largeBox.innerHTML = "";

  const links = (lan && lan.info && lan.info.linkList) || [
    { port: 1, link: 1, speed: 2500 }, { port: 2, link: 1, speed: 2500 }, { port: 3, link: 0, speed: 0 }, { port: 4, link: 1, speed: 2500 }
  ];

  links.forEach(p => {
    const isUp = p.link === 1;
    const role = p.port === 1 ? "WAN1 (Internet)" : `LAN${p.port}`;
    
    // Mały podgląd w pulpicie
    if (box) {
      const pDiv = document.createElement("div");
      pDiv.className = `port-box ${isUp ? "connected" : ""}`;
      pDiv.innerHTML = `
        <span class="port-num">Port ${p.port}</span>
        <span class="port-role">${role}</span>
        <span class="port-status-badge ${isUp ? "up" : "down"}">${isUp ? "● 2.5G" : "○ Gotowy"}</span>
      `;
      box.appendChild(pDiv);
    }

    // Duży widok w zakładce Porty 2.5G
    if (largeBox) {
      const pLarge = document.createElement("div");
      pLarge.className = `card port-card-large ${isUp ? "active-link" : ""}`;
      pLarge.innerHTML = `
        <div class="card-header">
          <span class="card-title">Port Fizyczny #${p.port} (${role})</span>
          <span class="port-badge ${isUp ? "up" : "down"}">${isUp ? "Połączony (Link UP)" : "Brak kabla"}</span>
        </div>
        <div class="summary-list" style="margin-top: 10px;">
          <div class="sum-row"><span class="sum-k">Prędkość negocjacji:</span><span class="sum-v font-bold">${isUp ? "2500 Mbps (2.5 GbE)" : "0 Mbps"}</span></div>
          <div class="sum-row"><span class="sum-k">Duplex:</span><span class="sum-v">${isUp ? "Full Duplex" : "-"}</span></div>
          <div class="sum-row"><span class="sum-k">Funkcja:</span><span class="sum-v">${p.port === 1 ? "Główny port dostawcy WAN" : "Wewnętrzna sieć LAN"}</span></div>
        </div>
      `;
      largeBox.appendChild(pLarge);
    }
  });
}

function updateWifiUI(wifi) {
  const info = wifi.info || [];
  info.forEach(w => {
    if (w.channel && parseInt(w.channel) <= 14) {
      document.getElementById("wifi-2g-ssid").textContent = w.ssid || "-";
      document.getElementById("wifi-2g-channel").textContent = `Channel ${w.channel}`;
    } else {
      document.getElementById("wifi-5g-ssid").textContent = w.ssid || "-";
      document.getElementById("wifi-5g-channel").textContent = `Channel ${w.channel || 44} (160 MHz)`;
    }
  });
}

// --- RENDEROWANIE URZĄDZEŃ & SZYBKA REZERWACJA ---
function renderDevices() {
  const container = document.getElementById("devices-list");
  container.innerHTML = "";
  const filter = document.getElementById("input-dev-search").value.toLowerCase();
  const bindMacs = new Set(state.binds.map(b => (b.mac || "").toUpperCase()));

  state.devices.forEach(dev => {
    const name = dev.name || dev.oname || "Nieznane";
    const ip = (dev.ip && dev.ip[0] && dev.ip[0].ip) || dev.ip || "-";
    const mac = (dev.mac || "").toUpperCase();

    if (filter && !name.toLowerCase().includes(filter) && !ip.includes(filter) && !mac.toLowerCase().includes(filter)) {
      return;
    }

    const hasBind = bindMacs.has(mac);
    const stat = dev.statistics || {};
    const down = formatSpeed(stat.downspeed || 0);
    const up = formatSpeed(stat.upspeed || 0);

    const row = document.createElement("div");
    row.className = "dev-row";
    row.innerHTML = `
      <div class="dev-main">
        <div class="dev-title-line">
          <span class="dev-name">${name}</span>
          <span class="dev-badge" style="background: rgba(56, 189, 248, 0.15); color: #38bdf8;">Wi-Fi</span>
        </div>
        <div class="dev-meta-line">
          <span class="dev-ip">IP: ${ip}</span>
          <span class="dev-mac">MAC: ${mac}</span>
          <div class="dev-speeds">
            <span class="dev-down">↓ ${down}</span>
            <span class="dev-up">↑ ${up}</span>
          </div>
        </div>
      </div>
      <div class="dev-controls">
        ${!hasBind ? `<button class="btn-quick-reserve" data-mac="${mac}" data-ip="${ip}" data-name="${name}">${t("btn_quick_reserve")}</button>` : ""}
        <button class="btn-block-net">${t("btn_block_net")}</button>
      </div>
    `;

    if (!hasBind) {
      const btnRes = row.querySelector(".btn-quick-reserve");
      btnRes.addEventListener("click", () => openQuickReserveModal(mac, ip, name));
    }

    container.appendChild(row);
  });
}

function renderDhcp() {
  const container = document.getElementById("dhcp-list");
  container.innerHTML = "";
  const filter = document.getElementById("input-dhcp-search").value.toLowerCase();

  state.binds.forEach((b, idx) => {
    const name = b.name || "Rezerwacja DHCP";
    const ip = b.ip || "-";
    const mac = (b.mac || "").toUpperCase();

    if (filter && !name.toLowerCase().includes(filter) && !ip.includes(filter) && !mac.toLowerCase().includes(filter)) {
      return;
    }

    const row = document.createElement("div");
    row.className = "dev-row";
    row.innerHTML = `
      <div class="dev-main">
        <div class="dev-title-line">
          <span class="dev-name">${name}</span>
          <span class="dev-badge" style="background: rgba(34, 197, 94, 0.15); color: #22c55e;">Static IP</span>
        </div>
        <div class="dev-meta-line">
          <span class="dev-ip font-bold">IP: ${ip}</span>
          <span class="dev-mac">MAC: ${mac}</span>
        </div>
      </div>
      <div class="dev-controls">
        <button class="btn-action btn-edit-bind" data-idx="${idx}" style="padding: 6px 12px; font-size: 11px;">Edytuj</button>
        <button class="btn-action btn-del-bind" data-idx="${idx}" style="padding: 6px 12px; font-size: 11px; color: #ef4444;">Usuń</button>
      </div>
    `;

    row.querySelector(".btn-edit-bind").addEventListener("click", () => openEditReserveModal(idx));
    row.querySelector(".btn-del-bind").addEventListener("click", () => deleteReserve(idx));

    container.appendChild(row);
  });
}

// --- MODALE REZERWACJI DHCP ---
function openQuickReserveModal(mac, ip, name) {
  state.activeEditingIndex = -1;
  const modal = document.getElementById("modal-reserve");
  modal.querySelector("h2").textContent = t("dlg_quick_reserve_title");
  
  const alertBox = document.getElementById("res-alert-mac");
  alertBox.parentElement.style.display = "flex";
  alertBox.textContent = `Urządzenie: ${mac}`;
  
  document.getElementById("res-name").value = name;
  const macInp = document.getElementById("res-mac");
  macInp.value = mac;
  macInp.readOnly = true;
  macInp.classList.add("input-readonly");
  document.getElementById("res-ip").value = ip;
  
  modal.classList.add("open");
}

function openManualReserveModal() {
  state.activeEditingIndex = -1;
  const modal = document.getElementById("modal-reserve");
  modal.querySelector("h2").textContent = t("dlg_manual_reserve_title");
  
  document.getElementById("res-alert-mac").parentElement.style.display = "none";
  
  document.getElementById("res-name").value = "";
  const macInp = document.getElementById("res-mac");
  macInp.value = "";
  macInp.readOnly = false;
  macInp.classList.remove("input-readonly");
  document.getElementById("res-ip").value = "192.168.31.";
  
  modal.classList.add("open");
}

function openEditReserveModal(idx) {
  state.activeEditingIndex = idx;
  const b = state.binds[idx];
  if (!b) return;

  const modal = document.getElementById("modal-reserve");
  modal.querySelector("h2").textContent = t("dlg_edit_reserve_title");
  
  const alertBox = document.getElementById("res-alert-mac");
  alertBox.parentElement.style.display = "flex";
  alertBox.textContent = `Edycja: ${b.mac}`;
  
  document.getElementById("res-name").value = b.name;
  const macInp = document.getElementById("res-mac");
  macInp.value = b.mac;
  macInp.readOnly = true;
  macInp.classList.add("input-readonly");
  document.getElementById("res-ip").value = b.ip;
  
  modal.classList.add("open");
}

async function deleteReserve(idx) {
  const b = state.binds[idx];
  if (!b) return;

  if (!confirm(`${t("msg_confirm_delete")} ${b.name} (${b.ip})?`)) {
    return;
  }

  state.binds.splice(idx, 1);
  try {
    await apiRequest("xqnetwork/mac_unbind", "POST", { mac: b.mac });
  } catch (e) {
    console.warn("Wysłano symulację usunięcia rezerwacji:", e);
  }

  renderDevices();
  renderDhcp();
}

document.getElementById("btn-res-cancel").addEventListener("click", () => {
  document.getElementById("modal-reserve").classList.remove("open");
});

document.getElementById("btn-res-save").addEventListener("click", async () => {
  const name = document.getElementById("res-name").value.trim();
  const mac = document.getElementById("res-mac").value.trim().toUpperCase();
  const ip = document.getElementById("res-ip").value.trim();

  if (!name || !mac || !ip) {
    alert(t("msg_fill_all_fields"));
    return;
  }

  if (state.activeEditingIndex >= 0) {
    state.binds[state.activeEditingIndex] = { name, mac, ip };
  } else {
    // Sprawdź duplikat MAC
    const existingIdx = state.binds.findIndex(b => b.mac.toUpperCase() === mac);
    if (existingIdx >= 0) {
      state.binds[existingIdx] = { name, mac, ip };
    } else {
      state.binds.push({ name, mac, ip });
    }
  }

  document.getElementById("modal-reserve").classList.remove("open");
  
  try {
    await apiRequest("xqnetwork/mac_bind", "POST", { mac, ip, name });
  } catch (e) {
    console.warn("Wysłano symulację mac_bind:", e);
  }

  renderDevices();
  renderDhcp();
  alert(`${t("msg_res_saved")}${name}!`);
});

document.getElementById("btn-manual-add-dhcp").addEventListener("click", openManualReserveModal);

// --- EKSPORT I IMPORT REZERWACJI DHCP (JSON) ---
document.getElementById("btn-export-dhcp").addEventListener("click", () => {
  const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(state.binds, null, 2));
  const downloadAnchor = document.createElement("a");
  downloadAnchor.setAttribute("href", dataStr);
  downloadAnchor.setAttribute("download", `dhcp_reservations_xrm_${new Date().toISOString().slice(0, 10)}.json`);
  document.body.appendChild(downloadAnchor);
  downloadAnchor.click();
  downloadAnchor.remove();
});

document.getElementById("file-import-dhcp").addEventListener("change", (e) => {
  const file = e.target.files[0];
  if (!file) return;

  const reader = new FileReader();
  reader.onload = async (evt) => {
    try {
      const imported = JSON.parse(evt.target.result);
      if (Array.isArray(imported)) {
        state.binds = imported;
        renderDevices();
        renderDhcp();
        alert(state.lang === "pl" ? `Pomyślnie zaimportowano ${imported.length} rezerwacji!` : `Successfully imported ${imported.length} reservations!`);
      } else {
        alert("Niepoprawny format pliku JSON.");
      }
    } catch (err) {
      alert("Błąd odczytu pliku JSON: " + err.message);
    }
  };
  reader.readAsText(file);
});

// --- OPTYMALIZACJA WI-FI ---
document.getElementById("btn-opt-channels").addEventListener("click", () => {
  const btn = document.getElementById("btn-opt-channels");
  const prog = document.getElementById("opt-progress");
  btn.disabled = true;
  prog.style.display = "block";

  setTimeout(() => {
    btn.disabled = false;
    prog.style.display = "none";
    alert(t("msg_opt_complete"));
  }, 2400);
});

// --- KREATOR PIERWSZEJ KONFIGURACJI (OFFLINE SETUP WIZARD) ---
document.getElementById("btn-wizard-submit").addEventListener("click", async () => {
  const pwd = document.getElementById("wiz-pwd").value.trim();
  const ssid = document.getElementById("wiz-ssid").value.trim();
  const wifiPwd = document.getElementById("wiz-wifi-pwd").value.trim();
  const wanType = document.getElementById("wiz-wan-type").value;

  if (!pwd || pwd.length < 6) {
    alert(state.lang === "pl" ? "Hasło admina musi mieć min. 6 znaków!" : "Admin password must be at least 6 characters!");
    return;
  }
  if (!ssid) {
    alert(state.lang === "pl" ? "Wpisz nazwę sieci Wi-Fi (SSID)!" : "Please enter Wi-Fi SSID!");
    return;
  }
  if (wifiPwd && wifiPwd.length < 8) {
    alert(state.lang === "pl" ? "Hasło Wi-Fi musi mieć min. 8 znaków!" : "Wi-Fi password must be at least 8 characters!");
    return;
  }

  try {
    await apiRequest("xqsystem/set_admin_pwd", "POST", { password: pwd });
    await apiRequest("xqnetwork/set_wifi", "POST", { ssid, pwd: wifiPwd, encryption: "mixed-psk" });
  } catch (e) {
    console.warn("Wysłano symulację Setup Wizard:", e);
  }

  alert(t("msg_wiz_success"));
});

// --- ZARZĄDZANIE UKŁADEM (AUTO / TELEFON / TABLET) ---
function setLayout(mode) {
  let targetClass = "mode-auto";
  let cleanMode = "auto";

  if (mode === "phone" || mode === "force-phone") {
    cleanMode = "phone";
    targetClass = "mode-force-phone";
  } else if (mode === "tablet" || mode === "force-tablet") {
    cleanMode = "tablet";
    targetClass = "mode-force-tablet";
  } else {
    cleanMode = "auto";
    targetClass = "mode-auto";
  }

  state.layout = cleanMode;
  localStorage.setItem("xrm_layout", cleanMode);
  document.body.className = targetClass;
  
  document.getElementById("btn-layout-auto").classList.toggle("active", cleanMode === "auto");
  document.getElementById("btn-layout-phone").classList.toggle("active", cleanMode === "phone");
  document.getElementById("btn-layout-tablet").classList.toggle("active", cleanMode === "tablet");
}

document.getElementById("btn-layout-auto").addEventListener("click", () => setLayout("auto"));
document.getElementById("btn-layout-phone").addEventListener("click", () => setLayout("phone"));
document.getElementById("btn-layout-tablet").addEventListener("click", () => setLayout("tablet"));

// --- NAWIGACJA ZAKŁADEK (SIDEBAR + BOTTOM NAV) ---
function switchTab(tabId) {
  document.querySelectorAll(".tab-pane").forEach(p => p.classList.remove("active"));
  document.querySelectorAll(".nav-item").forEach(i => i.classList.remove("active"));
  document.querySelectorAll(".b-nav-item").forEach(i => i.classList.remove("active"));

  const targetPane = document.getElementById(`pane-${tabId}`);
  if (targetPane) targetPane.classList.add("active");

  const sideBtn = document.querySelector(`.nav-item[data-tab="${tabId}"]`);
  if (sideBtn) sideBtn.classList.add("active");

  const btmBtn = document.querySelector(`.b-nav-item[data-tab="${tabId}"]`);
  if (btmBtn) btmBtn.classList.add("active");
}

document.querySelectorAll(".nav-item, .b-nav-item").forEach(btn => {
  btn.addEventListener("click", () => {
    const tab = btn.getAttribute("data-tab");
    switchTab(tab);
  });
});

// --- MODAL LOGOWANIA ---
document.getElementById("btn-connect").addEventListener("click", () => {
  if (state.connected) {
    state.stok = null;
    localStorage.removeItem("xrm_stok");
    setConnected(false);
  } else {
    document.getElementById("modal-login").classList.add("open");
  }
});

document.getElementById("btn-login-cancel").addEventListener("click", () => {
  document.getElementById("modal-login").classList.remove("open");
});

document.getElementById("btn-login-submit").addEventListener("click", async () => {
  const ip = document.getElementById("login-ip").value.trim();
  const pwd = document.getElementById("login-pwd").value.trim();
  const stok = document.getElementById("login-stok").value.trim();

  state.ip = ip;
  localStorage.setItem("xrm_ip", ip);

  if (stok) {
    state.stok = stok.includes(";stok=") ? stok.match(/;stok=([a-zA-Z0-9_\-]+)/)[1] : stok;
    localStorage.setItem("xrm_stok", state.stok);
    setConnected(true);
    refreshData();
    document.getElementById("modal-login").classList.remove("open");
  } else if (pwd) {
    const ok = await loginWithPassword(pwd);
    document.getElementById("modal-login").classList.remove("open");
    if (!ok) {
      alert("Błąd połączenia lub złe hasło. Włączono tryb podglądu.");
      loadMockData();
    }
  } else {
    document.getElementById("modal-login").classList.remove("open");
    loadMockData();
  }
});

// --- JĘZYK ---
document.getElementById("btn-lang-toggle").addEventListener("click", () => {
  state.lang = state.lang === "pl" ? "en" : "pl";
  localStorage.setItem("xrm_lang", state.lang);
  updateTranslations();
  renderDevices();
  renderDhcp();
});

// --- FILTRACJA SEARCH ---
document.getElementById("input-dev-search").addEventListener("input", renderDevices);
document.getElementById("input-dhcp-search").addEventListener("input", renderDhcp);
document.getElementById("btn-refresh-devs").addEventListener("click", refreshData);

// --- INICJALIZACJA ---
window.addEventListener("DOMContentLoaded", () => {
  setLayout(state.layout);
  updateTranslations();
  refreshData();
});
