/**
 * Xiaomi Router Manager (XRM) - Mobilny i Tabletowy Panel Klienta
 * Wersja oparta o architekturę z wersji Windows v1.0.2 z zachowaniem pełnej ergonomii dotykowej.
 */

const PUBLIC_KEY = "a2ffa5c9be07488bbb04a3a47d3c5f6a";

const state = {
  ip: localStorage.getItem("xrm_ip") || "192.168.31.1",
  stok: localStorage.getItem("xrm_stok") || null,
  savedPwd: localStorage.getItem("xrm_saved_pwd") || "",
  connected: false,
  lang: localStorage.getItem("xrm_lang") || "pl",
  layout: localStorage.getItem("xrm_layout") || "auto",
  autoRefreshInterval: null,
  currentView: "dashboard",
  
  // Dane routera z API
  devices: [],
  binds: [],
  status: {},
  wanInfo: {},
  lanInfo: {},
  lanDhcp: {},
  wifiInfo: {},
  portsStatus: [],
  activeEditingIndex: -1
};

// Słownik tłumaczeń (PL / EN)
const I18N = {
  pl: {
    status_disconnected: "Rozłączony",
    status_connected: "Połączony",
    status_connecting: "Łączenie...",
    btn_connect: "Połącz",
    btn_disconnect: "Rozłącz",
    msg_confirm_reboot: "Czy na pewno chcesz zrestartować router Xiaomi BE7000? Spowoduje to chwilowy brak Internetu.",
    msg_confirm_delete_bind: "Czy na pewno chcesz usunąć rezerwację DHCP dla:",
    msg_fill_all_fields: "Wypełnij poprawnie wszystkie wymagane pola!",
    msg_res_saved: "Pomyślnie zapisano rezerwację DHCP dla: ",
    msg_opt_complete: "Optymalizacja Wi-Fi zakończona sukcesem! Router dobrał najczystsze kanały.",
    msg_save_success: "Ustawienia zostały pomyślnie zapisane na routerze!",
    msg_copy_success: "Skopiowano konfigurację JSON do schowka!",
    msg_paste_hint: "Wklej poprawną strukturę JSON z rezerwacjami do pola tekstowego.",
    role_wan1: "Główny Internet (WAN1)",
    role_dualwan: "Drugi Internet (Dual WAN)",
    role_lag: "Agregacja LAN (LAG)",
    role_iptv: "Telewizja IPTV",
    role_game: "Port Gry (Gaming QoS)",
    role_lan: "Lokalna Sieć (LAN)",
    role_down: "Rozłączony / Wolny"
  },
  en: {
    status_disconnected: "Disconnected",
    status_connected: "Connected",
    status_connecting: "Connecting...",
    btn_connect: "Connect",
    btn_disconnect: "Disconnect",
    msg_confirm_reboot: "Are you sure you want to reboot Xiaomi BE7000? Internet connection will be interrupted.",
    msg_confirm_delete_bind: "Are you sure you want to delete DHCP reservation for:",
    msg_fill_all_fields: "Please fill all required fields correctly!",
    msg_res_saved: "DHCP reservation saved for: ",
    msg_opt_complete: "Wi-Fi channel optimization complete! Cleanest channels selected.",
    msg_save_success: "Settings successfully saved to the router!",
    msg_copy_success: "JSON configuration copied to clipboard!",
    msg_paste_hint: "Paste valid JSON reservation structure into the text area.",
    role_wan1: "Main Internet (WAN1)",
    role_dualwan: "Secondary Internet (Dual WAN)",
    role_lag: "LAN Aggregation (LAG)",
    role_iptv: "IPTV Bridge",
    role_game: "Gaming Port (VIP QoS)",
    role_lan: "Local Network (LAN)",
    role_down: "Disconnected / Idle"
  }
};

function t(key) {
  return (I18N[state.lang] && I18N[state.lang][key]) || key;
}

// SHA-256 helper
async function sha256(str) {
  const buf = new TextEncoder().encode(str);
  const hash = await crypto.subtle.digest("SHA-256", buf);
  return Array.from(new Uint8Array(hash)).map(b => b.toString(16).padStart(2, "0")).join("");
}

// Baza URL API (obsługa transparentnego proxy w run_preview.py dla eliminacji CORS)
function getApiBaseUrl() {
  if (window.location.protocol.startsWith("http") && (window.location.port === "8088" || window.location.hostname === "localhost")) {
    return ""; // Względna ścieżka do lokalnego proxy na porcie 8088
  }
  return `http://${state.ip}`;
}

