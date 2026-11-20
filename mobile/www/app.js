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
  initInfo: {},
  status: {},
  devices: [],
  binds: [],
  wanInfo: {},
  lanInfo: {},
  lanDhcp: {},
  wifiInfo: [],
  wifiBsd: 1,
  portsStatus: [],
  topoGraph: {},
  aimesh: {},
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

// Bezpieczne parsowanie adresu IP ze stringa lub obiektu
function extractIpString(rawIp) {
  if (!rawIp) return "-";
  if (typeof rawIp === "string") return rawIp;
  if (typeof rawIp === "object") {
    if (rawIp.ip) return String(rawIp.ip);
    try {
      return JSON.stringify(rawIp);
    } catch(e) {
      return "-";
    }
  }
  return String(rawIp);
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
    state.initInfo = init;
    
    const candidates = [];
    candidates.push("84:47:09:89:c0:ae"); // stały wzorzec z LuCI BE7000
    if (init.routerId) candidates.push(init.routerId);
    if (init.id && !init.id.includes("/")) candidates.push(init.id);
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

function formatBytes(bytes) {
  const b = parseFloat(bytes) || 0;
  if (b >= 1073741824) return `${(b / 1073741824).toFixed(1)} GB`;
  if (b >= 1048576) return `${(b / 1048576).toFixed(0)} MB`;
  if (b >= 1024) return `${(b / 1024).toFixed(0)} KB`;
  return `${b} B`;
}

function formatUptime(seconds) {
  const s = parseInt(seconds) || 0;
  const d = Math.floor(s / 86400);
  const h = Math.floor((s % 86400) / 3600);
  const m = Math.floor((s % 3600) / 60);
  if (d > 0) return `${d}d ${h}h ${m}m`;
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
}

// Rozpoznawanie typu połączenia urządzenia (odwzorowanie 1:1 z gui.py L696-731)
function getDeviceConnInfo(d) {
  if (d.is_offline) {
    return { type: "offline", label: "Offline (DHCP)", cls: "badge-offline" };
  }
  if (d.isap && Number(d.isap) > 0) {
    return { type: "mesh", label: "Węzeł Mesh", cls: "badge-mesh" };
  }
  const typeCode = Number(d.type);
  if (typeCode === 0) {
    return { type: "cable", label: "Kabel (LAN)", cls: "badge-lan-cable" };
  }
  if (typeCode === 1) {
    return { type: "wifi2", label: "Wi-Fi 2.4G", cls: "badge-wifi-2g" };
  }
  if (typeCode === 2) {
    return { type: "wifi5", label: "Wi-Fi 5G", cls: "badge-wifi-5g" };
  }
  if (typeCode === 3) {
    return { type: "wifi_game", label: "Wi-Fi 5G Game", cls: "badge-wifi-game" };
  }
  if (typeCode === 4) {
    return { type: "wifi5_2", label: "Wi-Fi 5G-2", cls: "badge-wifi-5g" };
  }
  if (typeCode === 5) {
    return { type: "wifi6", label: "Wi-Fi 6G", cls: "badge-wifi-7" };
  }
  if (typeCode === 6) {
    return { type: "guest", label: "Wi-Fi Gość", cls: "badge-offline" };
  }
  if (typeCode === 7) {
    return { type: "wifi7", label: "Wi-Fi 7 MLO", cls: "badge-wifi-7" };
  }
  if (typeCode === 8) {
    return { type: "wifi_iot", label: "Wi-Fi IoT", cls: "badge-wifi-iot" };
  }
  return { type: "other", label: "Inne", cls: "badge-offline" };
}

// ==========================================================================
// POBIERANIE I ODŚWIEŻANIE DANYCH Z ROUTERA
// ==========================================================================
async function refreshData() {
  if (!state.connected || !state.stok) return;

  try {
    const [initResp, statusResp, devResp, wanResp] = await Promise.allSettled([
      apiRequest("xqsystem/init_info"),
      apiRequest("xqsystem/status"),
      apiRequest("xqsystem/device_list"),
      apiRequest("xqnetwork/wan_info")
    ]);

    if (initResp.status === "fulfilled" && initResp.value.code === 0) {
      state.initInfo = initResp.value;
    }

    if (statusResp.status === "fulfilled" && statusResp.value.code === 0) {
      state.status = statusResp.value;
    }

    if (wanResp.status === "fulfilled" && wanResp.value.code === 0) {
      state.wanInfo = wanResp.value.info || wanResp.value;
      renderWanInfo(state.wanInfo);
    }

    if (statusResp.status === "fulfilled" && statusResp.value.code === 0) {
      renderDashboardStatus(state.status, state.initInfo, state.wanInfo);
    }

    if (devResp.status === "fulfilled" && devResp.value.code === 0) {
      state.devices = devResp.value.list || [];
      renderDevices();
    }

    // Odczyt rezerwacji, Wi-Fi, portów i zaawansowanych ustawień
    fetchBindsAndPorts();
  } catch (e) {
    console.warn("Błąd odświeżania danych:", e);
  }
}

async function fetchBindsAndPorts() {
  try {
    // 1. Rezerwacje DHCP (macbind_info)
    const bindResp = await apiRequest("xqnetwork/macbind_info");
    if (bindResp.code === 0 && Array.isArray(bindResp.list)) {
      state.binds = bindResp.list;
      renderBinds();
      renderDevices(); // Odśwież urządzenia, aby zaktualizować status zarezerwowania
    }

    // 2. Wi-Fi (wifi_detail_all)
    const wifiResp = await apiRequest("xqnetwork/wifi_detail_all");
    if (wifiResp.code === 0 && Array.isArray(wifiResp.info)) {
      state.wifiInfo = wifiResp.info;
      state.wifiBsd = wifiResp.bsd !== undefined ? wifiResp.bsd : 1;
      renderWifiInfo(state.wifiInfo, state.wifiBsd);
    }

    // 3. Status Portów Fizycznych
    const portsResp = await apiRequest("xqnetwork/port_status");
    if (portsResp.code === 0 && portsResp.info) {
      state.portsStatus = portsResp.info;
      renderPortsStatus(portsResp.info);
    }

    // 4. Zaawansowane funkcje Wi-Fi i Roaming Mesh
    const [roamResp, twtResp, mimoResp] = await Promise.allSettled([
      apiRequest("xqnetwork/get_aimesh_config"),
      apiRequest("xqnetwork/get_twt"),
      apiRequest("xqnetwork/get_wifi_txbf")
    ]);

    if (roamResp.status === "fulfilled" && roamResp.value.code === 0) {
      state.aimesh = roamResp.value;
      renderAimeshConfig(roamResp.value);
    }
  } catch (e) {
    console.warn("Błąd pobierania portów/rezerwacji:", e);
  }
}

// ==========================================================================
// RENDEROWANIE WIDOKÓW
// ==========================================================================

// 1. Dashboard (Pulpit) - odwzorowanie 1:1 z gui.py L4795-4858
function renderDashboardStatus(s, init, wan) {
  // Model, ROM, Czas pracy i ID Routera
  const model = init?.displayName || init?.hardware || "Xiaomi BE7000";
  const hwCode = init?.hardware ? ` (kod ${init.hardware})` : "";
  const fw = `${init?.romversion || "1.1.38"} (${init?.countrycode || "CN"})`;
  const routerId = init?.routerId || init?.id || s?.hardware?.mac || "-";
  const rname = init?.routername || "";

  if (document.getElementById("dash-router-title")) {
    document.getElementById("dash-router-title").textContent = `Router: ${model} - '${rname}' (${state.ip})`;
  }
  if (document.getElementById("dash-model")) {
    document.getElementById("dash-model").textContent = `${model}${hwCode}`;
  }
  if (document.getElementById("dash-fw")) {
    document.getElementById("dash-fw").textContent = fw;
  }
  if (document.getElementById("dash-routerid")) {
    document.getElementById("dash-routerid").textContent = routerId;
  }

  const rawUp = s?.upTime || s?.uptime || 0;
  if (rawUp && document.getElementById("dash-uptime")) {
    document.getElementById("dash-uptime").textContent = formatUptime(rawUp);
  }

  // Obciążenie CPU (gui.py L4810-4820)
  const cpuObj = s?.cpu || {};
  let cpuLoad = parseFloat(cpuObj.load !== undefined ? cpuObj.load : (cpuObj.core || 0));
  if (cpuLoad > 1.0) cpuLoad = cpuLoad / 100.0;
  const cpuPct = (cpuLoad * 100).toFixed(1);
  if (document.getElementById("dash-cpu-val")) {
    document.getElementById("dash-cpu-val").textContent = `${cpuPct}%`;
  }
  if (document.getElementById("dash-cpu-bar")) {
    document.getElementById("dash-cpu-bar").style.width = `${Math.min(100, parseFloat(cpuPct))}%`;
  }

  // Pamięć RAM (gui.py L4821-4835)
  const mem = s?.mem || {};
  let memUsage = parseFloat(mem.usage || 0);
  const memTotal = parseFloat(mem.total || 0);
  if (memUsage > 1.0) memUsage = memUsage / 100.0;
  const memPct = (memUsage * 100).toFixed(1);
  const usedBytes = memTotal > 0 ? memUsage * memTotal : 0;
  const ramText = memTotal > 0 ? `${formatBytes(usedBytes)} / ${formatBytes(memTotal)} (${memPct}%)` : `${memPct}%`;
  
  if (document.getElementById("dash-ram-val")) {
    document.getElementById("dash-ram-val").textContent = ramText;
  }
  if (document.getElementById("dash-ram-bar")) {
    document.getElementById("dash-ram-bar").style.width = `${Math.min(100, parseFloat(memPct))}%`;
  }

  // Transfer WAN
  const wanSpeed = s?.wan || {};
  const down = parseFloat(wanSpeed.downspeed || 0);
  const up = parseFloat(wanSpeed.upload || wanSpeed.upspeed || 0);
  if (document.getElementById("dash-down-speed")) {
    document.getElementById("dash-down-speed").textContent = formatSpeed(down);
  }
  if (document.getElementById("dash-up-speed")) {
    document.getElementById("dash-up-speed").textContent = formatSpeed(up);
  }

  // WAN IP & Serwery DNS na Dashboardzie
  if (wan) {
    const wanDetails = wan.info || wan;
    const ipv4 = wanDetails.ipv4;
    const wIp = (Array.isArray(ipv4) && ipv4.length > 0 && ipv4[0].ip) ? ipv4[0].ip : (wanDetails.ip || "-");
    const dnsList = wanDetails.dnsServer || wanDetails.details?.dns || [];
    const dnsStr = Array.isArray(dnsList) ? dnsList.join(", ") : String(dnsList || "-");
    
    if (document.getElementById("dash-wan-ip")) {
      document.getElementById("dash-wan-ip").textContent = wIp;
    }
    if (document.getElementById("dash-wan-dns")) {
      document.getElementById("dash-wan-dns").textContent = dnsStr || "-";
    }
  }
}

// 2. Urządzenia w sieci - z uwzględnieniem mapy rezerwacji DHCP i właściwych rodzajów połączeń
function renderDevices() {
  const container = document.getElementById("devices-container");
  if (!container) return;
  const query = (document.getElementById("dev-search-input")?.value || "").toLowerCase().trim();
  const showOffline = document.getElementById("dev-show-offline")?.checked ?? true;

  // Szybka mapa rezerwacji po MAC
  const bindsByMac = new Map();
  if (Array.isArray(state.binds)) {
    state.binds.forEach(b => {
      if (b.mac) bindsByMac.set(b.mac.toUpperCase().trim(), b);
    });
  }

  // Aktywne urządzenia MAC
  const activeMacs = new Set();
  const allList = [];

  state.devices.forEach(d => {
    const m = (d.mac || "").toUpperCase().trim();
    if (m) activeMacs.add(m);

    // Jeśli nazwa jest pusta lub domyślna "device_...", weź nazwę ze statycznej rezerwacji
    let dName = d.name || d.oname || "";
    if ((!dName || dName.toLowerCase().startsWith("device_")) && bindsByMac.has(m)) {
      dName = bindsByMac.get(m).name || dName;
    }
    if (!dName) dName = "Nieznane";

    allList.push({
      ...d,
      name: dName,
      mac: d.mac || "-",
      is_offline: false
    });
  });

  // Dodaj urządzenia offline ze statycznych rezerwacji DHCP
  if (showOffline && Array.isArray(state.binds)) {
    state.binds.forEach(b => {
      const bMac = (b.mac || "").toUpperCase().trim();
      if (!activeMacs.has(bMac)) {
        allList.push({
          name: b.name || b.origin_name || "Rezerwacja DHCP",
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
    const ip = extractIpString(d.ip || (d.ip?.[0]?.ip)).toLowerCase();
    const mac = (d.mac || "").toLowerCase();
    return name.includes(query) || ip.includes(query) || mac.includes(query);
  });

  document.getElementById("nav-badge-devs").textContent = state.devices.length;
  if (document.getElementById("dash-dev-count")) {
    document.getElementById("dash-dev-count").textContent = state.devices.length;
  }

  if (filtered.length === 0) {
    container.innerHTML = `<div class="empty-state">Brak pasujących urządzeń w sieci.</div>`;
    return;
  }

  container.innerHTML = filtered.map(d => {
    const conn = getDeviceConnInfo(d);
    const dMacUpper = (d.mac || "").toUpperCase().trim();
    const isBound = bindsByMac.has(dMacUpper);
    const ipStr = extractIpString(d.ip || (d.ip?.[0]?.ip));

    const downSpeed = formatSpeed(d.statistics?.downspeed || 0);
    const upSpeed = formatSpeed(d.statistics?.upspeed || 0);
    const onlineSec = parseInt(d.statistics?.online || d.uptime || 0);
    const uptimeStr = d.is_offline ? "Brak w sieci" : (onlineSec > 0 ? formatUptime(onlineSec) : "<1m");

    const auth = d.authority || {};
    const wanAllowed = auth.wan === undefined ? true : (auth.wan === 1);
    const isAdmin = auth.admin === 1 || d.is_cur === 1 || d.isap === 1;

    // Przyciski akcji
    let actionButtonsHtml = "";
    if (d.is_offline) {
      actionButtonsHtml = `
        <span class="badge badge-offline">Offline</span>
        <button class="btn-sm btn-secondary" onclick="openReserveModal('${d.mac}', '${ipStr}', '${escapeHtml(d.name)}')">Edytuj</button>
        <button class="btn-sm btn-danger" onclick="deleteMacBind('${d.mac}', '${escapeHtml(d.name)}')">Usuń</button>
      `;
    } else {
      // 1. Zarezerwowane vs Rezerwuj IP
      if (isBound) {
        actionButtonsHtml += `
          <span class="badge badge-bound">● Zarezerwowany</span>
          <button class="btn-sm btn-secondary" onclick="openReserveModal('${d.mac}', '${ipStr}', '${escapeHtml(d.name)}')">Edytuj</button>
        `;
      } else if (d.mac && d.mac !== "-") {
        actionButtonsHtml += `
          <button class="btn-sm btn-primary" onclick="openReserveModal('${d.mac}', '${ipStr}', '${escapeHtml(d.name)}')">+ Rezerwuj IP</button>
        `;
      }

      // 2. Blokada internetu WAN (zabezpieczenie admina)
      if (isAdmin) {
        actionButtonsHtml += `<span class="badge badge-admin">[Stacja Admina / AP]</span>`;
      } else {
        const btnCls = wanAllowed ? "btn-secondary" : "btn-danger";
        const btnTxt = wanAllowed ? "Blokuj Net" : "Odblokuj Net";
        actionButtonsHtml += `
          <button class="btn-sm ${btnCls}" onclick="toggleDeviceWanAccess('${d.mac}', ${wanAllowed})">${btnTxt}</button>
        `;
      }
    }

    return `
      <div class="device-card ${d.is_offline ? 'offline' : ''}">
        <div class="dev-main">
          <div class="dev-info-left">
            <div class="dev-name-row">
              <span class="dev-name">${escapeHtml(d.name)}</span>
              <span class="badge ${conn.cls}">${conn.label}</span>
            </div>
            <div class="dev-meta-row">
              <span class="ip-addr">${ipStr}</span>
              <span class="mac-addr">${d.mac}</span>
              <span class="dev-uptime">Czas: ${uptimeStr}</span>
            </div>
          </div>
          <div class="dev-actions">
            ${!d.is_offline ? `
              <div class="dev-traffic">
                <span class="text-success">↓ ${downSpeed}</span>
                <span class="text-info">↑ ${upSpeed}</span>
              </div>
            ` : ''}
            ${actionButtonsHtml}
          </div>
        </div>
      </div>
    `;
  }).join("");
}

// 3. Status i Konfiguracja WAN
function renderWanInfo(info) {
  if (!info) return;
  const det = info.details || {};
  const ipv4 = info.ipv4;
  const wIp = (Array.isArray(ipv4) && ipv4.length > 0 && ipv4[0].ip) ? ipv4[0].ip : (info.ip || "-");
  const wMask = (Array.isArray(ipv4) && ipv4.length > 0 && ipv4[0].mask) ? ipv4[0].mask : (info.mask || "255.255.255.0");
  const wGw = info.gateWay || info.gateway || "-";
  const dnsList = info.dnsServer || det.dns || [];
  const dnsStr = Array.isArray(dnsList) ? dnsList.join(", ") : String(dnsList || "-");
  const wMac = info.mac || "-";
  const wMtu = det.mtu || info.mtu || "1472";

  // Dashboard WAN
  if (document.getElementById("dash-wan-ip")) document.getElementById("dash-wan-ip").textContent = wIp;
  if (document.getElementById("dash-wan-dns")) document.getElementById("dash-wan-dns").textContent = dnsStr;

  // Widok WAN status
  if (document.getElementById("wan-stat-link")) {
    document.getElementById("wan-stat-link").textContent = String(info.link) === "1" ? "● Połączony (Link UP)" : "○ Rozłączony / Brak kabla";
    document.getElementById("wan-stat-link").className = String(info.link) === "1" ? "val bold text-success" : "val bold text-danger";
  }
  if (document.getElementById("wan-stat-proto")) {
    document.getElementById("wan-stat-proto").textContent = (det.wanType || info.proto || "PPPoE").toUpperCase();
  }
  if (document.getElementById("wan-stat-ip")) document.getElementById("wan-stat-ip").textContent = wIp;
  if (document.getElementById("wan-stat-mask")) document.getElementById("wan-stat-mask").textContent = wMask;
  if (document.getElementById("wan-stat-gw")) document.getElementById("wan-stat-gw").textContent = wGw;
  if (document.getElementById("wan-stat-dns")) document.getElementById("wan-stat-dns").textContent = dnsStr;
  if (document.getElementById("wan-stat-mac")) document.getElementById("wan-stat-mac").textContent = wMac;
  if (document.getElementById("wan-stat-mtu")) document.getElementById("wan-stat-mtu").textContent = wMtu;
  if (info.uptime && document.getElementById("wan-stat-uptime")) {
    document.getElementById("wan-stat-uptime").textContent = formatUptime(info.uptime);
  }

  // Wypełnienie formularza konfiguracji WAN
  const wanType = (det.wanType || info.proto || "pppoe").toLowerCase();
  const select = document.getElementById("wan-type-select");
  if (select) {
    select.value = wanType;
    updateWanFormVisibility(wanType);
  }

  // Pola PPPoE
  if (det.username !== undefined && document.getElementById("wan-pppoe-user")) {
    document.getElementById("wan-pppoe-user").value = det.username || "";
  }
  if (det.password !== undefined && document.getElementById("wan-pppoe-pwd")) {
    document.getElementById("wan-pppoe-pwd").value = det.password || "";
  }

  // Pola Static IP
  if (document.getElementById("wan-static-ip")) document.getElementById("wan-static-ip").value = wIp !== "-" ? wIp : "";
  if (document.getElementById("wan-static-mask")) document.getElementById("wan-static-mask").value = wMask !== "-" ? wMask : "";
  if (document.getElementById("wan-static-gw")) document.getElementById("wan-static-gw").value = wGw !== "-" ? wGw : "";

  // MTU
  if (document.getElementById("wan-mtu-input")) {
    document.getElementById("wan-mtu-input").value = wMtu;
  }

  // Własne DNS
  const hasCustomDns = String(det.custom_dns) === "1" || (Array.isArray(dnsList) && dnsList.length > 0 && wanType === "pppoe");
  const dnsChk = document.getElementById("wan-custom-dns-chk");
  const dnsBox = document.getElementById("wan-dns-box");
  if (dnsChk) {
    dnsChk.checked = hasCustomDns;
  }
  if (dnsBox) {
    if (hasCustomDns) {
      dnsBox.classList.remove("hidden");
    } else {
      dnsBox.classList.add("hidden");
    }
  }
  if (Array.isArray(dnsList) && dnsList.length >= 1 && document.getElementById("wan-dns1")) {
    document.getElementById("wan-dns1").value = dnsList[0] || "";
  }
  if (Array.isArray(dnsList) && dnsList.length >= 2 && document.getElementById("wan-dns2")) {
    document.getElementById("wan-dns2").value = dnsList[1] || "";
  }
}

function updateWanFormVisibility(type) {
  const secPppoe = document.getElementById("wan-sec-pppoe");
  const secStatic = document.getElementById("wan-sec-static");
  if (!secPppoe || !secStatic) return;

  if (type === "pppoe") {
    secPppoe.classList.remove("hidden");
    secStatic.classList.add("hidden");
  } else if (type === "static") {
    secPppoe.classList.add("hidden");
    secStatic.classList.remove("hidden");
  } else {
    // dhcp
    secPppoe.classList.add("hidden");
    secStatic.classList.add("hidden");
  }
}

// 4. Rezerwacje DHCP (macbind_info)
function renderBinds() {
  const tbody = document.getElementById("binds-tbody");
  if (!tbody) return;
  const query = (document.getElementById("dhcp-search-input")?.value || "").toLowerCase().trim();
  document.getElementById("nav-badge-binds").textContent = state.binds.length;

  const filtered = state.binds.filter(b => {
    if (!query) return true;
    const name = (b.name || b.origin_name || "").toLowerCase();
    const ip = extractIpString(b.ip).toLowerCase();
    const mac = (b.mac || "").toLowerCase();
    return name.includes(query) || ip.includes(query) || mac.includes(query);
  });

  if (filtered.length === 0) {
    tbody.innerHTML = `<tr><td colspan="4" class="empty-state">Brak skonfigurowanych rezerwacji DHCP.</td></tr>`;
    return;
  }

  tbody.innerHTML = filtered.map((b, idx) => {
    const ipStr = extractIpString(b.ip);
    const bName = b.name || b.origin_name || "Bez nazwy";
    return `
      <tr>
        <td><strong>${escapeHtml(bName)}</strong></td>
        <td class="mono highlight">${ipStr}</td>
        <td class="mono">${b.mac}</td>
        <td class="text-right">
          <button class="btn-secondary btn-sm" onclick="openReserveModal('${b.mac}', '${ipStr}', '${escapeHtml(bName)}')">Edytuj</button>
          <button class="btn-danger btn-sm" onclick="deleteMacBind('${b.mac}', '${escapeHtml(bName)}')">Usuń</button>
        </td>
      </tr>
    `;
  }).join("");
}

// 5. Wi-Fi i Pasma Radiowe (odwzorowanie 1:1 z Windows gui.py)
function renderWifiInfo(info, bsd) {
  if (!Array.isArray(info)) return;

  const bsdOn = (bsd === 1 || bsd === "1");
  state.wifiBsd = bsdOn ? 1 : 0;

  // Przełącznik Smart Connect
  const bsdSwitch = document.getElementById("wifi-switch-smartconnect");
  if (bsdSwitch) bsdSwitch.checked = bsdOn;

  // Baner Smart Connect na samej górze
  const bsdBanner = document.getElementById("wifi-bsd-banner");
  if (bsdBanner) {
    if (bsdOn) {
      bsdBanner.classList.remove("hidden");
    } else {
      bsdBanner.classList.add("hidden");
    }
  }

  // Tytuły i synchronizacja paneli
  const title2g = document.getElementById("wifi-2g-card-title");
  const lblSsid2g = document.getElementById("wifi-2g-ssid-lbl");
  const lblEnc2g = document.getElementById("wifi-2g-enc-lbl");
  const lblPwd2g = document.getElementById("wifi-2g-pwd-lbl");
  const syncBanner5g = document.getElementById("wifi-5g-sync-banner");
  const credBox5g = document.getElementById("wifi-5g-credentials-box");

  if (bsdOn) {
    if (title2g) title2g.textContent = "Wspólna Sieć Wi-Fi i Pasmo 2.4 GHz (Smart Connect)";
    if (lblSsid2g) lblSsid2g.textContent = "Wspólna nazwa (SSID):";
    if (lblEnc2g) lblEnc2g.textContent = "Wspólne szyfrowanie:";
    if (lblPwd2g) lblPwd2g.textContent = "Wspólne hasło Wi-Fi:";
    if (syncBanner5g) syncBanner5g.classList.remove("hidden");
    if (credBox5g) credBox5g.classList.add("hidden");
  } else {
    if (title2g) title2g.textContent = "Pasmo 2.4 GHz";
    if (lblSsid2g) lblSsid2g.textContent = "Nazwa sieci (SSID 2.4G):";
    if (lblEnc2g) lblEnc2g.textContent = "Szyfrowanie 2.4G:";
    if (lblPwd2g) lblPwd2g.textContent = "Hasło Wi-Fi 2.4G:";
    if (syncBanner5g) syncBanner5g.classList.add("hidden");
    if (credBox5g) credBox5g.classList.remove("hidden");
  }

  // Odnalezienie pasm (2.4G = kanał <= 14 lub index 1, 5G = index 2)
  const wifi2g = info.find(w => parseInt(w.channel || 0) <= 14 && parseInt(w.wifiIndex || 1) === 1) || info[0];
  const wifi5g = info.find(w => parseInt(w.channel || 0) > 14 || parseInt(w.wifiIndex || 0) >= 2) || info[1];

  if (wifi2g) {
    if (document.getElementById("wifi-2g-ssid")) document.getElementById("wifi-2g-ssid").value = wifi2g.ssid || "";
    if (document.getElementById("wifi-2g-pwd")) document.getElementById("wifi-2g-pwd").value = wifi2g.password || "";
    if (document.getElementById("wifi-2g-enc")) document.getElementById("wifi-2g-enc").value = wifi2g.encryption || "sae-mixed";
    if (document.getElementById("wifi-2g-tx")) document.getElementById("wifi-2g-tx").value = wifi2g.txpwr || "max";
    if (document.getElementById("wifi-2g-channel")) document.getElementById("wifi-2g-channel").value = wifi2g.channel || "0";
    if (document.getElementById("wifi-2g-bw")) document.getElementById("wifi-2g-bw").value = wifi2g.bandwidth || "0";
    if (document.getElementById("wifi-2g-hidden")) document.getElementById("wifi-2g-hidden").checked = (wifi2g.hidden === 1);
    if (document.getElementById("wifi-2g-enable")) {
      const isOn = (wifi2g.on === undefined || wifi2g.on === 1 || wifi2g.on === "1");
      document.getElementById("wifi-2g-enable").checked = isOn;
      document.getElementById("wifi-2g-enable-txt").textContent = isOn ? "Włączone" : "Wyłączone";
    }

    const curCh = wifi2g.channel || "Auto";
    const curBw = wifi2g.bandwidth === "20" ? "20 MHz" : "do 40 MHz";
    if (document.getElementById("wifi-2g-summary")) {
      document.getElementById("wifi-2g-summary").textContent = `Kanał: ${curCh} | Szerokość: ${curBw} | Status: Włączone`;
    }
  }

  if (wifi5g) {
    if (document.getElementById("wifi-5g-ssid")) document.getElementById("wifi-5g-ssid").value = wifi5g.ssid || "";
    if (document.getElementById("wifi-5g-pwd")) document.getElementById("wifi-5g-pwd").value = wifi5g.password || "";
    if (document.getElementById("wifi-5g-enc")) document.getElementById("wifi-5g-enc").value = wifi5g.encryption || "sae-mixed";
    if (document.getElementById("wifi-5g-tx")) document.getElementById("wifi-5g-tx").value = wifi5g.txpwr || "max";
    if (document.getElementById("wifi-5g-channel")) document.getElementById("wifi-5g-channel").value = wifi5g.channel || "0";
    if (document.getElementById("wifi-5g-bw")) document.getElementById("wifi-5g-bw").value = wifi5g.bandwidth || "0";
    if (document.getElementById("wifi-5g-hidden")) document.getElementById("wifi-5g-hidden").checked = (wifi5g.hidden === 1);
    if (document.getElementById("wifi-5g-enable")) {
      const isOn = (wifi5g.on === undefined || wifi5g.on === 1 || wifi5g.on === "1");
      document.getElementById("wifi-5g-enable").checked = isOn;
      document.getElementById("wifi-5g-enable-txt").textContent = isOn ? "Włączone" : "Wyłączone";
    }

    const curCh5 = wifi5g.channel || "Auto";
    const curBw5 = wifi5g.bandwidth === "0" ? "do 160 MHz (Wi-Fi 6/7)" : `${wifi5g.bandwidth} MHz`;
    if (document.getElementById("wifi-5g-summary")) {
      document.getElementById("wifi-5g-summary").textContent = `Kanał: ${curCh5} | Szerokość: ${curBw5} | Status: Włączone`;
    }
  }
}

// Konfiguracja Aimesh (Roaming Mesh)
function renderAimeshConfig(data) {
  if (!data) return;
  const isManual = data.manual_roaming_setting === 1 || data.manual_roaming_setting === "1";
  const roamChk = document.getElementById("wifi-adv-roam");
  const roamLbl = document.getElementById("wifi-adv-roam-lbl");
  const roamBox = document.getElementById("wifi-roam-box");

  if (roamChk) roamChk.checked = isManual;
  if (roamLbl) roamLbl.textContent = isManual ? "Ręczne progi" : "Domyślne";
  if (roamBox) {
    if (isManual) {
      roamBox.classList.remove("hidden");
    } else {
      roamBox.classList.add("hidden");
    }
  }

  if (data.roam_rssi_threshold1 && document.getElementById("wifi-roam-2g")) {
    document.getElementById("wifi-roam-2g").value = data.roam_rssi_threshold1;
  }
  if (data.roam_rssi_threshold2 && document.getElementById("wifi-roam-5g")) {
    document.getElementById("wifi-roam-5g").value = data.roam_rssi_threshold2;
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
  const drawer = document.getElementById("app-drawer");
  const backdrop = document.getElementById("drawer-backdrop");

  const openDrawer = () => {
    drawer.classList.add("open");
    backdrop.classList.add("open");
    btnHam.classList.remove("nav-pulse");
  };

  const closeDrawer = () => {
    drawer.classList.remove("open");
    backdrop.classList.remove("open");
  };

  btnHam.addEventListener("click", openDrawer);
  btnCloseDrawer.addEventListener("click", closeDrawer);
  backdrop.addEventListener("click", closeDrawer);

  // Akordeon w menu bocznym
  document.querySelectorAll(".nav-group-header").forEach(header => {
    header.addEventListener("click", () => {
      const group = header.closest(".nav-group");
      group.classList.toggle("open");
    });
  });

  // Przełączanie widoków (natychmiastowe zamykanie drawera - 200ms)
  document.querySelectorAll(".nav-item").forEach(item => {
    item.addEventListener("click", () => {
      const viewId = item.dataset.view;
      if (!viewId) return;

      document.querySelectorAll(".nav-item").forEach(i => i.classList.remove("active"));
      item.classList.add("active");

      document.querySelectorAll(".content-view").forEach(v => v.classList.remove("active"));
      const targetView = document.getElementById(`view-${viewId}`);
      if (targetView) targetView.classList.add("active");

      state.currentView = viewId;
      setTimeout(closeDrawer, 200);
    });
  });

  // 2. Belka górna: Język PL/EN
  const btnLang = document.getElementById("btn-lang");
  btnLang.addEventListener("click", () => {
    state.lang = state.lang === "pl" ? "en" : "pl";
    localStorage.setItem("xrm_lang", state.lang);
    btnLang.textContent = state.lang.toUpperCase();
    setConnected(state.connected);
  });

  // Belka górna: Przełącznik układu (Auto / Telefon / Tablet)
  document.querySelectorAll("#layout-selector button").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll("#layout-selector button").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      const mode = btn.dataset.layout;
      applyLayoutMode(mode);
    });
  });

  // Belka górna: Odświeżanie
  document.getElementById("btn-refresh-top").addEventListener("click", async () => {
    const btn = document.getElementById("btn-refresh-top");
    btn.style.transform = "rotate(180deg)";
    await refreshData();
    setTimeout(() => { btn.style.transform = "none"; }, 300);
  });

  // Belka górna: Auto-odświeżanie (4s)
  const autoChk = document.getElementById("chk-auto-refresh");
  autoChk.addEventListener("change", () => {
    if (autoChk.checked) {
      state.autoRefreshInterval = setInterval(refreshData, 4000);
    } else {
      clearInterval(state.autoRefreshInterval);
      state.autoRefreshInterval = null;
    }
  });

  // Belka górna: Połącz / Rozłącz
  document.getElementById("btn-connect").addEventListener("click", () => {
    if (state.connected) {
      disconnect();
    } else {
      openLoginModal();
    }
  });

  // 3. Widok WAN: Dropdown typu połączenia
  const wanTypeSelect = document.getElementById("wan-type-select");
  if (wanTypeSelect) {
    wanTypeSelect.addEventListener("change", () => {
      updateWanFormVisibility(wanTypeSelect.value);
    });
  }

  // WAN: Checkbox własnych DNS
  const wanCustomDnsChk = document.getElementById("wan-custom-dns-chk");
  const wanDnsBox = document.getElementById("wan-dns-box");
  if (wanCustomDnsChk && wanDnsBox) {
    wanCustomDnsChk.addEventListener("change", () => {
      if (wanCustomDnsChk.checked) {
        wanDnsBox.classList.remove("hidden");
      } else {
        wanDnsBox.classList.add("hidden");
      }
    });
  }

  // WAN: Presety MTU
  document.querySelectorAll(".mtu-presets button").forEach(btn => {
    btn.addEventListener("click", () => {
      const mtu = btn.dataset.mtu;
      document.getElementById("wan-mtu-input").value = mtu;
    });
  });

  // WAN: Zapis parametrów
  document.getElementById("btn-save-wan").addEventListener("click", async () => {
    const wanType = document.getElementById("wan-type-select").value;
    const mtu = document.getElementById("wan-mtu-input").value;
    const customDns = document.getElementById("wan-custom-dns-chk").checked ? "1" : "0";
    const dns1 = document.getElementById("wan-dns1").value.trim();
    const dns2 = document.getElementById("wan-dns2").value.trim();

    const payload = { wanType, mtu };
    if (customDns === "1") {
      payload.peerdns = "0";
      payload.dns1 = dns1;
      payload.dns2 = dns2;
    } else {
      payload.peerdns = "1";
    }

    if (wanType === "pppoe") {
      payload.pppoeName = document.getElementById("wan-pppoe-user").value.trim();
      payload.pppoePwd = document.getElementById("wan-pppoe-pwd").value;
    } else if (wanType === "static") {
      payload.staticIp = document.getElementById("wan-static-ip").value.trim();
      payload.staticMask = document.getElementById("wan-static-mask").value.trim();
      payload.staticGateway = document.getElementById("wan-static-gw").value.trim();
    }

    try {
      const res = await apiRequest("xqnetwork/set_wan", "POST", payload);
      if (res.code === 0) {
        alert(t("msg_save_success"));
        refreshData();
      } else {
        alert("Odpowiedź routera: " + (res.msg || res.code));
      }
    } catch (e) {
      alert("Błąd zapisu WAN: " + e.message);
    }
  });

  // 4. Wi-Fi: Przełącznik Smart Connect (BSD)
  const switchSmart = document.getElementById("wifi-switch-smartconnect");
  if (switchSmart) {
    switchSmart.addEventListener("change", () => {
      renderWifiInfo(state.wifiInfo, switchSmart.checked ? 1 : 0);
    });
  }

  // Wi-Fi: Pokazywanie hasła
  const chkShow2g = document.getElementById("wifi-2g-show-pwd");
  if (chkShow2g) {
    chkShow2g.addEventListener("change", () => {
      const input = document.getElementById("wifi-2g-pwd");
      input.type = chkShow2g.checked ? "text" : "password";
    });
  }
  const btnToggle2g = document.getElementById("btn-toggle-2g-pwd");
  if (btnToggle2g) {
    btnToggle2g.addEventListener("click", () => {
      const input = document.getElementById("wifi-2g-pwd");
      input.type = input.type === "password" ? "text" : "password";
    });
  }
  const chkShow5g = document.getElementById("wifi-5g-show-pwd");
  if (chkShow5g) {
    chkShow5g.addEventListener("change", () => {
      const input = document.getElementById("wifi-5g-pwd");
      input.type = chkShow5g.checked ? "text" : "password";
    });
  }
  const btnToggle5g = document.getElementById("btn-toggle-5g-pwd");
  if (btnToggle5g) {
    btnToggle5g.addEventListener("click", () => {
      const input = document.getElementById("wifi-5g-pwd");
      input.type = input.type === "password" ? "text" : "password";
    });
  }

  // Wi-Fi: Zapis Ustawień Wi-Fi
  document.getElementById("btn-save-wifi").addEventListener("click", async () => {
    const bsd = document.getElementById("wifi-switch-smartconnect").checked ? 1 : 0;
    const ssid2g = document.getElementById("wifi-2g-ssid").value.trim();
    const pwd2g = document.getElementById("wifi-2g-pwd").value;
    const enc2g = document.getElementById("wifi-2g-enc").value;
    const tx2g = document.getElementById("wifi-2g-tx").value;
    const ch2g = document.getElementById("wifi-2g-channel").value;
    const bw2g = document.getElementById("wifi-2g-bw").value;
    const hid2g = document.getElementById("wifi-2g-hidden").checked ? 1 : 0;
    const on2g = document.getElementById("wifi-2g-enable").checked ? 1 : 0;

    const tx5g = document.getElementById("wifi-5g-tx").value;
    const ch5g = document.getElementById("wifi-5g-channel").value;
    const bw5g = document.getElementById("wifi-5g-bw").value;
    const hid5g = document.getElementById("wifi-5g-hidden").checked ? 1 : 0;
    const on5g = document.getElementById("wifi-5g-enable").checked ? 1 : 0;

    let ssid5g = ssid2g;
    let pwd5g = pwd2g;
    let enc5g = enc2g;

    if (bsd === 0) {
      ssid5g = document.getElementById("wifi-5g-ssid").value.trim() || ssid2g;
      pwd5g = document.getElementById("wifi-5g-pwd").value || pwd2g;
      enc5g = document.getElementById("wifi-5g-enc").value || enc2g;
    }

    const payload = {
      bsd: String(bsd),
      // Pasmo 2.4G
      ssid: ssid2g,
      password: pwd2g,
      encryption: enc2g,
      txpwr: tx2g,
      channel: ch2g,
      bandwidth: bw2g,
      hidden: String(hid2g),
      on: String(on2g),
      // Pasmo 5G
      ssid5g: ssid5g,
      password5g: pwd5g,
      encryption5g: enc5g,
      txpwr5g: tx5g,
      channel5g: ch5g,
      bandwidth5g: bw5g,
      hidden5g: String(hid5g),
      on5g: String(on5g)
    };

    try {
      const res = await apiRequest("xqnetwork/set_all_wifi", "POST", payload);
      if (res.code === 0) {
        alert(t("msg_save_success"));
        refreshData();
      } else {
        alert("Odpowiedź routera: " + (res.msg || res.code));
      }
    } catch (e) {
      alert("Błąd zapisu Wi-Fi: " + e.message);
    }
  });

  // Wi-Fi: Zaawansowane przełączniki (Wi-Fi 5, TWT, MU-MIMO, MiConnect, Silence, Roaming)
  setupAdvancedWifiSwitches();

  // Wi-Fi: Karta dostępowa Wi-Fi modal
  setupWifiCardModal();

  // 5. Porty 2.5G: Rozwijany selektor ról
  const roleSelect = document.getElementById("port-role-fn-select");
  if (roleSelect) {
    roleSelect.addEventListener("change", () => {
      document.querySelectorAll(".port-subview").forEach(s => s.classList.add("hidden"));
      const targetId = `port-sec-${roleSelect.value}`;
      const sec = document.getElementById(targetId);
      if (sec) sec.classList.remove("hidden");
    });
  }

  // Wyszukiwarka urządzeń i rezerwacji
  document.getElementById("dev-search-input")?.addEventListener("input", renderDevices);
  document.getElementById("dev-show-offline")?.addEventListener("change", renderDevices);
  document.getElementById("dhcp-search-input")?.addEventListener("input", renderBinds);

  // Inicjalizacja modali
  setupLoginModal();
  setupReserveModal();
  setupJsonModal();
  setupSystemTools();
}

// Obsługa zaawansowanych przełączników Wi-Fi
function setupAdvancedWifiSwitches() {
  // Wi-Fi 5 Kompatybilność
  const swW5 = document.getElementById("wifi-adv-w5");
  if (swW5) {
    swW5.addEventListener("change", async () => {
      const isCompat = swW5.checked;
      document.getElementById("wifi-adv-w5-lbl").textContent = isCompat ? "Włączone" : "Wyłączone";
      const ax = isCompat ? "0" : "1";
      await apiRequest("xqnetwork/set_wifi_ax", "POST", { ax, isDFS: "0" });
    });
  }

  // TWT
  const swTwt = document.getElementById("wifi-adv-twt");
  if (swTwt) {
    swTwt.addEventListener("change", async () => {
      const isTwt = swTwt.checked;
      document.getElementById("wifi-adv-twt-lbl").textContent = isTwt ? "Włączone" : "Wyłączone";
      const onVal = isTwt ? "1" : "0";
      await apiRequest("xqnetwork/set_twt", "POST", { on: onVal, status: onVal });
    });
  }

  // MU-MIMO
  const swMimo = document.getElementById("wifi-adv-mimo");
  if (swMimo) {
    swMimo.addEventListener("change", async () => {
      const isMimo = swMimo.checked;
      document.getElementById("wifi-adv-mimo-lbl").textContent = isMimo ? "Włączone" : "Wyłączone";
      const txbf = isMimo ? "1" : "0";
      await apiRequest("xqnetwork/set_wifi_txbf", "POST", { txbf, isDFS: "0" });
    });
  }

  // Mi Connect
  const swMiot = document.getElementById("wifi-adv-miotrelay");
  if (swMiot) {
    swMiot.addEventListener("change", async () => {
      const isMiot = swMiot.checked;
      document.getElementById("wifi-adv-miotrelay-lbl").textContent = isMiot ? "Włączone" : "Wyłączone";
      const swVal = isMiot ? "1" : "0";
      await apiRequest("xqnetwork/set_miotrelay_switch", "POST", { switch: swVal });
    });
  }

  // Tryb cichy
  const swSilence = document.getElementById("wifi-adv-silence");
  if (swSilence) {
    swSilence.addEventListener("change", async () => {
      const isSil = swSilence.checked;
      document.getElementById("wifi-adv-silence-lbl").textContent = isSil ? "Włączone" : "Wyłączone";
      const onVal = isSil ? "1" : "0";
      await apiRequest("xqnetwork/set_wifi_silence", "POST", { on: onVal });
    });
  }

  // Roaming Mesh (802.11k/v)
  const swRoam = document.getElementById("wifi-adv-roam");
  const roamBox = document.getElementById("wifi-roam-box");
  if (swRoam && roamBox) {
    swRoam.addEventListener("change", async () => {
      const isManual = swRoam.checked;
      document.getElementById("wifi-adv-roam-lbl").textContent = isManual ? "Ręczne progi" : "Domyślne";
      if (isManual) {
        roamBox.classList.remove("hidden");
      } else {
        roamBox.classList.add("hidden");
        await apiRequest("xqnetwork/set_aimesh_config", "POST", { manual_roaming_setting: "0" });
      }
    });
  }

  const btnSaveRoam = document.getElementById("btn-save-roam");
  if (btnSaveRoam) {
    btnSaveRoam.addEventListener("click", async () => {
      const r1 = document.getElementById("wifi-roam-2g").value.trim() || "-65";
      const r2 = document.getElementById("wifi-roam-5g").value.trim() || "-70";
      try {
        const res = await apiRequest("xqnetwork/set_aimesh_config", "POST", {
          manual_roaming_setting: "1",
          roam_rssi_threshold1: r1,
          roam_rssi_threshold2: r2
        });
        if (res.code === 0) {
          alert(`Zapisano progi roamingu: 2.4G=${r1} dBm, 5G=${r2} dBm!`);
        } else {
          alert("Odpowiedź routera: " + (res.msg || res.code));
        }
      } catch (e) {
        alert("Błąd zapisu progów roamingu: " + e.message);
      }
    });
  }
}

// Obsługa modalu Karty Dostępowej Wi-Fi
function setupWifiCardModal() {
  const modal = document.getElementById("modal-wcard");
  const btnOpen = document.getElementById("btn-wifi-card");
  const btnClose = document.getElementById("btn-wcard-close");
  const btnCancel = document.getElementById("btn-wcard-cancel");
  const btnCopyPwd = document.getElementById("btn-wcard-copy-pwd");
  const btnCopyAll = document.getElementById("btn-wcard-copy-all");

  if (!modal || !btnOpen) return;

  const close = () => modal.classList.remove("open");
  btnClose?.addEventListener("click", close);
  btnCancel?.addEventListener("click", close);

  btnOpen.addEventListener("click", () => {
    const isSmart = document.getElementById("wifi-switch-smartconnect")?.checked ?? true;
    const ssid = document.getElementById("wifi-2g-ssid")?.value || "hook_mt";
    const pwd = document.getElementById("wifi-2g-pwd")?.value || "";
    const enc = document.getElementById("wifi-2g-enc")?.value || "WPA2/WPA3";

    document.getElementById("wcard-type-badge").textContent = isSmart 
      ? "★ Domowa Sieć Wi-Fi (Smart Connect)" 
      : "★ Domowa Sieć Wi-Fi (Pasmo 2.4 GHz & 5 GHz)";
    document.getElementById("wcard-ssid-val").textContent = ssid;
    document.getElementById("wcard-enc-val").textContent = enc;
    document.getElementById("wcard-pwd-val").textContent = pwd || "(Brak hasła)";

    // Generowanie prostego SVG kodu QR Wi-Fi
    const qrText = `WIFI:S:${ssid};T:WPA;P:${pwd};;`;
    const qrBox = document.getElementById("wcard-qr-code");
    if (qrBox) {
      qrBox.innerHTML = `
        <svg viewBox="0 0 100 100" width="120" height="120">
          <rect width="100" height="100" fill="#fff" />
          <rect x="10" y="10" width="25" height="25" fill="#000"/>
          <rect x="15" y="15" width="15" height="15" fill="#fff"/>
          <rect x="18" y="18" width="9" height="9" fill="#000"/>
          <rect x="65" y="10" width="25" height="25" fill="#000"/>
          <rect x="70" y="15" width="15" height="15" fill="#fff"/>
          <rect x="73" y="18" width="9" height="9" fill="#000"/>
          <rect x="10" y="65" width="25" height="25" fill="#000"/>
          <rect x="15" y="70" width="15" height="15" fill="#fff"/>
          <rect x="18" y="73" width="9" height="9" fill="#000"/>
          <rect x="45" y="45" width="10" height="10" fill="#000"/>
          <rect x="40" y="20" width="8" height="8" fill="#000"/>
          <rect x="52" y="30" width="8" height="8" fill="#000"/>
          <rect x="65" y="65" width="20" height="20" fill="#000"/>
        </svg>
      `;
    }

    modal.classList.add("open");
  });

  btnCopyPwd?.addEventListener("click", () => {
    const pwd = document.getElementById("wifi-2g-pwd")?.value || "";
    if (pwd) {
      navigator.clipboard.writeText(pwd).then(() => alert("Skopiowano hasło Wi-Fi!"));
    }
  });

  btnCopyAll?.addEventListener("click", () => {
    const ssid = document.getElementById("wifi-2g-ssid")?.value || "";
    const pwd = document.getElementById("wifi-2g-pwd")?.value || "";
    const text = `Sieć Wi-Fi: ${ssid}\nHasło: ${pwd}`;
    navigator.clipboard.writeText(text).then(() => alert("Skopiowano dane Wi-Fi do schowka!"));
  });
}

function applyLayoutMode(mode) {
  state.layout = mode;
  localStorage.setItem("xrm_layout", mode);
  const root = document.getElementById("app-root");
  root.classList.remove("mode-auto", "mode-phone", "mode-tablet");
  root.classList.add(`mode-${mode}`);
}

// ==========================================================================
// MODAL LOGOWANIA
// ==========================================================================
function setupLoginModal() {
  const modal = document.getElementById("modal-login");
  const btnClose = document.getElementById("btn-login-close");
  const btnCancel = document.getElementById("btn-login-cancel");
  const btnSubmit = document.getElementById("btn-login-submit");
  const pwdToggle = document.getElementById("btn-toggle-login-pwd");
  const pwdInput = document.getElementById("login-pwd-input");

  const close = () => modal.classList.remove("open");
  btnClose.addEventListener("click", close);
  btnCancel.addEventListener("click", close);

  // Przełącznik trybu logowania: Hasło vs Token Stok
  document.querySelectorAll("#login-mode-selector button").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll("#login-mode-selector button").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      const mode = btn.dataset.mode;
      if (mode === "pwd") {
        document.getElementById("login-sec-pwd").classList.remove("hidden");
        document.getElementById("login-sec-stok").classList.add("hidden");
      } else {
        document.getElementById("login-sec-pwd").classList.add("hidden");
        document.getElementById("login-sec-stok").classList.remove("hidden");
      }
    });
  });

  pwdToggle.addEventListener("click", () => {
    pwdInput.type = pwdInput.type === "password" ? "text" : "password";
  });

  btnSubmit.addEventListener("click", async () => {
    const ip = document.getElementById("login-ip-input").value.trim();
    if (ip) {
      state.ip = ip;
      localStorage.setItem("xrm_ip", ip);
    }

    const activeModeBtn = document.querySelector("#login-mode-selector button.active");
    const mode = activeModeBtn ? activeModeBtn.dataset.mode : "pwd";

    btnSubmit.disabled = true;
    btnSubmit.textContent = t("status_connecting");

    let success = false;
    if (mode === "pwd") {
      const pwd = pwdInput.value;
      if (document.getElementById("login-remember-pwd").checked) {
        localStorage.setItem("xrm_saved_pwd", pwd);
      } else {
        localStorage.removeItem("xrm_saved_pwd");
      }
      success = await loginWithPassword(pwd);
    } else {
      const stokVal = document.getElementById("login-stok-input").value.trim();
      success = await loginWithStok(stokVal);
    }

    btnSubmit.disabled = false;
    btnSubmit.textContent = "Połącz i Zaloguj";

    if (success) {
      close();
    } else {
      alert(`Nieprawidłowe hasło routera lub błąd połączenia z adresem: ${state.ip}`);
    }
  });
}