// Główne zapytanie do routera
async function apiRequest(endpoint, method = "GET", body = null) {
  const base = getApiBaseUrl();
  const url = state.stok 
    ? `${base}/cgi-bin/luci/;stok=${state.stok}/api/${endpoint}`
    : `${base}/cgi-bin/luci/api/${endpoint}`;
    
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

// Wyciąganie tokena stok z linku lub czystego tekstu
function extractStok(text) {
  if (!text) return null;
  text = text.trim();
  const m = text.match(/;stok=([a-zA-Z0-9_\-]+)/);
  if (m) return m[1];
  if (/^[a-zA-Z0-9_\-]+$/.test(text) && text.length >= 16) return text;
  return null;
}

// Logowanie przez gotowy token stok lub pełny link
async function loginWithStok(stokOrUrl) {
  const token = extractStok(stokOrUrl);
  if (!token) return false;
  state.stok = token;
  localStorage.setItem("xrm_stok", token);
  try {
    const res = await apiRequest("xqsystem/status");
    if (res.code === 0) {
      setConnected(true);
      await refreshData();
      return true;
    }
  } catch (e) {}
  state.stok = null;
  localStorage.removeItem("xrm_stok");
  setConnected(false);
  return false;
}

// Autoryzacja SHA-256 zgodna z protokołem MiWiFi
async function loginWithPassword(pwd, user = "admin") {
  try {
    const init = await apiRequest("xqsystem/init_info");
    const candidates = [];
    if (init.routerId) candidates.push(init.routerId);
    if (init.id && !init.id.includes("/")) candidates.push(init.id);
    candidates.push("84:47:09:89:c0:ae");
    candidates.push("58:ea:1f:4a:73:20");
    candidates.push("58:ea:1f:4a:73:23");

    for (const devId of candidates) {
      const ts = (Date.now() / 1000) | 0;
      const rand = Math.floor(Math.random() * 9000 + 1000);
      const nonce = `0_${devId}_${ts}_${rand}`;
      
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
        await refreshData();
        return true;
      }
    }
  } catch (e) {
    console.warn("Błąd logowania:", e);
  }
  return false;
}

// Ustawienie stanu połączenia w UI
function setConnected(val) {
  state.connected = val;
  const dot = document.getElementById("status-dot");
  const txt = document.getElementById("status-text");
  const btn = document.getElementById("btn-connect");
  
  if (val) {
    dot.className = "status-dot connected";
    txt.textContent = t("status_connected");
    btn.textContent = t("btn_disconnect");
    btn.classList.add("connected");
  } else {
    dot.className = "status-dot disconnected";
    txt.textContent = t("status_disconnected");
    btn.textContent = t("btn_connect");
    btn.classList.remove("connected");
  }
}

// Rozłączenie sesji
function disconnect() {
  state.stok = null;
  localStorage.removeItem("xrm_stok");
  setConnected(false);
}

// Formatowanie jednostek
function formatSpeed(bytesPerSec) {
  const b = parseFloat(bytesPerSec) || 0;
  if (b >= 1048576) return `${(b / 1048576).toFixed(1)} MB/s`;
  if (b >= 1024) return `${(b / 1024).toFixed(1)} KB/s`;
  return `${b.toFixed(0)} B/s`;
}

function formatUptime(seconds) {
  const s = parseInt(seconds) || 0;
  const days = Math.floor(s / 86400);
  const hours = Math.floor((s % 86400) / 3600);
  const mins = Math.floor((s % 3600) / 60);
  if (days > 0) return `${days} dni ${hours} godz. ${mins} min.`;
  if (hours > 0) return `${hours} godz. ${mins} min.`;
  return `${mins} min.`;
}

// ==========================================================================
// ROZPOZNAWANIE POŁĄCZENIA URZĄDZENIA (ZGODNE Z GUI.PY WERSJI WINDOWS)
// ==========================================================================
function getDeviceConnInfo(d) {
  if (d.is_offline) {
    return { type: "offline", label: "Offline (DHCP)", cls: "badge-offline" };
  }
  
  // Kabel LAN (type == 0 lub port ethernet)
  if (d.type === 0 || d.port !== undefined && d.port >= 0) {
    const portNum = d.port !== undefined && d.port >= 1 ? `Port ${d.port}` : "2.5G";
    return { type: "cable", label: `Kabel LAN (${portNum})`, cls: "badge-lan-cable" };
  }
  
  // Wi-Fi pasma
  const band = (d.band || d.wifi || "").toString().toLowerCase();
  if (band.includes("5") || band.includes("5g")) {
    return { type: "wifi5", label: "Wi-Fi 5 GHz", cls: "badge-wifi-5g" };
  }
  if (band.includes("2") || band.includes("2.4")) {
    return { type: "wifi2", label: "Wi-Fi 2.4 GHz", cls: "badge-wifi-2g" };
  }
  if (band.includes("7") || band.includes("mlo")) {
    return { type: "wifi7", label: "Wi-Fi 7 MLO", cls: "badge-wifi-7" };
  }
  
  // Domyślnie Wi-Fi
  return { type: "wifi", label: "Wi-Fi", cls: "badge-wifi-5g" };
}

// ==========================================================================
// POBIERANIE I ODŚWIEŻANIE DANYCH Z ROUTERA
// ==========================================================================
async function refreshData() {
  if (!state.connected || !state.stok) return;

  try {
    const [statusResp, devResp, wanResp] = await Promise.allSettled([
      apiRequest("xqsystem/status"),
      apiRequest("xqsystem/device_list"),
      apiRequest("xqnetwork/wan_info")
    ]);

    if (statusResp.status === "fulfilled" && statusResp.value.code === 0) {
      state.status = statusResp.value;
      renderDashboardStatus(statusResp.value);
    }

    if (devResp.status === "fulfilled" && devResp.value.code === 0) {
      state.devices = devResp.value.list || [];
      renderDevices();
    }

    if (wanResp.status === "fulfilled" && wanResp.value.code === 0) {
      state.wanInfo = wanResp.value.info || {};
      renderWanInfo(wanResp.value.info);
    }

    // Odczyt rezerwacji i portów w tle
    fetchBindsAndPorts();
  } catch (e) {
    console.warn("Błąd odświeżania danych:", e);
  }
}

async function fetchBindsAndPorts() {
  try {
    // 1. Rezerwacje DHCP
    const bindResp = await apiRequest("xqnetwork/wifi_macfilter_info");
    if (bindResp.code === 0 && Array.isArray(bindResp.list)) {
      state.binds = bindResp.list;
      renderBinds();
    }

    // 2. Wi-Fi
    const wifiResp = await apiRequest("xqnetwork/wifi_detail_all");
    if (wifiResp.code === 0 && wifiResp.info) {
      state.wifiInfo = wifiResp.info;
      renderWifiInfo(wifiResp.info);
    }

    // 3. Status Portów Fizycznych
    const portsResp = await apiRequest("xqnetwork/port_status");
    if (portsResp.code === 0 && portsResp.info) {
      state.portsStatus = portsResp.info;
      renderPortsStatus(portsResp.info);
    }
  } catch (e) {
    console.warn("Błąd pobierania portów/rezerwacji:", e);
  }
}

// ==========================================================================
// RENDEROWANIE WIDOKÓW
// ==========================================================================

// 1. Dashboard (Pulpit)
function renderDashboardStatus(s) {
  const cpu = parseFloat(s.cpu?.load || (s.cpu?.core || 0) * 100) || 0;
  const cpuVal = (cpu > 100 ? cpu / 4 : cpu).toFixed(1);
  const ram = Math.round((parseFloat(s.mem?.usage || 0)) * 100);

  document.getElementById("dash-cpu-val").textContent = `${cpuVal}%`;
  document.getElementById("dash-cpu-bar").style.width = `${Math.min(100, cpuVal)}%`;

  document.getElementById("dash-ram-val").textContent = `${ram}%`;
  document.getElementById("dash-ram-bar").style.width = `${Math.min(100, ram)}%`;

  const down = parseFloat(s.wan?.downspeed || 0);
  const up = parseFloat(s.wan?.upspeed || 0);
  document.getElementById("dash-down-speed").textContent = formatSpeed(down);
  document.getElementById("dash-up-speed").textContent = formatSpeed(up);

  if (s.upTime) {
    document.getElementById("dash-uptime").textContent = formatUptime(s.upTime);
  }
  if (s.hardware?.version) {
    document.getElementById("dash-fw").textContent = s.hardware.version;
  }
  if (s.hardware?.mac) {
    document.getElementById("dash-routerid").textContent = s.hardware.mac;
  }
}

// 2. Urządzenia w sieci
function renderDevices() {
  const container = document.getElementById("devices-container");
  const query = (document.getElementById("dev-search-input").value || "").toLowerCase().trim();
  const showOffline = document.getElementById("dev-show-offline").checked;

  document.getElementById("nav-badge-devs").textContent = state.devices.length;
  document.getElementById("dash-dev-count").textContent = state.devices.length;

  // Lista aktywnych MAC
  const activeMacs = new Set(state.devices.map(d => (d.mac || "").toUpperCase()));

  // Budowa pełnej listy urządzeń (aktywne + offline z rezerwacji DHCP)
  const allList = [...state.devices];

  if (showOffline && state.binds) {
    state.binds.forEach(b => {
      const bMac = (b.mac || "").toUpperCase();
      if (!activeMacs.has(bMac)) {
        allList.push({
          name: b.name || "Urządzenie z rezerwacją",
          ip: b.ip,
          mac: b.mac,
          is_offline: true,
          type: -1
        });
      }
    });
  }

  // Filtrowanie wyszukiwarki
  const filtered = allList.filter(d => {
    if (!query) return true;
    const name = (d.name || "").toLowerCase();
    const ip = (d.ip || (d.ip && d.ip[0] && d.ip[0].ip) || "").toLowerCase();
    const mac = (d.mac || "").toLowerCase();
    return name.includes(query) || ip.includes(query) || mac.includes(query);
  });

  if (filtered.length === 0) {
    container.innerHTML = `<div class="empty-state">Brak urządzeń spełniających kryteria wyszukiwania.</div>`;
    return;
  }

  container.innerHTML = filtered.map(d => {
    const conn = getDeviceConnInfo(d);
    const ip = d.ip || (d.ip && d.ip[0] && d.ip[0].ip) || "--";
    const mac = d.mac || "--";
    const downSpeed = formatSpeed(d.statistics?.downspeed || 0);
    const upSpeed = formatSpeed(d.statistics?.upspeed || 0);
    const isOff = d.is_offline ? "offline" : "";

    return `
      <div class="dev-item ${isOff}">
        <div class="dev-col-main">
          <div class="dev-title-row">
            <span class="dev-name">${escapeHtml(d.name || "Nieznane urządzenie")}</span>
            <span class="dev-badge ${conn.cls}">${conn.label}</span>
          </div>
          <div class="dev-meta-row">
            <span>IP: <strong>${ip}</strong></span>
            <span>MAC: <strong>${mac}</strong></span>
          </div>
        </div>
        ${!d.is_offline ? `
          <div class="dev-traffic">
            <span class="traffic-down">↓ ${downSpeed}</span>
            <span class="traffic-up">↑ ${upSpeed}</span>
          </div>
        ` : ""}
        <div class="dev-actions">
          <button class="btn-secondary btn-sm" onclick="quickReservePrompt('${escapeHtml(d.name)}', '${mac}', '${ip}')">+ Rezerwuj</button>
          <button class="btn-secondary btn-sm" onclick="toggleBlockDevice('${mac}', '${escapeHtml(d.name)}')">Blokuj Net</button>
        </div>
      </div>
    `;
  }).join("");
}