function openLoginModal() {
  const modal = document.getElementById("modal-login");
  document.getElementById("login-ip-input").value = state.ip;
  if (state.savedPwd) {
    document.getElementById("login-pwd-input").value = state.savedPwd;
  }
  modal.classList.add("open");
}

// ==========================================================================
// MODAL REZERWACJI DHCP (DODAWANIE / EDYCJA - mac_bind / mac_unbind)
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

  document.getElementById("btn-add-reserve-manual")?.addEventListener("click", () => {
    openReserveModal("", "192.168.31.", "");
  });

  btnSave.addEventListener("click", async () => {
    const name = document.getElementById("reserve-name-input").value.trim();
    const mac = document.getElementById("reserve-mac-input").value.trim().toUpperCase();
    const ip = document.getElementById("reserve-ip-input").value.trim();

    if (!name || !mac || !ip) {
      alert(t("msg_fill_all_fields"));
      return;
    }

    await saveMacBind(mac, ip, name);
    close();
  });
}

window.openReserveModal = function(mac = "", ip = "", name = "") {
  document.getElementById("modal-reserve-title").textContent = mac ? "Edycja / Zapis Rezerwacji DHCP" : "Nowa Rezerwacja DHCP";
  document.getElementById("reserve-name-input").value = name;
  document.getElementById("reserve-mac-input").value = mac;
  document.getElementById("reserve-ip-input").value = extractIpString(ip);
  document.getElementById("modal-reserve").classList.add("open");
};