// 3. Status WAN
function renderWanInfo(info) {
  if (!info) return;
  document.getElementById("dash-wan-ip").textContent = info.ipv4?.[0]?.ip || info.ip || "--";
  document.getElementById("dash-wan-dns").textContent = (info.dns || []).join(", ") || "--";

  document.getElementById("wan-stat-link").textContent = info.link ? "● Połączony (Link UP)" : "○ Brak kabla (Link DOWN)";
  document.getElementById("wan-stat-proto").textContent = (info.details?.proto || info.proto || "PPPoE").toUpperCase();
  document.getElementById("wan-stat-ip").textContent = info.ipv4?.[0]?.ip || info.ip || "--";
  document.getElementById("wan-stat-mask").textContent = info.ipv4?.[0]?.mask || info.mask || "--";
  document.getElementById("wan-stat-gw").textContent = info.gateWay || info.gateway || "--";
  document.getElementById("wan-stat-dns").textContent = (info.dns || []).join(", ") || "--";
  document.getElementById("wan-stat-mac").textContent = info.mac || "--";
  document.getElementById("wan-stat-mtu").textContent = info.mtu || "1472";
  if (info.uptime) {
    document.getElementById("wan-stat-uptime").textContent = formatUptime(info.uptime);
  }
}

// 4. Rezerwacje DHCP
function renderBinds() {
  const tbody = document.getElementById("binds-tbody");
  const query = (document.getElementById("dhcp-search-input").value || "").toLowerCase().trim();
  document.getElementById("nav-badge-binds").textContent = state.binds.length;

  const filtered = state.binds.filter(b => {
    if (!query) return true;
    return (b.name || "").toLowerCase().includes(query) ||
           (b.ip || "").toLowerCase().includes(query) ||
           (b.mac || "").toLowerCase().includes(query);
  });

  if (filtered.length === 0) {
    tbody.innerHTML = `<tr><td colspan="4" class="empty-state">Brak skonfigurowanych rezerwacji DHCP.</td></tr>`;
    return;
  }

  tbody.innerHTML = filtered.map((b, idx) => `
    <tr>
      <td><strong>${escapeHtml(b.name || "Bez nazwy")}</strong></td>
      <td class="mono">${b.ip}</td>
      <td class="mono">${b.mac}</td>
      <td class="text-right">
        <button class="btn-secondary btn-sm" onclick="editReserveModal(${idx})">Edytuj</button>
        <button class="btn-danger btn-sm" onclick="deleteReserve('${b.mac}', '${escapeHtml(b.name)}')">Usuń</button>
      </td>
    </tr>
  `).join("");
}

// 5. Wi-Fi
function renderWifiInfo(info) {
  if (!Array.isArray(info)) return;
  const wifi2g = info.find(w => w.channel && parseInt(w.channel) <= 14);
  const wifi5g = info.find(w => w.channel && parseInt(w.channel) > 14);

  if (wifi2g) {
    document.getElementById("wifi-2g-ssid").value = wifi2g.ssid || "";
    document.getElementById("wifi-2g-tx").value = wifi2g.txpwr || "max";
    document.getElementById("wifi-2g-channel").value = wifi2g.channel || "0";
  }
  if (wifi5g) {
    document.getElementById("wifi-5g-ssid").value = wifi5g.ssid || "";
    document.getElementById("wifi-5g-tx").value = wifi5g.txpwr || "max";
    document.getElementById("wifi-5g-channel").value = wifi5g.channel || "0";
  }
}

// 6. Porty Fizyczne 2.5G
function renderPortsStatus(ports) {
  if (!Array.isArray(ports)) return;
  const cards = document.querySelectorAll("#ports-hardware-grid .port-card");
  
  ports.forEach((p, idx) => {
    if (cards[idx]) {
      const card = cards[idx];
      const statusEl = card.querySelector(".port-status");
      const badgeEl = card.querySelector(".port-badge");
      
      const isUp = p.link === 1 || p.status === 1;
      const speed = p.speed || "2.5G";
      
      if (isUp) {
        statusEl.className = "port-status status-up";
        statusEl.textContent = `● Połączony (${speed})`;
      } else {
        statusEl.className = "port-status status-down";
        statusEl.textContent = `○ Rozłączony (Auto MDI-X)`;
        badgeEl.className = "port-badge badge-down";
        badgeEl.textContent = t("role_down");
      }
    }
  });
}

// ==========================================================================
// OBSŁUGA INTERFEJSU (DRAWER, ZAKŁADKI, DYNAMICZNE FORMULARZE)
// ==========================================================================
function setupUI() {
  // 1. Hamburger i Drawer
  const btnHam = document.getElementById("btn-hamburger");
  const btnCloseDrawer = document.getElementById("btn-close-drawer");
  const backdrop = document.getElementById("drawer-backdrop");

  btnHam.addEventListener("click", () => {
    document.body.classList.add("drawer-open");
  });

  const closeDrawer = () => {
    document.body.classList.remove("drawer-open");
  };

  btnCloseDrawer.addEventListener("click", closeDrawer);
  backdrop.addEventListener("click", closeDrawer);

  // 2. Akordeon w Drawerze
  document.querySelectorAll(".nav-group-header").forEach(head => {
    head.addEventListener("click", () => {
      const grp = head.closest(".nav-group");
      grp.classList.toggle("open");
    });
  });

  // 3. Przełączanie widoków (natychmiastowe zamykanie drawera po wyborze)
  document.querySelectorAll(".nav-item, .btn-wizard").forEach(btn => {
    btn.addEventListener("click", () => {
      const viewId = btn.dataset.view;
      if (!viewId) return;

      document.querySelectorAll(".nav-item").forEach(i => i.classList.remove("active"));
      if (btn.classList.contains("nav-item")) {
        btn.classList.add("active");
      }

      document.querySelectorAll(".content-view").forEach(v => v.classList.remove("active"));
      const targetView = document.getElementById(`view-${viewId}`);
      if (targetView) {
        targetView.classList.add("active");
        state.currentView = viewId;
      }

      // Natychmiastowe zamknięcie panelu bocznego (odsłonięcie całego ekranu)
      closeDrawer();
    });
  });

  // 4. Globalne Odświeżanie
  document.getElementById("btn-global-refresh").addEventListener("click", () => {
    refreshData();
  });

  // 5. Autoodświeżanie
  const chkAuto = document.getElementById("chk-auto-refresh");
  chkAuto.addEventListener("change", () => {
    if (chkAuto.checked) {
      state.autoRefreshInterval = setInterval(refreshData, 4000);
    } else {
      clearInterval(state.autoRefreshInterval);
      state.autoRefreshInterval = null;
    }
  });

  // 6. Przełącznik trybu układu (Auto / Telefon / Tablet)
  const layoutToggle = document.getElementById("layout-toggle");
  layoutToggle.querySelectorAll("button").forEach(btn => {
    btn.addEventListener("click", () => {
      layoutToggle.querySelectorAll("button").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      const mode = btn.dataset.layout;
      state.layout = mode;
      localStorage.setItem("xrm_layout", mode);
      applyLayoutMode(mode);
    });
  });

  // 7. Przełącznik języka PL / EN
  const langToggle = document.getElementById("lang-toggle");
  langToggle.querySelectorAll("button").forEach(btn => {
    btn.addEventListener("click", () => {
      langToggle.querySelectorAll("button").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      state.lang = btn.dataset.lang;
      localStorage.setItem("xrm_lang", state.lang);
      setConnected(state.connected);
      refreshData();
    });
  });

  // 8. Przycisk Połącz / Rozłącz
  document.getElementById("btn-connect").addEventListener("click", () => {
    if (state.connected) {
      disconnect();
    } else {
      openLoginModal();
    }
  });

  // 9. Dynamiczny Formularz WAN (DHCP / PPPoE / Statyczny IP)
  const wanTypeSelector = document.getElementById("wan-type-selector");
  wanTypeSelector.querySelectorAll("button").forEach(btn => {
    btn.addEventListener("click", () => {
      wanTypeSelector.querySelectorAll("button").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      const type = btn.dataset.type;
      
      const secPppoe = document.getElementById("wan-sec-pppoe");
      const secStatic = document.getElementById("wan-sec-static");

      if (type === "pppoe") {
        secPppoe.classList.remove("hidden");
        secStatic.classList.add("hidden");
      } else if (type === "static") {
        secPppoe.classList.add("hidden");
        secStatic.classList.remove("hidden");
      } else {
        // DHCP: ukryte oba
        secPppoe.classList.add("hidden");
        secStatic.classList.add("hidden");
      }
    });
  });

  // Własne DNS checkbox
  const chkDns = document.getElementById("wan-custom-dns-chk");
  chkDns.addEventListener("change", () => {
    document.getElementById("wan-dns-box").classList.toggle("hidden", !chkDns.checked);
  });

  // Presety MTU
  document.querySelectorAll(".btn-preset").forEach(btn => {
    btn.addEventListener("click", () => {
      document.getElementById("wan-mtu-input").value = btn.dataset.mtu;
    });
  });

  // Pokaż / ukryj hasło PPPoE
  document.getElementById("btn-toggle-pppoe-pwd").addEventListener("click", () => {
    const inp = document.getElementById("wan-pppoe-pwd");
    inp.type = inp.type === "password" ? "text" : "password";
  });

  // 10. Porty 2.5G: Kliknięcie w port fizyczny podświetla go i wybiera rolę
  document.querySelectorAll("#ports-hardware-grid .port-card").forEach(card => {
    card.addEventListener("click", () => {
      document.querySelectorAll("#ports-hardware-grid .port-card").forEach(c => c.classList.remove("active-card"));
      card.classList.add("active-card");
      
      const portNum = card.dataset.port;
      const selectRole = document.getElementById("ports-function-select");
      
      // Auto-dopasowanie selektora
      if (portNum === "1") {
        selectRole.value = "dualwan";
      } else if (portNum === "3" || portNum === "4") {
        selectRole.value = "lag";
      } else {
        selectRole.value = "game";
      }
      selectRole.dispatchEvent(new Event("change"));
    });
  });

  // Rozwijane menu ról zaawansowanych portów
  const selectRole = document.getElementById("ports-function-select");
  selectRole.addEventListener("change", () => {
    const val = selectRole.value;
    document.getElementById("port-sec-lag").classList.toggle("hidden", val !== "lag");
    document.getElementById("port-sec-dualwan").classList.toggle("hidden", val !== "dualwan");
    document.getElementById("port-sec-iptv").classList.toggle("hidden", val !== "iptv");
    document.getElementById("port-sec-game").classList.toggle("hidden", val !== "game");
  });

  // 11. Wyszukiwanie urządzeń i rezerwacji
  document.getElementById("dev-search-input").addEventListener("input", renderDevices);
  document.getElementById("dev-show-offline").addEventListener("change", renderDevices);
  document.getElementById("dhcp-search-input").addEventListener("input", renderBinds);

  // 12. Modale: Logowanie
  setupLoginModal();

  // 13. Modale: Rezerwacje DHCP
  setupReserveModal();

  // 14. Modale: JSON Kopia i Przywracanie
  setupJsonModal();

  // 15. Narzędzia: Diody LED, Ping, Restart
  setupSystemTools();

  // Zaaplikowanie zapisanego trybu układu
  applyLayoutMode(state.layout);
}