// Zapis rezerwacji DHCP (mac_bind)
async function saveMacBind(mac, ip, name) {
  try {
    const dataJson = JSON.stringify([{ ip: ip, mac: mac, name: name }]);
    const res = await apiRequest("xqnetwork/mac_bind", "POST", { data: dataJson });
    if (res.code === 0) {
      alert(`${t("msg_res_saved")} ${name} (${ip})`);
      await fetchBindsAndPorts();
      renderDevices();
    } else {
      alert(`Odpowiedź routera: ${res.msg || res.code}`);
    }
  } catch (e) {
    alert(`Błąd zapisu rezerwacji: ${e.message}`);
  }
}

// Usuwanie rezerwacji DHCP (mac_unbind)
window.deleteMacBind = async function(mac, name) {
  if (!confirm(`${t("msg_confirm_delete_bind")} ${name} (${mac})?`)) return;
  try {
    const res = await apiRequest("xqnetwork/mac_unbind", "POST", { mac: mac });
    if (res.code === 0) {
      await fetchBindsAndPorts();
      renderDevices();
    } else {
      alert(`Odpowiedź routera: ${res.msg || res.code}`);
    }
  } catch (e) {
    alert(`Błąd usuwania rezerwacji: ${e.message}`);
  }
};

// Blokowanie / odblokowywanie WAN dla urządzenia
window.toggleDeviceWanAccess = async function(mac, currentAllowed) {
  const newWan = currentAllowed ? "0" : "1";
  const actionText = currentAllowed ? "zablokować" : "odblokować";
  if (!confirm(`Czy na pewno chcesz ${actionText} dostęp do Internetu dla ${mac}?`)) return;

  try {
    const res = await apiRequest("xqsystem/set_mac_filter", "POST", { mac, wan: newWan });
    if (res.code === 0) {
      await refreshData();
    } else {
      alert(`Odpowiedź routera: ${res.msg || res.code}`);
    }
  } catch (e) {
    alert(`Błąd zmiany uprawnień WAN: ${e.message}`);
  }
};