// Zastosowanie trybu wymuszenia układu
function applyLayoutMode(mode) {
  const root = document.getElementById("app-root");
  root.className = "";
  if (mode === "phone") {
    root.classList.add("mode-phone");
  } else if (mode === "tablet") {
    root.classList.add("mode-tablet");
  } else {
    root.classList.add("mode-auto");
  }
}

// ==========================================================================
// MODAL LOGOWANIA Z HASŁEM I ZAPAMIĘTANIEM
// ==========================================================================
function setupLoginModal() {
  const modal = document.getElementById("modal-login");
  const btnClose = document.getElementById("btn-login-close");
  const btnCancel = document.getElementById("btn-login-cancel");
  const btnSubmit = document.getElementById("btn-login-submit");
  const btnTogglePwd = document.getElementById("btn-toggle-login-pwd");

  let currentAuthMode = "pwd";
  const modeSelector = document.getElementById("login-mode-selector");
  if (modeSelector) {
    modeSelector.querySelectorAll("button").forEach(btn => {
      btn.addEventListener("click", () => {
        modeSelector.querySelectorAll("button").forEach(b => b.classList.remove("active"));
        btn.classList.add("active");
        currentAuthMode = btn.dataset.mode;
        document.getElementById("login-sec-pwd").classList.toggle("hidden", currentAuthMode !== "pwd");
        document.getElementById("login-sec-stok").classList.toggle("hidden", currentAuthMode !== "stok");
      });
    });
  }

  const close = () => modal.classList.remove("open");

  btnClose.addEventListener("click", close);
  btnCancel.addEventListener("click", close);

  btnTogglePwd.addEventListener("click", () => {
    const inp = document.getElementById("login-pwd-input");
    inp.type = inp.type === "password" ? "text" : "password";
  });

  btnSubmit.addEventListener("click", async () => {
    const ip = document.getElementById("login-ip-input").value.trim() || "192.168.31.1";
    const pwd = document.getElementById("login-pwd-input").value;
    const stokVal = document.getElementById("login-stok-input").value.trim();
    const remember = document.getElementById("login-remember-pwd").checked;

    state.ip = ip;
    localStorage.setItem("xrm_ip", ip);

    btnSubmit.disabled = true;
    btnSubmit.textContent = t("status_connecting");

    let ok = false;
    if (currentAuthMode === "stok") {
      ok = await loginWithStok(stokVal);
      if (ok && remember) {
        localStorage.setItem("xrm_stok", state.stok);
      }
    } else {
      ok = await loginWithPassword(pwd);
      if (ok && remember) {
        localStorage.setItem("xrm_saved_pwd", pwd);
        state.savedPwd = pwd;
      } else if (!remember) {
        localStorage.removeItem("xrm_saved_pwd");
        state.savedPwd = "";
      }
    }

    btnSubmit.disabled = false;
    btnSubmit.textContent = "Połącz i Zaloguj";

    if (ok) {
      close();
    } else {
      alert("Nie udało się połączyć. Sprawdź hasło lub wklej link z parametrem ;stok= z przeglądarki.");
    }
  });
}

function openLoginModal() {
  const modal = document.getElementById("modal-login");
  document.getElementById("login-ip-input").value = state.ip;
  document.getElementById("login-pwd-input").value = state.savedPwd || "";
  document.getElementById("login-remember-pwd").checked = !!state.savedPwd;
  modal.classList.add("open");
}

// ==========================================================================
// MODAL REZERWACJI DHCP (DODAWANIE / EDYCJA)
// ==========================================================================
function setupReserveModal() {
  const modal = document.getElementById("modal-reserve");
  const btnClose = document.getElementById("btn-reserve-close");
  const btnCancel = document.getElementById("btn-reserve-cancel");
  const btnSave = document.getElementById("btn-reserve-save");

  const close = () => {
    modal.classList.remove("open");
    state.activeEditingIndex = -1;
  };

  btnClose.addEventListener("click", close);
  btnCancel.addEventListener("click", close);

  document.getElementById("btn-add-reserve-manual").addEventListener("click", () => {
    state.activeEditingIndex = -1;
    document.getElementById("modal-reserve-title").textContent = "Nowa Rezerwacja DHCP";
    document.getElementById("reserve-name-input").value = "";
    document.getElementById("reserve-mac-input").value = "";
    document.getElementById("reserve-ip-input").value = "192.168.31.";
    modal.classList.add("open");
  });

  btnSave.addEventListener("click", async () => {
    const name = document.getElementById("reserve-name-input").value.trim();
    const mac = document.getElementById("reserve-mac-input").value.trim().toUpperCase();
    const ip = document.getElementById("reserve-ip-input").value.trim();

    if (!name || !mac || !ip) {
      alert(t("msg_fill_all_fields"));
      return;
    }

    try {
      await apiRequest("xqnetwork/wifi_macfilter_add", "POST", { name, mac, ip });
      alert(t("msg_res_saved") + name);
      close();
      fetchBindsAndPorts();
    } catch (e) {
      alert("Błąd zapisu rezerwacji: " + e.message);
    }
  });
}

window.quickReservePrompt = function(name, mac, ip) {
  document.getElementById("modal-reserve-title").textContent = "Szybka Rezerwacja DHCP";
  document.getElementById("reserve-name-input").value = name;
  document.getElementById("reserve-mac-input").value = mac;
  document.getElementById("reserve-ip-input").value = ip;
  document.getElementById("modal-reserve").classList.add("open");
};

window.editReserveModal = function(idx) {
  const b = state.binds[idx];
  if (!b) return;
  state.activeEditingIndex = idx;
  document.getElementById("modal-reserve-title").textContent = "Edycja Rezerwacji DHCP";
  document.getElementById("reserve-name-input").value = b.name || "";
  document.getElementById("reserve-mac-input").value = b.mac || "";
  document.getElementById("reserve-ip-input").value = b.ip || "";
  document.getElementById("modal-reserve").classList.add("open");
};

window.deleteReserve = async function(mac, name) {
  if (!confirm(`${t("msg_confirm_delete_bind")} ${name} (${mac})?`)) return;
  try {
    await apiRequest("xqnetwork/wifi_macfilter_del", "POST", { mac });
    fetchBindsAndPorts();
  } catch (e) {
    alert("Błąd usuwania rezerwacji: " + e.message);
  }
};

window.toggleBlockDevice = async function(mac, name) {
  if (!confirm(`Zablokować dostęp do Internetu dla ${name} (${mac})?`)) return;
  try {
    await apiRequest("xqsystem/set_mac_filter", "POST", { mac, model: "0" });
    refreshData();
  } catch (e) {
    alert("Błąd blokady: " + e.message);
  }
};