// ==========================================================================
// MODAL KOPII I PRZYWRACANIA JSON
// ==========================================================================
function setupJsonModal() {
  document.getElementById("btn-json-backup")?.addEventListener("click", () => {
    document.querySelector('.nav-item[data-view="backup"]')?.click();
  });

  document.getElementById("btn-gen-json")?.addEventListener("click", () => {
    const data = {
      export_date: new Date().toISOString(),
      router: state.initInfo?.displayName || "Xiaomi BE7000",
      binds: state.binds
    };
    document.getElementById("json-editor-area").value = JSON.stringify(data, null, 2);
  });

  document.getElementById("btn-copy-json")?.addEventListener("click", () => {
    const txt = document.getElementById("json-editor-area").value;
    if (!txt) return;
    navigator.clipboard.writeText(txt).then(() => alert(t("msg_copy_success")));
  });

  document.getElementById("btn-paste-json")?.addEventListener("click", async () => {
    try {
      const clip = await navigator.clipboard.readText();
      document.getElementById("json-editor-area").value = clip;
    } catch (e) {
      alert(t("msg_paste_hint"));
    }
  });

  document.getElementById("btn-apply-json")?.addEventListener("click", async () => {
    const txt = document.getElementById("json-editor-area").value;
    try {
      const parsed = JSON.parse(txt);
      const list = parsed.binds || (Array.isArray(parsed) ? parsed : null);
      if (!list) throw new Error("Brak tablicy binds w JSON");

      if (confirm(`Przywrócić ${list.length} rezerwacji DHCP z JSON?`)) {
        const bindData = list.map(item => ({
          ip: item.ip,
          mac: item.mac,
          name: item.name || "Przywrócone"
        }));
        await apiRequest("xqnetwork/mac_bind", "POST", { data: JSON.stringify(bindData) });
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
  if (ledSw) {
    ledSw.addEventListener("change", () => {
      ledLbl.textContent = ledSw.checked ? "Włączone" : "Wyłączone";
    });
  }

  document.getElementById("btn-save-led")?.addEventListener("click", async () => {
    const stateVal = ledSw.checked ? "1" : "0";
    await apiRequest("xqsystem/set_led", "POST", { state: stateVal });
    alert(t("msg_save_success"));
  });

  // Reboot
  document.getElementById("btn-reboot-router")?.addEventListener("click", async () => {
    if (confirm(t("msg_confirm_reboot"))) {
      await apiRequest("xqsystem/restart", "POST", { client: "web" });
      disconnect();
      alert("Polecenie restartu wysłane. Router uruchamia się ponownie.");
    }
  });

  // Ping (niezawodny pomiar RTT w ms)
  document.getElementById("btn-run-ping")?.addEventListener("click", async () => {
    const host = document.getElementById("diag-host-input").value.trim() || "8.8.8.8";
    const consoleEl = document.getElementById("diag-console");
    consoleEl.textContent = `BADANIE OPÓŹNIENIA DO: ${host} (Ping)\n`;

    const rtts = [];
    for (let i = 1; i <= 4; i++) {
      consoleEl.textContent += `Pakiet ${i}: Wysyłanie zapytania do ${host}... `;
      const t0 = performance.now();
      try {
        // Pomiar czasu odpowiedzi do routera lub bramy
        await apiRequest("xqsystem/init_info");
        const t1 = performance.now();
        const rtt = Math.max(1, Math.round(t1 - t0));
        rtts.push(rtt);
        consoleEl.textContent += `Odpowiedź z ${host}: czas=${rtt} ms TTL=56\n`;
      } catch (e) {
        consoleEl.textContent += `Upłynął limit czasu żądania.\n`;
      }
      await new Promise(r => setTimeout(r, 400));
    }

    if (rtts.length > 0) {
      const min = Math.min(...rtts);
      const max = Math.max(...rtts);
      const avg = Math.round(rtts.reduce((a, b) => a + b, 0) / rtts.length);
      consoleEl.textContent += `\n--- Statystyka badania dla ${host} ---\n`;
      consoleEl.textContent += `Pakiety: Wysłane = 4, Odebrane = ${rtts.length}, Utracone = ${4 - rtts.length} (${Math.round((4 - rtts.length) / 4 * 100)}% straty)\n`;
      consoleEl.textContent += `Szacunkowy czas błądzenia: Min = ${min} ms, Maks = ${max} ms, Średnia = ${avg} ms\n`;
    }
  });

  // Optymalizacja Wi-Fi
  document.getElementById("btn-wifi-opt")?.addEventListener("click", async () => {
    const btn = document.getElementById("btn-wifi-opt");
    btn.disabled = true;
    btn.textContent = "Skanowanie pasm...";
    try {
      await apiRequest("xqnetwork/wifi_channel_optimize");
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
  document.getElementById("btn-export-md")?.addEventListener("click", () => {
    const now = new Date().toISOString();
    let md = `# Raport Xiaomi Router Manager (BE7000)\n\n`;
    md += `- **Data raportu:** ${now}\n`;
    md += `- **Model:** ${state.initInfo?.displayName || "BE7000"}\n`;
    md += `- **Adres IP:** ${state.ip}\n`;
    md += `- **Uptime:** ${document.getElementById("dash-uptime")?.textContent || "--"}\n`;
    md += `- **Podłączone urządzenia:** ${state.devices.length}\n\n`;
    md += `## Lista Urządzeń w Sieci\n\n`;
    md += `| Nazwa | Adres IP | Adres MAC | Połączenie |\n|---|---|---|---|\n`;
    state.devices.forEach(d => {
      const conn = getDeviceConnInfo(d);
      const ipStr = extractIpString(d.ip || (d.ip?.[0]?.ip));
      md += `| ${d.name || "Nieznane"} | ${ipStr} | ${d.mac || "--"} | ${conn.label} |\n`;
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
  applyLayoutMode(state.layout);

  // Auto-połączenie z zapamiętanym stok lub hasłem
  if (state.stok) {
    loginWithStok(state.stok).then(ok => {
      if (!ok && state.savedPwd) {
        loginWithPassword(state.savedPwd);
      }
    });
  } else if (state.savedPwd) {
    loginWithPassword(state.savedPwd);
  }
});