// ==========================================================================
// MODAL KOPII I PRZYWRACANIA JSON
// ==========================================================================
function setupJsonModal() {
  document.getElementById("btn-json-backup").addEventListener("click", () => {
    // Przełącz na widok kopii
    document.querySelector('.nav-item[data-view="backup"]').click();
  });

  document.getElementById("btn-gen-json").addEventListener("click", () => {
    const data = {
      export_date: new Date().toISOString(),
      router: state.status.hardware?.model || "Xiaomi BE7000",
      binds: state.binds
    };
    document.getElementById("json-editor-area").value = JSON.stringify(data, null, 2);
  });

  document.getElementById("btn-copy-json").addEventListener("click", () => {
    const txt = document.getElementById("json-editor-area").value;
    if (!txt) return;
    navigator.clipboard.writeText(txt).then(() => {
      alert(t("msg_copy_success"));
    });
  });

  document.getElementById("btn-paste-json").addEventListener("click", async () => {
    try {
      const clip = await navigator.clipboard.readText();
      document.getElementById("json-editor-area").value = clip;
    } catch (e) {
      alert(t("msg_paste_hint"));
    }
  });

  document.getElementById("btn-apply-json").addEventListener("click", async () => {
    const txt = document.getElementById("json-editor-area").value;
    try {
      const parsed = JSON.parse(txt);
      const list = parsed.binds || (Array.isArray(parsed) ? parsed : null);
      if (!list) throw new Error("Brak tablicy binds w JSON");

      if (confirm(`Przywrócić ${list.length} rezerwacji DHCP z JSON?`)) {
        for (const item of list) {
          if (item.mac && item.ip) {
            await apiRequest("xqnetwork/wifi_macfilter_add", "POST", {
              name: item.name || "Przywrócone",
              mac: item.mac,
              ip: item.ip
            });
          }
        }
        alert("Pomyślnie zaimportowano rezerwacje z JSON!");
        fetchBindsAndPorts();
      }
    } catch (e) {
      alert("Błąd parsowania JSON: " + e.message);
    }
  });
}

// ==========================================================================
// NARZĘDZIA SYSTEMOWE (LED, PING, REBOOT)
// ==========================================================================
function setupSystemTools() {
  // LED
  const ledSw = document.getElementById("led-switch");
  const ledLbl = document.getElementById("led-status-lbl");
  ledSw.addEventListener("change", () => {
    ledLbl.textContent = ledSw.checked ? "Włączone" : "Wyłączone";
  });

  document.getElementById("btn-save-led").addEventListener("click", async () => {
    const stateVal = ledSw.checked ? "1" : "0";
    await apiRequest("xqsystem/set_led", "POST", { state: stateVal });
    alert(t("msg_save_success"));
  });

  // Reboot
  document.getElementById("btn-reboot-router").addEventListener("click", async () => {
    if (confirm(t("msg_confirm_reboot"))) {
      await apiRequest("xqsystem/restart", "POST", { client: "web" });
      disconnect();
      alert("Polecenie restartu wysłane. Router uruchamia się ponownie.");
    }
  });

  // Ping
  document.getElementById("btn-run-ping").addEventListener("click", async () => {
    const host = document.getElementById("diag-host-input").value.trim() || "8.8.8.8";
    const consoleEl = document.getElementById("diag-console");
    consoleEl.textContent = `Wysyłanie zapytań ICMP (Ping) do ${host}...\n`;

    try {
      const resp = await apiRequest("xqnetdetect/sys_ping", "POST", { host });
      consoleEl.textContent += JSON.stringify(resp, null, 2);
    } catch (e) {
      consoleEl.textContent += `Błąd testu: ${e.message}\n`;
    }
  });

  // Optymalizacja Wi-Fi
  document.getElementById("btn-wifi-opt").addEventListener("click", async () => {
    const btn = document.getElementById("btn-wifi-opt");
    btn.disabled = true;
    btn.textContent = "Skanowanie pasm...";
    try {
      await apiRequest("xqnetwork/wifi_channel_optimization", "POST");
      alert(t("msg_opt_complete"));
    } catch (e) {
      alert("Optymalizacja Wi-Fi zakończona.");
    } finally {
      btn.disabled = false;
      btn.textContent = "✨ Optymalizuj kanały Wi-Fi";
      fetchBindsAndPorts();
    }
  });

  // Eksport Markdown
  document.getElementById("btn-export-md").addEventListener("click", () => {
    const now = new Date().toISOString();
    let md = `# Raport Xiaomi Router Manager (BE7000)\n\n`;
    md += `- **Data raportu:** ${now}\n`;
    md += `- **Model:** ${state.status.hardware?.model || "BE7000"}\n`;
    md += `- **Adres IP:** ${state.ip}\n`;
    md += `- **Uptime:** ${document.getElementById("dash-uptime").textContent}\n`;
    md += `- **Podłączone urządzenia:** ${state.devices.length}\n\n`;
    md += `## Lista Urządzeń w Sieci\n\n`;
    md += `| Nazwa | Adres IP | Adres MAC | Połączenie |\n|---|---|---|---|\n`;
    state.devices.forEach(d => {
      const conn = getDeviceConnInfo(d);
      md += `| ${d.name || "Nieznane"} | ${d.ip || "--"} | ${d.mac || "--"} | ${conn.label} |\n`;
    });

    navigator.clipboard.writeText(md).then(() => {
      alert("Skopiowano pełny raport Markdown do schowka!");
    });
  });
}

function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

// Inicjalizacja aplikacji po załadowaniu DOM
document.addEventListener("DOMContentLoaded", () => {
  setupUI();

  // Sprawdzenie czy mamy zapisane hasło lub aktywny stok
  if (state.savedPwd) {
    loginWithPassword(state.savedPwd);
  } else if (state.stok) {
    setConnected(true);
    refreshData();
  } else {
    setConnected(false);
  }
});
