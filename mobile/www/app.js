/**
 * Xiaomi Router Manager (XRM) - Mobilny i Tabletowy Panel Klienta
 * Wersja oparta o architekturę z wersji Windows v1.0.2 z zachowaniem pełnej ergonomii dotykowej.
 */

const PUBLIC_KEY = "a2ffa5c9be07488bbb04a3a47d3c5f6a";

// ==========================================================================
// MAPA STREF CZASOWYCH IANA -> POSIX (dla API routera Xiaomi / OpenWrt)
// Uzupelniaj wedlug potrzeb; klucz = strefa IANA, wartosc = string POSIX
// ==========================================================================
const TZ_POSIX_MAP = {
  "Europe/Warsaw":       "CET-1CEST,M3.5.0,M10.5.0/3",
  "Europe/London":       "GMT0BST,M3.5.0/1,M10.5.0",
  "Europe/Berlin":       "CET-1CEST,M3.5.0,M10.5.0/3",
  "Europe/Paris":        "CET-1CEST,M3.5.0,M10.5.0/3",
  "Europe/Prague":       "CET-1CEST,M3.5.0,M10.5.0/3",
  "Europe/Vienna":       "CET-1CEST,M3.5.0,M10.5.0/3",
  "Europe/Budapest":     "CET-1CEST,M3.5.0,M10.5.0/3",
  "Europe/Stockholm":    "CET-1CEST,M3.5.0,M10.5.0/3",
  "Europe/Oslo":         "CET-1CEST,M3.5.0,M10.5.0/3",
  "Europe/Copenhagen":   "CET-1CEST,M3.5.0,M10.5.0/3",
  "Europe/Amsterdam":    "CET-1CEST,M3.5.0,M10.5.0/3",
  "Europe/Brussels":     "CET-1CEST,M3.5.0,M10.5.0/3",
  "Europe/Rome":         "CET-1CEST,M3.5.0,M10.5.0/3",
  "Europe/Madrid":       "CET-1CEST,M3.5.0,M10.5.0/3",
  "Europe/Lisbon":       "WET0WEST,M3.5.0/1,M10.5.0",
  "Europe/Helsinki":     "EET-2EEST,M3.5.0/3,M10.5.0/4",
  "Europe/Riga":         "EET-2EEST,M3.5.0/3,M10.5.0/4",
  "Europe/Tallinn":      "EET-2EEST,M3.5.0/3,M10.5.0/4",
  "Europe/Vilnius":      "EET-2EEST,M3.5.0/3,M10.5.0/4",
  "Europe/Bucharest":    "EET-2EEST,M3.5.0/3,M10.5.0/4",
  "Europe/Sofia":        "EET-2EEST,M3.5.0/3,M10.5.0/4",
  "Europe/Athens":       "EET-2EEST,M3.5.0/3,M10.5.0/4",
  "Europe/Kyiv":         "EET-2EEST,M3.5.0/3,M10.5.0/4",
  "Europe/Moscow":       "MSK-3",
  "Europe/Istanbul":     "TRT-3",
  "Asia/Shanghai":       "CST-8",
  "Asia/Hong_Kong":      "HKT-8",
  "Asia/Singapore":      "SGT-8",
  "Asia/Tokyo":          "JST-9",
  "Asia/Seoul":          "KST-9",
  "Asia/Taipei":         "CST-8",
  "Asia/Bangkok":        "ICT-7",
  "Asia/Jakarta":        "WIB-7",
  "Asia/Kolkata":        "IST-5:30",
  "Asia/Dubai":          "GST-4",
  "Asia/Riyadh":         "AST-3",
  "Asia/Tehran":         "IRST-3:30IRDT,80/0,264/0",
  "Asia/Almaty":         "ALMT-6",
  "Asia/Karachi":        "PKT-5",
  "Asia/Dhaka":          "BDT-6",
  "Asia/Yangon":         "MMT-6:30",
  "Asia/Colombo":        "IST-5:30",
  "Asia/Kathmandu":      "NPT-5:45",
  "Asia/Vladivostok":    "VLAT-10",
  "Asia/Krasnoyarsk":    "KRAT-7",
  "Asia/Yekaterinburg":  "YEKT-5",
  "Africa/Cairo":        "EET-2",
  "Africa/Johannesburg": "SAST-2",
  "Africa/Lagos":        "WAT-1",
  "Africa/Nairobi":      "EAT-3",
  "Africa/Casablanca":   "WET0",
  "America/New_York":    "EST5EDT,M3.2.0,M11.1.0",
  "America/Chicago":     "CST6CDT,M3.2.0,M11.1.0",
  "America/Denver":      "MST7MDT,M3.2.0,M11.1.0",
  "America/Los_Angeles": "PST8PDT,M3.2.0,M11.1.0",
  "America/Anchorage":   "AKST9AKDT,M3.2.0,M11.1.0",
  "America/Honolulu":    "HST10",
  "America/Phoenix":     "MST7",
  "America/Toronto":     "EST5EDT,M3.2.0,M11.1.0",
  "America/Vancouver":   "PST8PDT,M3.2.0,M11.1.0",
  "America/Sao_Paulo":   "BRT3BRST,M10.3.0/0,M2.3.0/0",
  "America/Argentina/Buenos_Aires": "ART3",
  "America/Mexico_City": "CST6CDT,M4.1.0,M10.5.0",
  "America/Bogota":      "COT5",
  "America/Lima":        "PET5",
  "America/Santiago":    "CLT4CLST,M10.2.6/24,M3.2.6/24",
  "Pacific/Auckland":    "NZST-12NZDT,M9.5.0,M4.1.0/3",
  "Pacific/Sydney":      "AEST-10AEDT,M10.1.0,M4.1.0/3",
  "Pacific/Melbourne":   "AEST-10AEDT,M10.1.0,M4.1.0/3",
  "Pacific/Brisbane":    "AEST-10",
  "Pacific/Fiji":        "FJT-12",
  "Pacific/Honolulu":    "HST10",
  "UTC":                 "UTC0"
};

// Lista stref do selecta (skrocone etykiety dla UI mobilnego)
const TZ_DISPLAY_LIST = [
  { iana: "Europe/Warsaw",       label: "🇵🇱 Polska (CET/CEST, UTC+1/+2)" },
  { iana: "Europe/Berlin",       label: "🇩🇪 Niemcy / DE (CET/CEST)" },
  { iana: "Europe/London",       label: "🇬🇧 Wielka Brytania / UK (GMT/BST)" },
  { iana: "Europe/Paris",        label: "🇫🇷 Francja / FR (CET/CEST)" },
  { iana: "Europe/Prague",       label: "🇨🇿 Czechy / CZ (CET/CEST)" },
  { iana: "Europe/Vienna",       label: "🇦🇹 Austria / AT (CET/CEST)" },
  { iana: "Europe/Stockholm",    label: "🇸🇪 Szwecja / SE (CET/CEST)" },
  { iana: "Europe/Amsterdam",    label: "🇳🇱 Holandia / NL (CET/CEST)" },
  { iana: "Europe/Rome",         label: "🇮🇹 Wlochy / IT (CET/CEST)" },
  { iana: "Europe/Madrid",       label: "🇪🇸 Hiszpania / ES (CET/CEST)" },
  { iana: "Europe/Lisbon",       label: "🇵🇹 Portugalia / PT (WET/WEST)" },
  { iana: "Europe/Helsinki",     label: "🇫🇮 Finlandia / FI (EET/EEST)" },
  { iana: "Europe/Athens",       label: "🇬🇷 Grecja / GR (EET/EEST)" },
  { iana: "Europe/Bucharest",    label: "🇷🇴 Rumunia / RO (EET/EEST)" },
  { iana: "Europe/Kyiv",         label: "🇺🇦 Ukraina / UA (EET/EEST)" },
  { iana: "Europe/Moscow",       label: "🇷🇺 Rosja - Moskwa (MSK, UTC+3)" },
  { iana: "Europe/Istanbul",     label: "🇹🇷 Turcja / TR (TRT, UTC+3)" },
  { iana: "Asia/Dubai",          label: "🇦🇪 ZEA / UAE (GST, UTC+4)" },
  { iana: "Asia/Karachi",        label: "🇵🇰 Pakistan / PK (PKT, UTC+5)" },
  { iana: "Asia/Kolkata",        label: "🇮🇳 Indie / IN (IST, UTC+5:30)" },
  { iana: "Asia/Dhaka",          label: "🇧🇩 Bangladesz / BD (BDT, UTC+6)" },
  { iana: "Asia/Bangkok",        label: "🇹🇭 Tajlandia / TH (ICT, UTC+7)" },
  { iana: "Asia/Shanghai",       label: "🇨🇳 Chiny / CN (CST, UTC+8)" },
  { iana: "Asia/Singapore",      label: "🇸🇬 Singapur / SG (SGT, UTC+8)" },
  { iana: "Asia/Hong_Kong",      label: "🇭🇰 Hongkong / HK (HKT, UTC+8)" },
  { iana: "Asia/Taipei",         label: "🇹🇼 Tajwan / TW (CST, UTC+8)" },
  { iana: "Asia/Tokyo",          label: "🇯🇵 Japonia / JP (JST, UTC+9)" },
  { iana: "Asia/Seoul",          label: "🇰🇷 Korea Poludniowa / KR (KST, UTC+9)" },
  { iana: "Pacific/Sydney",      label: "🇦🇺 Australia - Sydney (AEST/AEDT)" },
  { iana: "Pacific/Brisbane",    label: "🇦🇺 Australia - Brisbane (AEST, UTC+10)" },
  { iana: "Pacific/Auckland",    label: "🇳🇿 Nowa Zelandia / NZ (NZST/NZDT)" },
  { iana: "America/New_York",    label: "🇺🇸 USA - Wschod (EST/EDT, UTC-5/-4)" },
  { iana: "America/Chicago",     label: "🇺🇸 USA - Centrum (CST/CDT, UTC-6/-5)" },
  { iana: "America/Denver",      label: "🇺🇸 USA - Gory (MST/MDT, UTC-7/-6)" },
  { iana: "America/Los_Angeles", label: "🇺🇸 USA - Zachod (PST/PDT, UTC-8/-7)" },
  { iana: "America/Honolulu",    label: "🇺🇸 USA - Hawaje (HST, UTC-10)" },
  { iana: "America/Toronto",     label: "🇨🇦 Kanada - Toronto (EST/EDT)" },
  { iana: "America/Vancouver",   label: "🇨🇦 Kanada - Vancouver (PST/PDT)" },
  { iana: "America/Sao_Paulo",   label: "🇧🇷 Brazylia - Sao Paulo (BRT/BRST)" },
  { iana: "America/Mexico_City", label: "🇲🇽 Meksyk (CST/CDT)" },
  { iana: "Africa/Cairo",        label: "🇪🇬 Egipt / EG (EET, UTC+2)" },
  { iana: "Africa/Johannesburg", label: "🇿🇦 RPA / ZA (SAST, UTC+2)" },
  { iana: "Africa/Nairobi",      label: "🇰🇪 Kenia / KE (EAT, UTC+3)" },
  { iana: "UTC",                 label: "🌍 UTC (Czas Uniwersalny)" }
];

// Lista kodow regionow regulacyjnych (country code -> opis, profil CE/FCC)
const REGION_LIST = [
  { code: "PL", label: "PL - Polska (CE/ETSI, Europa)" },
  { code: "DE", label: "DE - Niemcy (CE/ETSI)" },
  { code: "GB", label: "GB - Wielka Brytania (CE/ETSI)" },
  { code: "FR", label: "FR - Francja (CE/ETSI)" },
  { code: "CZ", label: "CZ - Czechy (CE/ETSI)" },
  { code: "AT", label: "AT - Austria (CE/ETSI)" },
  { code: "NL", label: "NL - Holandia (CE/ETSI)" },
  { code: "SE", label: "SE - Szwecja (CE/ETSI)" },
  { code: "FI", label: "FI - Finlandia (CE/ETSI)" },
  { code: "IT", label: "IT - Wlochy (CE/ETSI)" },
  { code: "ES", label: "ES - Hiszpania (CE/ETSI)" },
  { code: "PT", label: "PT - Portugalia (CE/ETSI)" },
  { code: "GR", label: "GR - Grecja (CE/ETSI)" },
  { code: "RO", label: "RO - Rumunia (CE/ETSI)" },
  { code: "HU", label: "HU - Wegry (CE/ETSI)" },
  { code: "UA", label: "UA - Ukraina (CE/ETSI)" },
  { code: "TR", label: "TR - Turcja" },
  { code: "RU", label: "RU - Rosja" },
  { code: "US", label: "US - USA (FCC, pelna moc)" },
  { code: "CA", label: "CA - Kanada (FCC)" },
  { code: "JP", label: "JP - Japonia" },
  { code: "KR", label: "KR - Korea Poludniowa" },
  { code: "CN", label: "CN - Chiny (fabryczna moc TX)" },
  { code: "TW", label: "TW - Tajwan" },
  { code: "HK", label: "HK - Hongkong" },
  { code: "SG", label: "SG - Singapur" },
  { code: "AU", label: "AU - Australia" },
  { code: "NZ", label: "NZ - Nowa Zelandia" },
  { code: "IN", label: "IN - Indie" },
  { code: "BR", label: "BR - Brazylia" },
  { code: "MX", label: "MX - Meksyk" },
  { code: "ZA", label: "ZA - Republika Poludniowej Afryki" },
  { code: "AE", label: "AE - Zjednoczone Emiraty Arabskie" },
  { code: "SA", label: "SA - Arabia Saudyjska" }
];

const state = {
  ip: localStorage.getItem("xrm_ip") || "192.168.31.1",
  stok: null,
  savedPwd: "",
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

const xrmNativeAlert = window.alert.bind(window), xrmNativeConfirm = window.confirm.bind(window);
window.alert = message => xrmNativeAlert(translatePrompt(message));
window.confirm = message => xrmNativeConfirm(translatePrompt(message));

// Android serves the app from a secure local origin; router HTTP is handled by the native bridge.
let nextRequestId = 0;
const pendingRequests = new Map();
window.xrmNativeResult = (id, ok, result) => {
  const pending = pendingRequests.get(id);
  if (!pending) return;
  pendingRequests.delete(id);
  clearTimeout(pending.timer);
  if (ok) pending.resolve(result); else pending.reject(new Error(result));
};
async function requestRaw(path, method = "GET", body = null) {
  const encoded = body ? new URLSearchParams(body).toString() : "";
  if (window.AndroidRouter) {
    return new Promise((resolve, reject) => {
      const id = ++nextRequestId;
      const timer = setTimeout(() => { pendingRequests.delete(id); reject(new Error("Upłynął czas oczekiwania na router")); }, 65000);
      pendingRequests.set(id, { resolve, reject, timer });
      window.AndroidRouter.request(id, state.ip, path, method, encoded);
    });
  }
  const base = (location.port === "8088" || location.hostname === "localhost") ? "" : `http://${state.ip}`;
  const response = await fetch(base + path, { method, headers: { "Content-Type": "application/x-www-form-urlencoded" }, ...(body ? {body: encoded} : {}) });
  if (!response.ok) throw new Error(`HTTP ${response.status}`);
  return response.text();
}
async function digest(algorithm, value) {
  const hash = await crypto.subtle.digest(algorithm, new TextEncoder().encode(value));
  return Array.from(new Uint8Array(hash), b => b.toString(16).padStart(2, "0")).join("");
}
async function apiRequest(endpoint, method = "GET", body = null) {
  if (method !== "GET" && endpoint !== "xqsystem/login" && (!state.connected || !state.stok)) throw new Error("Najpierw połącz się z routerem.");
  const prefix = state.stok ? `/cgi-bin/luci/;stok=${state.stok}/api/` : "/cgi-bin/luci/api/";
  return JSON.parse(await requestRaw(prefix + endpoint, method, body));
}

// Bezpieczne parsowanie adresu IP ze stringa lub obiektu
function extractIpString(rawIp) {
  if (!rawIp) return "-";
  if (typeof rawIp === "string") return rawIp;
  if (Array.isArray(rawIp)) {
    const entry = rawIp.find(item => item && Number(item.active) === 1 && item.ip) || rawIp.find(item => item && item.ip);
    return entry ? extractIpString(entry.ip) : "-";
  }
  if (typeof rawIp === "object" && rawIp.ip) return extractIpString(rawIp.ip);
  return "-";
}

function sortNetworkEntries(entries, mode) {
  if (!mode || mode === "original") return entries;
  const byIp=mode.startsWith("ip-"), direction=mode.endsWith("-desc") ? -1 : 1;
  const collator=new Intl.Collator(state.lang === "en" ? "en" : "pl", {sensitivity:"base",numeric:true});
  const nameOf=item=>String(item.name || item.origin_name || item.oname || "");
  const addressOf=item=>{const ip=extractIpString(item.ip);return validIPv4(ip) ? ip.split(".").map(Number) : null;};
  return entries.sort((a,b)=>{
    if (byIp) {
      const ai=addressOf(a), bi=addressOf(b);
      if (!ai || !bi) return ai ? -1 : bi ? 1 : collator.compare(nameOf(a),nameOf(b));
      for(let i=0;i<4;i++) if(ai[i]!==bi[i]) return direction*(ai[i]-bi[i]);
      return collator.compare(nameOf(a),nameOf(b));
    }
    const an=nameOf(a), bn=nameOf(b);
    if (!an || !bn) return an ? -1 : bn ? 1 : 0;
    return direction*collator.compare(an,bn);
  });
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
  state.deviceId = null; state.initInfo = {};
  const token = extractStok(stokOrUrl);
  if (!token) return false;
  state.stok = token;
  try {
    const res = await apiRequest("misystem/status");
    if (res.code === 0) {
      setConnected(true);
      void refreshData();
      return true;
    }
  } catch (e) {}
  state.stok = null;
  setConnected(false);
  return false;
}

// Same nonce and hash selection as the tested desktop client. Only one login request.
async function loginWithPassword(pwd, user = "admin") {
  state.stok = null;
  try {
    const init = await apiRequest("xqsystem/init_info");
    state.initInfo = init;
    let deviceId = init.id || init.routerId;
    if (!deviceId || String(deviceId).includes("/")) {
      try {
        const html = await requestRaw("/cgi-bin/luci/web");
        const match = html.match(/deviceId\s*:\s*['"]([^'"]+)['"]/);
        if (match) deviceId = match[1];
      } catch (_) { /* Use the desktop client's fallback when the page is unavailable. */ }
    }
    if (!deviceId || String(deviceId).includes("/")) deviceId = "00:00:00:00:00:00";
    state.deviceId = deviceId;
    const nonce = `0_${deviceId}_${Math.floor(Date.now() / 1000)}_${Math.floor(Math.random() * 9000 + 1000)}`;
    const algorithm = Number(init.newEncryptMode) === 1 ? "SHA-256" : "SHA-1";
    const inner = await digest(algorithm, pwd + PUBLIC_KEY);
    const pwdHash = await digest(algorithm, nonce + inner);
    const resp = await apiRequest("xqsystem/login", "POST", { username: user, password: pwdHash, logtype: "2", nonce });
    if (resp.code !== 0) return false;
    state.stok = extractStok(resp.token || resp.url || "");
    if (!state.stok) return false;
    setConnected(true);
    void refreshData();
    return true;
  } catch (e) {
    console.warn("Logowanie nie powiodło się");
    return false;
  }
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
  viewLoaded.clear();
  state.wifiRendered = false; state.wanRendered = false; state.deviceId = null;
  state.wifiInfo = []; state.wanInfo = {}; state.pendingQosBand = null; state.qosActive = false; state.portServices = {}; state.portsStatus = []; state.portLinks = [];
  const led=document.getElementById("led-switch"), ledSave=document.getElementById("btn-save-led");
  if (led) led.disabled=true; if (ledSave) ledSave.disabled=true;
  state.stok = null;
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
  if (!state.connected || !state.stok || state.refreshing) return;
  state.refreshing = true;
  try {
    const [initResp, statusResp, devResp, wanResp] = await Promise.allSettled([
      apiRequest("xqsystem/init_info"),
      apiRequest("misystem/status"),
      apiRequest("misystem/devicelist"),
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
      if (state.currentView !== "wan" || !state.wanRendered) { renderWanInfo(state.wanInfo); state.wanRendered = true; }
    }

    if (statusResp.status === "fulfilled" && statusResp.value.code === 0) {
      renderDashboardStatus(state.status, state.initInfo, state.wanInfo);
    }

    if (devResp.status === "fulfilled" && devResp.value.code === 0) {
      state.devices = devResp.value.list || [];
      renderDevices();
    }

    // Odczyt rezerwacji, Wi-Fi, portów i zaawansowanych ustawień
    await fetchBindsAndPorts();
  } catch (e) {
    console.warn("Błąd odświeżania danych:", e);
  } finally { state.refreshing = false; }
}

async function fetchBindsAndPorts() {
  if (!state.connected || !state.stok) return;
  const session=state.stok;
  const calls=await Promise.allSettled([
    apiRequest("xqnetwork/macbind_info"), apiRequest("xqnetwork/wifi_detail_all"),
    apiRequest("misystem/get_ps_map"), apiRequest("xqnetwork/lan_info")
  ]);
  if (!state.connected || state.stok !== session) return;
  const available=item=>item.status === "fulfilled" && item.value && typeof item.value === "object" && (item.value.code === undefined || Number(item.value.code) === 0) ? item.value : null;
  const [bindResp,wifiResp,mapResp,lanResp]=calls.map(available);
  if (Array.isArray(bindResp?.list)) { state.binds=bindResp.list; renderBinds(); renderDevices(); }
  if (Array.isArray(wifiResp?.info)) {
    state.wifiInfo=wifiResp.info;
    state.wifiBsd=wifiResp.bsd !== undefined ? wifiResp.bsd : null;
    if (state.currentView !== "wifi" || !state.wifiRendered) { renderWifiInfo(state.wifiInfo,state.wifiBsd); state.wifiRendered=true; }
    if (state.currentView === "wifi" && !viewLoaded.has("wifi")) void loadViewData("wifi");
  }
  const rawPorts=mapResp?.ports ?? mapResp?.list;
  const rawLinks=lanResp?.linkList ?? lanResp?.info?.linkList;
  state.portsStatus=Array.isArray(rawPorts) ? rawPorts : [];
  state.portLinks=Array.isArray(rawLinks) ? rawLinks : [];
  renderPortsStatus(state.portsStatus,state.portLinks);
}

// ==========================================================================
// RENDEROWANIE WIDOKÓW
// ==========================================================================

// 1. Dashboard (Pulpit) - odwzorowanie 1:1 z gui.py L4795-4858
function renderDashboardStatus(s, init, wan) {
  // Model, ROM, Czas pracy i ID Routera
  const model = init?.displayName || init?.hardware || "Xiaomi BE7000";
  const hwCode = init?.hardware ? ` (kod ${init.hardware})` : "";
  const fw = `${init?.romversion || "-"} (${init?.countrycode || "-"})`;
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
  const rawTotal = String(mem.total || "").trim();
  let memTotal = parseFloat(rawTotal) || 0;
  if (/gb/i.test(rawTotal)) {
    memTotal = memTotal * 1024 * 1024 * 1024;
  } else if (/mb/i.test(rawTotal) || (memTotal > 0 && memTotal < 65536)) {
    memTotal = memTotal * 1024 * 1024;
  } else if (/kb/i.test(rawTotal)) {
    memTotal = memTotal * 1024;
  }
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
  sortNetworkEntries(filtered, document.getElementById("dev-sort-select")?.value);

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

    const ipStats = Array.isArray(d.ip) ? (d.ip.find(item => Number(item?.active) === 1) || d.ip[0] || {}) : {};
    const downSpeed = formatSpeed(d.statistics?.downspeed ?? ipStats.downspeed ?? 0);
    const upSpeed = formatSpeed(d.statistics?.upspeed ?? ipStats.upspeed ?? 0);
    const onlineSec = parseInt(d.statistics?.online || ipStats.online || d.uptime || 0);
    const uptimeStr = d.is_offline ? "Brak w sieci" : (onlineSec > 0 ? formatUptime(onlineSec) : "<1m");

    const auth = d.authority || {};
    const wanAllowed = auth.wan === undefined ? true : (auth.wan === 1);
    const isAdmin = auth.admin === 1 || d.is_cur === 1 || d.isap === 1;

    // Przyciski akcji
    let actionButtonsHtml = "";
    if (d.is_offline) {
      actionButtonsHtml = `
        <span class="badge badge-offline">Offline</span>
        <button class="btn-sm btn-secondary" onclick="openReserveModal(${escapeHtml(JSON.stringify(d.mac))}, ${escapeHtml(JSON.stringify(ipStr))}, ${escapeHtml(JSON.stringify(d.name))})">Edytuj</button>
        <button class="btn-sm btn-danger" onclick="deleteMacBind(${escapeHtml(JSON.stringify(d.mac))}, ${escapeHtml(JSON.stringify(d.name))})">Usuń</button>
      `;
    } else {
      // 1. Zarezerwowane vs Rezerwuj IP
      if (isBound) {
        actionButtonsHtml += `
          <span class="badge badge-bound">● Zarezerwowany</span>
          <button class="btn-sm btn-secondary" onclick="openReserveModal(${escapeHtml(JSON.stringify(d.mac))}, ${escapeHtml(JSON.stringify(ipStr))}, ${escapeHtml(JSON.stringify(d.name))})">Edytuj</button>
        `;
      } else if (d.mac && d.mac !== "-") {
        actionButtonsHtml += `
          <button class="btn-sm btn-primary" onclick="openReserveModal(${escapeHtml(JSON.stringify(d.mac))}, ${escapeHtml(JSON.stringify(ipStr))}, ${escapeHtml(JSON.stringify(d.name))})">+ Rezerwuj IP</button>
        `;
      }

      // 2. Blokada internetu WAN (zabezpieczenie admina)
      if (isAdmin) {
        actionButtonsHtml += `<span class="badge badge-admin">[Stacja Admina / AP]</span>`;
      } else {
        const btnCls = wanAllowed ? "btn-secondary" : "btn-danger";
        const btnTxt = wanAllowed ? "Blokuj Net" : "Odblokuj Net";
        actionButtonsHtml += `
          <button class="btn-sm ${btnCls}" onclick="toggleDeviceWanAccess(${escapeHtml(JSON.stringify(d.mac))}, ${wanAllowed})">${btnTxt}</button>
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
              <span class="ip-addr">${escapeHtml(ipStr)}</span>
              <span class="mac-addr">${escapeHtml(d.mac)}</span>
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
    document.getElementById("wan-stat-link").textContent = info.link == null ? "Brak danych" : String(info.link) === "1" ? "● Połączony (Link UP)" : "○ Rozłączony / Brak kabla";
    document.getElementById("wan-stat-link").className = String(info.link) === "1" ? "val bold text-success" : "val bold text-danger";
  }
  if (document.getElementById("wan-stat-proto")) {
    document.getElementById("wan-stat-proto").textContent = (det.wanType || info.proto || "-").toUpperCase();
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
  sortNetworkEntries(filtered, document.getElementById("bind-sort-select")?.value);

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
        <td class="mono highlight">${escapeHtml(ipStr)}</td>
        <td class="mono">${escapeHtml(b.mac)}</td>
        <td class="text-right">
          <button class="btn-secondary btn-sm" onclick="openReserveModal(${escapeHtml(JSON.stringify(b.mac))}, ${escapeHtml(JSON.stringify(ipStr))}, ${escapeHtml(JSON.stringify(bName))})">Edytuj</button>
          <button class="btn-danger btn-sm" onclick="deleteMacBind(${escapeHtml(JSON.stringify(b.mac))}, ${escapeHtml(JSON.stringify(bName))})">Usuń</button>
        </td>
      </tr>
    `;
  }).join("");
}

// 5. Wi-Fi i Pasma Radiowe (odwzorowanie 1:1 z Windows gui.py)
function setEncryptionSelect(id, code) {
  const select = document.getElementById(id);
  const value = String(code ?? "");
  if (!select) return;
  if (!value) {
    let option = select.querySelector('option[value=""]');
    if (!option) { option = document.createElement("option"); option.value = ""; option.textContent = "Brak danych o szyfrowaniu"; select.prepend(option); }
  } else if (![...select.options].some(option => option.value === value)) {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = value === "psk2+ccmp" ? "WPA2/WPA3 Personal (psk2+ccmp)" : `Szyfrowanie: ${value}`;
    select.append(option);
  }
  select.value = value;
}
// Move the same input elements between the shared section and the 2.4 GHz card.
// Reusing them preserves unsaved edits and their event listeners.
function setWifiPresentation(bsdOn) {
  const byId = id => document.getElementById(id);
  const common = byId("wifi-common-credentials");
  const fields = byId("wifi-2g-credentials-fields");
  const slot = byId("wifi-2g-credentials-slot");
  if (common && fields && slot) {
    (bsdOn ? common : slot).appendChild(fields);
    common.classList.toggle("hidden", !bsdOn);
  }
  byId("wifi-bsd-banner")?.classList.toggle("hidden", !bsdOn);
  byId("wifi-5g-sync-banner")?.classList.toggle("hidden", !bsdOn);
  byId("wifi-5g-credentials-box")?.classList.toggle("hidden", bsdOn);
  const text = (id, pl, en) => { const el=byId(id); if (el) el.textContent=state.lang === "en" ? en : pl; };
  text("wifi-common-heading", "Wspólna sieć Wi-Fi", "Shared Wi-Fi network");
  text("wifi-2g-card-title", bsdOn ? "Parametry radiowe 2.4 GHz" : "Pasmo 2.4 GHz", bsdOn ? "2.4 GHz radio settings" : "2.4 GHz band");
  text("wifi-5g-card-title", bsdOn ? "Parametry radiowe 5 GHz" : "Pasmo 5 GHz", bsdOn ? "5 GHz radio settings" : "5 GHz band");
  text("wifi-2g-ssid-lbl", bsdOn ? "Wspólna nazwa (SSID):" : "Nazwa sieci (SSID 2.4G):", bsdOn ? "Shared network name (SSID):" : "Network name (SSID 2.4G):");
  text("wifi-2g-enc-lbl", bsdOn ? "Wspólne szyfrowanie:" : "Szyfrowanie 2.4G:", bsdOn ? "Shared encryption:" : "2.4G encryption:");
  text("wifi-2g-pwd-lbl", bsdOn ? "Wspólne hasło Wi-Fi:" : "Hasło Wi-Fi 2.4G:", bsdOn ? "Shared Wi-Fi password:" : "2.4G Wi-Fi password:");
}
function renderWifiInfo(info, bsd) {
  if (!Array.isArray(info)) return;
  const bsdKnown = bsd === 0 || bsd === 1 || bsd === "0" || bsd === "1";
  const bsdOn = (bsd === 1 || bsd === "1");
  state.wifiBsd = bsdKnown ? (bsdOn ? 1 : 0) : null;
  const bsdSwitch = document.getElementById("wifi-switch-smartconnect");
  if (bsdSwitch) { bsdSwitch.checked = bsdOn; bsdSwitch.disabled = !bsdKnown; }
  setWifiPresentation(bsdOn);
  const banner = document.getElementById("wifi-bsd-banner");
  if (banner && !bsdKnown) {
    banner.textContent = state.lang === "en" ? "The router did not report Smart Connect status. Saving Wi-Fi settings is unavailable." : "Router nie podał stanu Smart Connect. Zapis ustawień Wi-Fi jest niedostępny.";
    banner.classList.remove("hidden");
  } else if (banner) {
    banner.textContent = state.lang === "en" ? "Smart Connect is enabled: both bands share the network name and password." : "Smart Connect jest włączony: oba pasma korzystają ze wspólnej nazwy i hasła.";
  }

  // Odnalezienie pasm (2.4G = kanał <= 14 lub index 1, 5G = index 2)
  const wifi2g = info.find(w => parseInt(w.channel || 0) <= 14 && parseInt(w.wifiIndex || 1) === 1) || info[0];
  const wifi5g = info.find(w => parseInt(w.channel || 0) > 14 || parseInt(w.wifiIndex || 0) >= 2) || info[1];

  if (wifi2g) {
    if (document.getElementById("wifi-2g-ssid")) document.getElementById("wifi-2g-ssid").value = wifi2g.ssid || "";
    if (document.getElementById("wifi-2g-pwd")) document.getElementById("wifi-2g-pwd").value = wifi2g.password || "";
    setEncryptionSelect("wifi-2g-enc", wifi2g.encryption);
    if (document.getElementById("wifi-2g-tx")) document.getElementById("wifi-2g-tx").value = wifi2g.txpwr || "max";
    if (document.getElementById("wifi-2g-channel")) document.getElementById("wifi-2g-channel").value = wifi2g.channel || "0";
    if (document.getElementById("wifi-2g-bw")) document.getElementById("wifi-2g-bw").value = wifi2g.bandwidth || "0";
    if (document.getElementById("wifi-2g-hidden")) document.getElementById("wifi-2g-hidden").checked = (Number(wifi2g.hidden) === 1);
    if (document.getElementById("wifi-2g-enable")) {
      const isOn = (Number(wifi2g.status ?? wifi2g.on ?? 1) === 1);
      document.getElementById("wifi-2g-enable").checked = isOn;
      document.getElementById("wifi-2g-enable-txt").textContent = isOn ? "Włączone" : "Wyłączone";
    }

    const status2 = wifi2g.status ?? wifi2g.on;
    const parts2 = [];
    if (wifi2g.channel !== undefined && wifi2g.channel !== null && wifi2g.channel !== "") parts2.push(`${state.lang === "en" ? "Channel" : "Kanał"}: ${String(wifi2g.channel) === "0" ? "Auto" : wifi2g.channel}`);
    if (wifi2g.bandwidth !== undefined && wifi2g.bandwidth !== null && wifi2g.bandwidth !== "") parts2.push(`${state.lang === "en" ? "Width" : "Szerokość"}: ${String(wifi2g.bandwidth) === "0" ? "Auto" : `${wifi2g.bandwidth} MHz`}`);
    if (status2 !== undefined && status2 !== null) parts2.push(`${state.lang === "en" ? "Status" : "Stan"}: ${Number(status2) === 1 ? (state.lang === "en" ? "Enabled" : "Włączone") : (state.lang === "en" ? "Disabled" : "Wyłączone")}`);
    if (document.getElementById("wifi-2g-summary")) document.getElementById("wifi-2g-summary").textContent = parts2.join(" | ") || "--";
  }

  if (wifi5g) {
    if (document.getElementById("wifi-5g-ssid")) document.getElementById("wifi-5g-ssid").value = wifi5g.ssid || "";
    if (document.getElementById("wifi-5g-pwd")) document.getElementById("wifi-5g-pwd").value = wifi5g.password || "";
    setEncryptionSelect("wifi-5g-enc", wifi5g.encryption);
    if (document.getElementById("wifi-5g-tx")) document.getElementById("wifi-5g-tx").value = wifi5g.txpwr || "max";
    if (document.getElementById("wifi-5g-channel")) document.getElementById("wifi-5g-channel").value = wifi5g.channel || "0";
    if (document.getElementById("wifi-5g-bw")) document.getElementById("wifi-5g-bw").value = wifi5g.bandwidth || "0";
    if (document.getElementById("wifi-5g-hidden")) document.getElementById("wifi-5g-hidden").checked = (Number(wifi5g.hidden) === 1);
    if (document.getElementById("wifi-5g-enable")) {
      const isOn = (Number(wifi5g.status ?? wifi5g.on ?? 1) === 1);
      document.getElementById("wifi-5g-enable").checked = isOn;
      document.getElementById("wifi-5g-enable-txt").textContent = isOn ? "Włączone" : "Wyłączone";
    }

    const status5 = wifi5g.status ?? wifi5g.on;
    const parts5 = [];
    if (wifi5g.channel !== undefined && wifi5g.channel !== null && wifi5g.channel !== "") parts5.push(`${state.lang === "en" ? "Channel" : "Kanał"}: ${String(wifi5g.channel) === "0" ? "Auto" : wifi5g.channel}`);
    if (wifi5g.bandwidth !== undefined && wifi5g.bandwidth !== null && wifi5g.bandwidth !== "") parts5.push(`${state.lang === "en" ? "Width" : "Szerokość"}: ${String(wifi5g.bandwidth) === "0" ? "Auto" : `${wifi5g.bandwidth} MHz`}`);
    if (status5 !== undefined && status5 !== null) parts5.push(`${state.lang === "en" ? "Status" : "Stan"}: ${Number(status5) === 1 ? (state.lang === "en" ? "Enabled" : "Włączone") : (state.lang === "en" ? "Disabled" : "Wyłączone")}`);
    if (document.getElementById("wifi-5g-summary")) document.getElementById("wifi-5g-summary").textContent = parts5.join(" | ") || "--";
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
function portRole(port) {
  const n=Number(port.port), svc=state.portServices || {};
  const includes=(value) => String(value ?? "").split(/[^0-9]+/).filter(Boolean).map(Number).includes(n);
  const wan=svc.multiwan, mapped=(Array.isArray(wan?.port_map) ? wan.port_map : []).find(x => Number(x.port) === n);
  const wanName=String(mapped?.name || "").toUpperCase();
  if (wanName === "WAN1" || wanName === "WAN") return "wan";
  if (Number(wan?.enable) === 1 && wanName === "WAN2") return "wan2";
  for (const role of ["lag","iptv","game"]) if (Number(svc[role]?.enable) === 1 && includes(svc[role]?.ports)) return role;
  const raw=String(port.service || "").toLowerCase();
  return ({multiwan:"wan2",wan1:"wan",gaming:"game"}[raw] || raw);
}
function getPortRecord(index, ports = state.portsStatus, links = state.portLinks) {
  const stored=(Array.isArray(ports) ? ports : []).find(p => p && Number(p.port) === index+1);
  if (stored) return stored;
  const link=links?.[index], candidate={port:index+1};
  // A link-list entry or an explicit service assignment provides evidence for the slot,
  // but neither an unknown role nor an unknown link is guessed.
  if (link !== undefined && link !== null) return candidate;
  if (portRole(candidate)) return candidate;
  return null;
}
function renderPortsStatus(ports, links = []) {
  const roles = {wan:"role_wan1",wan2:"role_dualwan",lag:"role_lag",iptv:"role_iptv",game:"role_game",lan:"role_lan"};
  document.querySelectorAll("#ports-hardware-grid .port-card").forEach((card,idx) => {
    const port=getPortRecord(idx,ports,links), status=card.querySelector(".port-status"), badge=card.querySelector(".port-badge");
    card.className="port-card";
    if (!port) { card.classList.add("port-unknown"); status.textContent="Stan nieznany"; badge.textContent="Rola nieznana"; return; }
    const role=portRole(port), linkInfo=links[idx];
    let linked=role === "wan" ? state.wanInfo?.link : (linkInfo && typeof linkInfo === "object" ? (linkInfo.link ?? linkInfo.status) : linkInfo);
    if (linked == null) linked=port.link;
    const known=linked !== undefined && linked !== null && (Number(linked) === 0 || Number(linked) === 1), up=known && Number(linked) === 1;
    const speed=(linkInfo && typeof linkInfo === "object" ? (linkInfo.negotiated_speed ?? linkInfo.link_speed) : null) ?? port.negotiated_speed ?? port.link_speed;
    badge.textContent=roles[role] ? t(roles[role]) : "Rola nieznana"; badge.className="port-badge";
    card.classList.add(!known ? "port-unknown" : !up ? "port-inactive" : `port-role-${roles[role] ? role : "unknown"}`);
    status.className=`port-status ${up ? "status-up" : "status-down"}`;
    status.textContent=!known ? "Stan nieznany" : !up ? "○ Rozłączony" : `● Połączony${speed != null && speed !== "" ? ` (${speed})` : ""}`;
  });
}

// ==========================================================================
// OBSŁUGA INTERFEJSU (DRAWER, ZAKŁADKI, DYNAMICZNE FORMULARZE)
// ==========================================================================
function setupUI() {
  // 1. Hamburger i Drawer
  const btnHam = document.getElementById("btn-hamburger");
  const btnCloseDrawer = document.getElementById("btn-close-drawer");
  const drawer = document.getElementById("nav-drawer");
  const backdrop = document.getElementById("drawer-backdrop");

  const openDrawer = () => {
    document.getElementById("app-root").classList.add("drawer-open");
    backdrop.classList.add("open");
    btnHam.classList.remove("nav-pulse");
  };

  const closeDrawer = () => {
    document.getElementById("app-root").classList.remove("drawer-open");
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
  document.querySelectorAll(".nav-item, .btn-wizard[data-view]").forEach(item => {
    item.addEventListener("click", () => {
      const viewId = item.dataset.view;
      if (!viewId) return;

      document.querySelectorAll(".nav-item").forEach(i => i.classList.remove("active"));
      item.classList.add("active");

      document.querySelectorAll(".content-view").forEach(v => v.classList.remove("active"));
      const targetView = document.getElementById(`view-${viewId}`);
      if (targetView) targetView.classList.add("active");

      state.currentView = viewId;
      if (state.connected) loadViewData(viewId);
      setTimeout(closeDrawer, 200);
    });
  });

  // 2. Belka górna: Język PL/EN
  document.querySelectorAll("#lang-toggle button").forEach(btn => {
    btn.addEventListener("click", () => {
      state.lang = btn.dataset.lang;
      localStorage.setItem("xrm_lang", state.lang);
      document.querySelectorAll("#lang-toggle button").forEach(item => {
        item.classList.toggle("active", item === btn);
      });
      applyStaticTranslation();
      setWifiPresentation(document.getElementById("wifi-switch-smartconnect").checked);
      setConnected(state.connected);
      if (state.portsStatus.length) renderPortsStatus(state.portsStatus,state.portLinks || []);
      if (state.natSnapshot) renderNat();
    });
  });

  // Belka górna: Przełącznik układu (Auto / Telefon / Tablet)
  document.querySelectorAll("#layout-toggle button").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll("#layout-toggle button").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      const mode = btn.dataset.layout;
      applyLayoutMode(mode);
    });
  });

  // Belka górna: Odświeżanie
  document.getElementById("btn-global-refresh").addEventListener("click", async () => {
    const btn = document.getElementById("btn-global-refresh");
    btn.style.transform = "rotate(180deg)";
    await refreshData();
    if (state.connected && state.currentView !== "dashboard") { viewLoaded.delete(state.currentView); await loadViewData(state.currentView); }
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
    if (!state.connected || !Object.keys(state.wanInfo).length) { alert("Najpierw odczytaj ustawienia WAN z routera."); return; }
    if (!confirm("Zapisać ustawienia WAN? Może to przerwać dostęp do Internetu.")) return;
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
      if (!document.getElementById("wan-pppoe-user").value.trim() || !document.getElementById("wan-pppoe-pwd").value) { alert("Podaj nazwę użytkownika i hasło PPPoE."); return; }
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
      setWifiPresentation(switchSmart.checked);
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
    if (!state.connected || state.wifiInfo.length < 2 || state.wifiBsd === null) { alert("Najpierw odczytaj pełne ustawienia obu pasm Wi-Fi z routera."); return; }
    if (!confirm("Zapisać ustawienia Wi-Fi? Połączenie może zostać przerwane.")) return;
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

    if (!ssid2g || !enc2g || (enc2g !== "none" && !pwd2g) || !ssid5g || !enc5g || (enc5g !== "none" && !pwd5g)) { alert("Podaj nazwy sieci i hasła dla zabezpieczonych pasm."); return; }
    const payload = {
      bsd: String(bsd), on1: String(on2g), ssid1: ssid2g, pwd1: pwd2g,
      encryption1: enc2g, channel1: ch2g, bandwidth1: bw2g, hidden1: String(hid2g), txpwr1: tx2g,
      on2: String(on5g), ssid2: ssid5g, pwd2: pwd5g, encryption2: enc5g,
      channel2: ch5g, bandwidth2: bw5g, hidden2: String(hid5g), txpwr2: tx5g,
      channel: ch2g, bandwidth: bw2g, txpwr: tx2g, channel50: ch5g,
      bandwidth50: bw5g, txpwr50: tx5g, isDFS: "0"
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
  const roleSelect = document.getElementById("ports-function-select");
  if (roleSelect) {
    roleSelect.addEventListener("change", () => {
      document.querySelectorAll(".port-subview").forEach(s => s.classList.add("hidden"));
      const targetId = `port-sec-${roleSelect.value}`;
      const sec = document.getElementById(targetId);
      if (sec) sec.classList.remove("hidden");
    });
  }

  setupAdditionalControls(); setupNatControls(); setupSystemEnhancements(); setupServices();

  // Wyszukiwarka urządzeń i rezerwacji
  document.getElementById("dev-search-input")?.addEventListener("input", renderDevices);
  document.getElementById("dev-show-offline")?.addEventListener("change", renderDevices);
  document.getElementById("dev-sort-select")?.addEventListener("change", renderDevices);
  document.getElementById("dhcp-search-input")?.addEventListener("input", renderBinds);
  document.getElementById("bind-sort-select")?.addEventListener("change", renderBinds);

  // Inicjalizacja modali
  setupLoginModal();
  setupReserveModal();
  setupSystemTools();
}

function renderMesh(graph) {
  const text = (id, value) => { const el = document.getElementById(id); if (el) el.textContent = String(value ?? "--"); };
  const hardware = {RC06:"Xiaomi Router 7000 (BE7000)", RN02:"Xiaomi Router BE6500"};
  text("mesh-master-name", [hardware[graph.hardware] || graph.hardware || "Router", graph.name].filter(Boolean).join(" - "));
  text("mesh-master-ip", graph.ip || state.ip);
  text("mesh-master-mac", graph.mac || "--");
  text("mesh-master-clients", graph.onlines ?? state.devices.length);
  const leafs = Array.isArray(graph.leafs) ? graph.leafs : Array.isArray(graph.re) ? graph.re : null;
  const satellites = leafs ? [...leafs] : [];
  const known = new Set(satellites.map(node => extractIpString(node.ip)));
  for (const d of state.devices) {
    const ip = extractIpString(d.ip);
    if (Number(d.isap) > 0 && ip !== "-" && ip !== state.ip && !known.has(ip)) {
      satellites.push({name:d.name || d.oname,ip,mac:d.mac,hardware:d.hardware}); known.add(ip);
    }
  }
  const container = document.getElementById("mesh-satellites-list");
  container.replaceChildren();
  if (!satellites.length) {
    const empty = document.createElement("div"); empty.className="empty-state";
    empty.textContent = leafs ? "Nie wykryto dodatkowych węzłów Mesh." : "Router nie podał listy węzłów Mesh.";
    container.append(empty); return;
  }
  satellites.forEach(sat => {
    const card=document.createElement("div"); card.className="mesh-node-card satellite";
    const title=document.createElement("h3"); title.textContent=[hardware[sat.hardware] || sat.hardware || "Satelita",sat.name].filter(Boolean).join(" - ");
    const info=document.createElement("div"); info.className="node-meta";
    const parts=[`IP: ${extractIpString(sat.ip)}`,`MAC: ${sat.mac || "--"}`];
    if (sat.onlines !== undefined) parts.push(`Klienci: ${sat.onlines}`);
    const link=String(sat.link_type || sat.backhaul || "").toLowerCase();
    if (link) parts.push(link.includes("wire") || link.includes("lan") ? "Połączenie kablowe" : "Połączenie Wi-Fi");
    info.textContent=parts.join("  |  "); card.append(title,info); container.append(card);
  });
}

// Data are loaded on demand so auto-refresh does not overwrite an edited form.
const viewLoaded = new Set();
const $id = id => document.getElementById(id);
async function loadViewData(view) {
  if (viewLoaded.has(view)) return;
  try {
    if (view === "services") {
      const [ddns,vpn,status,smart] = await Promise.allSettled([apiRequest("xqnetwork/ddns"),apiRequest("xqsystem/vpn"),apiRequest("xqsystem/vpn_status"),apiRequest("misystem/smartvpn_info")]);
      state.serviceSnapshot={ddns:ddns.status==="fulfilled" ? ddns.value : null,vpn:vpn.status==="fulfilled" ? vpn.value : null,status:status.status==="fulfilled" ? status.value : null,smart:smart.status==="fulfilled" ? smart.value : null};
      renderServices();
    } else if (view === "mesh") {
      const topo = await apiRequest("misystem/topo_graph");
      if (topo.code !== 0 || !topo.graph || typeof topo.graph !== "object") throw Error("Brak danych topologii");
      state.topoGraph = topo.graph;
      renderMesh(topo.graph);
    } else if (view === "reboot") {
      const [timeResult,ledResult]=await Promise.allSettled([apiRequest("misystem/sys_time"),apiRequest("misystem/led")]);
      const time=timeResult.status === "fulfilled" ? timeResult.value : null;
      const led=ledResult.status === "fulfilled" ? ledResult.value : null;
      if (time && Number(time.code) === 0) {
        let tStr = "--";
        const tObj = (typeof time.time === "object" && time.time !== null) ? time.time : null;
        if (tObj && tObj.year) {
          const y = tObj.year;
          const m = String(tObj.month || 1).padStart(2, "0");
          const d = String(tObj.day || 1).padStart(2, "0");
          const hh = String(tObj.hour || 0).padStart(2, "0");
          const mm = String(tObj.min || 0).padStart(2, "0");
          const ss = String(tObj.sec || 0).padStart(2, "0");
          const tz = tObj.timezone || "";
          tStr = `${y}-${m}-${d} ${hh}:${mm}:${ss}${tz ? " (" + tz + ")" : ""}`;
        } else if (typeof time.time === "string") {
          tStr = time.time;
        } else if (time.datetime || time.localtime) {
          tStr = String(time.datetime || time.localtime);
        }
        $id("system-router-time").textContent = `Czas routera: ${tStr}`;
      }
      const ledAvailable=led && (led.code === undefined || Number(led.code) === 0) && [0,1].includes(Number(led.status)) && led.status !== null && led.status !== undefined;
      $id("led-switch").disabled=!ledAvailable;$id("btn-save-led").disabled=!ledAvailable;
      if (ledAvailable) { $id("led-switch").checked=Number(led.status)===1;$id("led-status-lbl").textContent=Number(led.status)===1 ? "Włączone" : "Wyłączone"; }
    } else if (view === "wifi") {
      if (!state.wifiInfo.length) throw Error("Brak danych Wi-Fi");
      const first = state.wifiInfo[0] || {};
      const calls = await Promise.allSettled([apiRequest("xqnetwork/get_twt"),apiRequest("xqnetwork/get_miotrelay_switch"),apiRequest("xqnetwork/get_wifi_silence"),apiRequest("xqnetwork/get_aimesh_config")]);
      const set = (id,value) => { if (value === undefined || value === null) return; const el=$id(`wifi-adv-${id}`); el.checked=Boolean(Number(value)); el.disabled=false; const label=$id(`wifi-adv-${id}-lbl`); if(label) label.textContent=el.checked ? "Włączone" : "Wyłączone"; };
      if (first.ax !== undefined) set("w5", Number(first.ax) === 0 ? 1 : 0);
      if (first.txbf !== undefined) set("mimo", [1,3].includes(Number(first.txbf)) ? 1 : 0);
      if (calls[0].status === "fulfilled" && calls[0].value.code === 0) set("twt",calls[0].value.status);
      if (calls[1].status === "fulfilled" && calls[1].value.code === 0) set("miotrelay",calls[1].value.switch);
      if (calls[2].status === "fulfilled" && calls[2].value.code === 0) set("silence",calls[2].value.status);
      if (calls[3].status === "fulfilled" && calls[3].value.code === 0 && calls[3].value.manual_roaming_setting !== undefined) {
        renderAimeshConfig(calls[3].value); $id("wifi-adv-roam").disabled=false;
      }
    } else if (view === "lan") {
      const [lan, dhcp] = await Promise.all([apiRequest("xqnetwork/lan_info"), apiRequest("xqnetwork/lan_dhcp")]);
      const ipv4 = lan.info?.ipv4?.[0], info = dhcp.info;
      if (!ipv4?.ip || !ipv4.mask || !info || info.start === undefined || info.limit === undefined || !info.leasetime) throw Error("Niepełny odczyt LAN/DHCP");
      $id("lan-ip-input").value = ipv4.ip; $id("lan-mask-input").value = ipv4.mask || "";
      const prefix = ipv4.ip.split(".").slice(0, 3).join(".");
      $id("dhcp-start-input").value = `${prefix}.${info.start}`;
      $id("dhcp-end-input").value = `${prefix}.${Number(info.start) + Number(info.limit) - 1}`;
      const lease = String(info.leasetime || "").match(/^(\d+)\s*([mhsd]?)$/i);
      if (lease) $id("dhcp-lease-input").value = Math.round(Number(lease[1]) * ({h:60,d:1440,s:1/60}[lease[2].toLowerCase()] || 1));
      $id("dhcp-dns1-input").value = typeof info.dns1 === "string" ? info.dns1 : "";
      $id("dhcp-dns2-input").value = typeof info.dns2 === "string" ? info.dns2 : "";
      state.lanInfo = lan; state.lanDhcp = dhcp;
    } else if (view === "ports") {
      const services=["lag","multiwan","iptv","game"];
      const results=await Promise.allSettled(services.map(service => apiRequest(`misystem/get_ps_service?service=${service}`)));
      const available={};
      services.forEach((service,i) => {
        const r=results[i];
        if (r.status === "fulfilled" && r.value && (r.value.code === undefined || Number(r.value.code) === 0) && r.value[service] && typeof r.value[service] === "object") available[service]=r.value[service];
      });
      state.portServices=available;
      renderPortsStatus(state.portsStatus || [],state.portLinks || []);
      for (const [id,service] of [["lag","lag"],["dualwan","multiwan"],["iptv","iptv"],["game","game"]]) $id(`btn-save-${id}`).disabled = available[service]?.enable === undefined;
      const missing=services.filter(service => available[service]?.enable === undefined);
      $id("ports-read-status").textContent=missing.length ? `Nie udało się odczytać ustawień: ${missing.join(", ")}.` : "";
      const {lag,multiwan:wan,iptv,game}=available;
      if (lag) {
        $id("lag-enabled-chk").checked = Number(lag.enable) === 1;
        const lagPorts=String(lag.ports || "").match(/\d+/g);
        if (lagPorts?.length >= 2) $id("lag-ports-select").value=lagPorts.slice(0,2).join("+");
        $id("lag-mode-select").value=Number(lag.mode) === 2 ? "lacp" : "static";
      }
      if (wan) {
        $id("dualwan-enabled-chk").checked=Number(wan.enable) === 1;
        const wan2=(Array.isArray(wan.port_map) ? wan.port_map : []).find(p => p.name === "WAN2");
        if (wan2?.port) $id("dualwan-port-select").value=String(wan2.port);
        $id("dualwan-mode-select").value=Number(wan.policy?.mode) === 1 ? "failover" : "load";
      }
      for (const [name,data] of [["iptv",iptv],["game",game]]) if (data) {
        $id(`${name}-enabled-chk`).checked=Number(data.enable) === 1;
        if (data.ports) $id(`${name}-port-select`).value=String(data.ports);
      }
      if (iptv) $id("iptv-vid-input").value=Number(iptv.vid)>0 ? iptv.vid : "";
    } else if (view === "nat") {
      // Each part is independent: a failed DMZ or range request must not hide the others.
      const calls=await Promise.allSettled([
        apiRequest("xqsystem/dmz"), apiRequest("xqsystem/portforward?ftype=1"),
        apiRequest("xqsystem/portforward?ftype=2"), apiRequest("xqsystem/upnp")
      ]);
      const available = item => item.status === "fulfilled" && item.value && typeof item.value === "object" && (item.value.code === undefined || Number(item.value.code) === 0) ? item.value : null;
      const [dmz,singleResponse,rangeResponse,upnpResponse]=calls.map(available);
      const single=Array.isArray(singleResponse?.list) ? singleResponse.list : null;
      const range=Array.isArray(rangeResponse?.list) ? rangeResponse.list : null;
      const upnp=upnpResponse ? {...upnpResponse,code:0} : null;
      const dmzAvailable=dmz !== null && dmz.status !== undefined && dmz.status !== null && Number.isFinite(Number(dmz.status));
      if (dmzAvailable) {
        $id("dmz-enabled-chk").checked = Number(dmz.status) === 1;
        $id("dmz-ip-input").value = dmz.ip || dmz.lanip || "";
      }
      state.natHasRules = single !== null && range !== null ? single.length + range.length > 0 : null;
      state.natSnapshot={single,range,upnp,dmzAvailable};
      renderNat();
      const missing=[];
      if (single === null) missing.push("pojedynczych portów");
      if (range === null) missing.push("zakresów portów");
      if (!dmzAvailable) missing.push("DMZ");
      if (!upnp || upnp.status === undefined || upnp.status === null || ![0,1].includes(Number(upnp.status))) missing.push("UPnP");
      $id("nat-read-status").textContent = missing.length ? `Nie udało się odczytać: ${missing.join(", ")}. Spróbuj odświeżyć.` : "";
      $id("btn-save-dmz").disabled = !dmzAvailable || state.natHasRules === null;
      $id("dmz-enabled-chk").disabled = !dmzAvailable || state.natHasRules === null;
      $id("btn-add-nat-rule").disabled = single === null || !dmzAvailable;
      $id("btn-add-range").disabled = range === null || !dmzAvailable;
    } else if (view === "qos") {
      const qos = await apiRequest("misystem/qos_info");
      if (qos.code !== 0 || !qos.status) throw Error("Brak danych QoS");
      state.qosActive = Number(qos.status.on) === 1;
      $id("qos-enabled-chk").checked = state.qosActive;
      $id("qos-download").value = state.pendingQosBand?.download ?? qos.band?.download ?? "";
      $id("qos-upload").value = state.pendingQosBand?.upload ?? qos.band?.upload ?? "";
      const names = ["auto","game","web","video"];
      document.querySelectorAll("#qos-mode-selector button").forEach(b => b.classList.toggle("active", b.dataset.mode === names[Number(qos.status.mode)]));
    } else return;
    viewLoaded.add(view);
  } catch (e) { console.warn("Nie udało się odczytać danych widoku", view); }
}
function validIPv4(s) { return /^(?:\d{1,3}\.){3}\d{1,3}$/.test(s) && s.split(".").every(n => Number(n) <= 255); }
async function sendChange(view, endpoint, payload, question, method = "POST") {
  if (!state.connected || !viewLoaded.has(view)) { alert("Najpierw odczytaj bieżące ustawienia tego widoku z routera."); return false; }
  if (!confirm(question)) return false;
  try {
    const result = await apiRequest(endpoint, method, payload);
    if (result.code !== 0) throw Error(result.msg || `kod ${result.code}`);
    alert("Router potwierdził zapis."); viewLoaded.delete(view); await loadViewData(view); return true;
  } catch (e) { alert("Nie udało się potwierdzić zmiany: " + e.message); return false; }
}
function setupAdditionalControls() {
  // Kreator - buduj selektory strefy i regionu (moze byc wywolane przed setupSystemEnhancements)
  buildTzSelect("wiz-tz-select");
  buildRegionSelect("wiz-region-select", "PL");

  // Kreator - przycisk Zastosuj i Uruchom Router
  const btnWizApply = $id("btn-wizard-apply");
  if (btnWizApply) {
    btnWizApply.disabled = false;
    btnWizApply.title = "";
    btnWizApply.addEventListener("click", async () => {
      if (!state.connected) return alert("Najpierw połącz się z routerem.");
      const proto = $id("wiz-proto")?.value || "dhcp";
      const ssid = $id("wiz-ssid")?.value.trim() || "";
      const wifiPwd = $id("wiz-pwd")?.value.trim() || "";
      const samePwd = $id("wiz-same-pwd")?.checked ?? true;
      const tzIana = $id("wiz-tz-select")?.value || "";
      const regionCode = $id("wiz-region-select")?.value || "";
      const tzPosix = TZ_POSIX_MAP[tzIana] || "";

      if (!ssid) return alert("Podaj nazwę sieci Wi-Fi (SSID).");
      if (wifiPwd && wifiPwd.length < 8) return alert("Hasło Wi-Fi musi mieć co najmniej 8 znaków.");

      let summary = `Typ WAN: ${proto.toUpperCase()}\nSSID: ${ssid}`;
      if (tzIana) summary += `\nStrefa czasowa: ${tzIana} (${tzPosix || "nieznana"})`;
      if (regionCode) summary += `\nRegion RF: ${regionCode}`;
      if (!confirm(`Zastosować ustawienia na routerze?\n\n${summary}`)) return;

      btnWizApply.disabled = true;
      const errors = [];

      // 1. Ustaw Wi-Fi
      if (ssid) {
        try {
          const r = await apiRequest("xqnetwork/set_all_wifi", "POST", {
            bsd: "1", ssid1: ssid, ssid2: ssid,
            pwd1: wifiPwd, pwd2: wifiPwd,
            encryption1: wifiPwd ? "sae-mixed" : "none",
            encryption2: wifiPwd ? "sae-mixed" : "none",
            on1: "1", on2: "1", txpwr1: "max", txpwr2: "max",
            channel1: "0", channel2: "0", bandwidth1: "0", bandwidth2: "0",
            hidden1: "0", hidden2: "0", isDFS: "0"
          });
          if (r.code !== 0) errors.push(`Wi-Fi: ${r.msg || r.code}`);
        } catch(e) { errors.push(`Wi-Fi: ${e.message}`); }
      }

      // 2. Ustaw strefę czasową i czas
      if (tzPosix) {
        try {
          const d = new Date(), pad = n => String(n).padStart(2, "0");
          const time = `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
          const query = new URLSearchParams({time, timezone: tzPosix});
          const r = await apiRequest(`misystem/set_sys_time?${query}`);
          if (r.code !== 0) errors.push(`Czas/TZ: ${r.msg || r.code}`);
        } catch(e) { errors.push(`Czas/TZ: ${e.message}`); }
      }

      // 3. Ustaw region (RegDomain)
      if (regionCode) {
        try {
          const r = await apiRequest("xqsystem/set_country_code", "POST", {country: regionCode});
          if (r.code !== 0) errors.push(`Region: ${r.msg || r.code}`);
        } catch(e) { errors.push(`Region: ${e.message}`); }
      }

      btnWizApply.disabled = false;
      if (errors.length) {
        alert(`Kreator zakończył z błędami:\n${errors.join("\n")}`);
      } else {
        alert("Kreator zakończył konfigurację routera.");
      }
    });
  }
  $id("btn-restart-wan").addEventListener("click", async () => {
    if (!state.connected || !confirm("Zrestartować połączenie WAN? Dostęp do Internetu zostanie przerwany.")) return;
    try {
      await apiRequest("xqnetwork/pppoe_stop");
      await new Promise(resolve => setTimeout(resolve, 1000));
      const result = await apiRequest("xqnetwork/pppoe_start");
      alert(result.code === 0 ? "Router potwierdził uruchomienie połączenia." : "Błąd routera: " + (result.msg || result.code));
    } catch (_) { alert("Nie udało się potwierdzić restartu WAN."); }
  });
  $id("btn-toggle-pppoe-pwd").addEventListener("click", () => { const el=$id("wan-pppoe-pwd"); el.type=el.type === "password" ? "text" : "password"; });
  $id("btn-save-lan-ip").addEventListener("click", () => {
    const ip=$id("lan-ip-input").value.trim(), mask=$id("lan-mask-input").value.trim();
    if (!validIPv4(ip) || !validIPv4(mask)) return alert("Podaj poprawny adres IP i maskę.");
    sendChange("lan", "xqnetwork/set_lan_ip", {ip,mask}, "Zmienić adres LAN? Połączenie z routerem może zostać przerwane.");
  });
  $id("btn-save-dhcp").addEventListener("click", () => {
    if (!state.connected || !state.lanInfo?.info?.ipv4?.[0] || !state.lanDhcp?.info) return alert("Najpierw odczytaj ustawienia LAN i DHCP.");
    const begin=$id("dhcp-start-input").value.trim(), endIP=$id("dhcp-end-input").value.trim(), lease=Number($id("dhcp-lease-input").value);
    if (state.lanInfo.info.ipv4[0].mask !== "255.255.255.0" || !validIPv4(begin) || !validIPv4(endIP) || begin.split(".").slice(0,3).join(".") !== endIP.split(".").slice(0,3).join(".")) return alert("Ta wersja obsługuje pulę DHCP tylko w podsieci /24. Podaj poprawny zakres.");
    const start=Number(begin.split(".")[3]), end=Number(endIP.split(".")[3]);
    if (start < 2 || end > 254 || end < start || !Number.isInteger(lease) || lease < 2 || lease > 2880) return alert("Niepoprawny zakres DHCP lub czas dzierżawy (2-2880 minut).");
    const dns1=$id("dhcp-dns1-input").value.trim(),dns2=$id("dhcp-dns2-input").value.trim(),old=state.lanDhcp.info;
    if ((dns1 && !validIPv4(dns1)) || (dns2 && !validIPv4(dns2))) return alert("Podaj poprawne adresy IPv4 serwerów DNS.");
    if ((old.dns1 && !dns1) || (old.dns2 && !dns2)) return alert("Nie potwierdzono sposobu usuwania adresu DNS. Wpisz adres DNS zamiast pozostawiać wcześniej wypełnione pole puste.");
    const payload={start,end,limit:end-start+1,leasetime:`${lease}m`,leasetimeNum:lease,leasetimeUnit:"m",ignore:"0"};
    if (dns1) payload.dns1=dns1; if (dns2) payload.dns2=dns2;
    sendChange("lan", "xqnetwork/set_lan_dhcp", payload, "Zapisać ustawienia serwera DHCP?");
  });
  for (const name of ["lag","dualwan","iptv","game"]) $id(`btn-save-${name}`).addEventListener("click", () => {
    const service=name === "dualwan" ? "multiwan" : name;
    if (!state.connected || state.portServices?.[service]?.enable === undefined) return alert("Najpierw odczytaj ustawienia wybranej funkcji portów.");
    const enable=$id(`${name}-enabled-chk`).checked ? 1 : 0;
    const payload={service:name === "dualwan" ? "multiwan" : name,enable};
    if (name === "lag") { payload.ports=$id("lag-ports-select").value.replace("+"," "); payload.mode=$id("lag-mode-select").value === "lacp" ? 2 : 1; }
    if (name === "dualwan") { payload.port=$id("dualwan-port-select").value; payload.mode=$id("dualwan-mode-select").value === "load" ? 0 : 1; }
    if (name === "iptv") { payload.ports=$id("iptv-port-select").value; payload.vid=$id("iptv-vid-input").value || -1; payload.profile=0; payload.priority=-1; }
    if (name === "game") payload.ports=$id("game-port-select").value;
    if (!payload.ports && name !== "dualwan") return alert("Wybierz poprawne porty.");
    sendChange("ports", "misystem/set_ps_service", payload, "Zmienić konfigurację portu? Połączenie sieciowe może zostać przerwane.");
  });
  $id("btn-save-dmz").addEventListener("click", () => {
    if (!state.connected || !viewLoaded.has("nat") || !state.natSnapshot?.dmzAvailable || state.natHasRules === null) return alert("Najpierw odczytaj pełne ustawienia DMZ i przekierowań.");
    const on=$id("dmz-enabled-chk").checked, ip=$id("dmz-ip-input").value.trim();
    if (on && (!validIPv4(ip) || state.natHasRules)) return alert(state.natHasRules ? "Najpierw usuń istniejące reguły przekierowania portów." : "Podaj poprawny adres IP.");
    sendChange("nat", on ? "xqsystem/set_dmz" : "xqsystem/dmz_off", on ? {ip} : null, "Zmienić ustawienia DMZ?", on ? "POST" : "GET");
  });
  $id("btn-add-nat-rule").addEventListener("click", async () => {
    if (!state.connected || !Array.isArray(state.natSnapshot?.single) || !state.natSnapshot?.dmzAvailable) return alert("Najpierw odczytaj reguły portów i stan DMZ.");
    const name=$id("nat-name-input").value.trim(), ip=$id("nat-target-ip").value.trim(), sport=Number($id("nat-ext-port").value), dport=Number($id("nat-int-port").value);
    if (!name || !validIPv4(ip) || !Number.isInteger(sport) || sport<1 || sport>65535 || !Number.isInteger(dport) || dport<1 || dport>65535) return alert("Uzupełnij nazwę, adres IP i numery portów 1-65535.");
    const proto={tcp:1,udp:2,all:3}[$id("nat-proto-select").value];
    if (await sendChange("nat", "xqsystem/add_redirect", {name,ip,sport,dport,proto}, "Dodać przekierowanie portu?")) {
      try { const res=await apiRequest("xqsystem/redirect_apply", "POST", {}); if (res.code !== 0) alert("Nie udało się potwierdzić aktywacji reguły."); } catch (_) { alert("Nie udało się potwierdzić aktywacji reguły."); }
    }
  });
  $id("btn-save-qos-band").addEventListener("click", () => {
    const down=Number($id("qos-download").value), up=Number($id("qos-upload").value);
    if (!Number.isInteger(down) || down < 1 || !Number.isInteger(up) || up < 1) return alert("Podaj prędkości pobierania i wysyłania w Mbps.");
    if (!state.connected || !viewLoaded.has("qos")) return alert("Najpierw odczytaj ustawienia QoS.");
    if (!state.qosActive) { state.pendingQosBand={upload:up,download:down}; return alert("Prędkości zapamiętano w aplikacji. Zostaną wysłane po włączeniu QoS."); }
    sendChange("qos", `misystem/set_band?upload=${up}&download=${down}`, null, "Zapisać deklarowaną prędkość łącza?", "GET");
  });
  document.querySelectorAll("#qos-mode-selector button").forEach(b=>b.addEventListener("click",()=>document.querySelectorAll("#qos-mode-selector button").forEach(x=>x.classList.toggle("active",x===b))));
  $id("btn-save-qos").addEventListener("click", async () => {
    if (!state.connected || !viewLoaded.has("qos")) return alert("Najpierw odczytaj bieżące ustawienia QoS.");
    if (!confirm("Zmienić ustawienia QoS?")) return;
    try {
      const on=$id("qos-enabled-chk").checked ? 1 : 0;
      const mode={auto:0,game:1,web:2,video:3}[document.querySelector("#qos-mode-selector button.active").dataset.mode];
      const a=await apiRequest(`misystem/qos_switch?on=${on}`); if (a.code !== 0) throw Error(a.msg || a.code);
      if (on) {
        const b=await apiRequest(`misystem/qos_mode?mode=${mode}`); if (b.code !== 0) throw Error(b.msg || b.code);
        if (state.pendingQosBand) { const {upload,download}=state.pendingQosBand; const c=await apiRequest(`misystem/set_band?upload=${upload}&download=${download}`); if(c.code!==0) throw Error(c.msg || c.code); state.pendingQosBand=null; }
      }
      alert("Router potwierdził zapis QoS."); viewLoaded.delete("qos"); await loadViewData("qos");
    } catch(e) { alert("Nie udało się potwierdzić całej zmiany QoS: " + e.message); }
  });
}

// Obsługa zaawansowanych przełączników Wi-Fi
function setupAdvancedWifiSwitches() {
  const mapping = {
    w5: ["xqnetwork/set_wifi_ax", on => ({ax:on ? "0" : "1",isDFS:"0"})],
    twt: ["xqnetwork/set_twt", on => ({on:String(on),status:String(on)})],
    mimo: ["xqnetwork/set_wifi_txbf", on => ({txbf:String(on),isDFS:"0"})],
    miotrelay: ["xqnetwork/miotrelay_switch", on => ({on:String(on),switch:String(on)})],
    silence: ["xqnetwork/set_wifi_silence", on => ({on:String(on),status:String(on)})]
  };
  for (const [name,[endpoint,payload]] of Object.entries(mapping)) {
    const el=$id(`wifi-adv-${name}`); el.disabled=true;
    el.addEventListener("change", async () => {
      const next=el.checked ? 1 : 0;
      if (!state.connected || (name === "silence" && next && !confirm("Wyłączyć Wi-Fi do restartu routera? Połączenie zostanie przerwane."))) { el.checked=!el.checked; return; }
      el.disabled=true;
      try {
        const result=await apiRequest(endpoint,"POST",payload(next));
        if (result.code !== 0) throw Error(result.msg || result.code);
        $id(`wifi-adv-${name}-lbl`).textContent=next ? "Włączone" : "Wyłączone";
      } catch(e) { el.checked=!el.checked; alert("Nie udało się potwierdzić zmiany: " + e.message); }
      finally { el.disabled=false; }
    });
  }
  const roam=$id("wifi-adv-roam"), box=$id("wifi-roam-box"); roam.disabled=true;
  roam.addEventListener("change", async () => {
    if (!state.connected) { roam.checked=!roam.checked; return; }
    if (roam.checked) { box.classList.remove("hidden"); return; }
    try {
      const result=await apiRequest("xqnetwork/set_aimesh_config","POST",{manual_roaming_setting:"0"});
      if (result.code !== 0) throw Error(result.msg || result.code);
      box.classList.add("hidden");
    } catch(e) { roam.checked=true; alert("Nie udało się wyłączyć progów: " + e.message); }
  });
  $id("btn-save-roam").addEventListener("click", async () => {
    const r1=$id("wifi-roam-2g").value.trim(), r2=$id("wifi-roam-5g").value.trim();
    if (!state.connected || !viewLoaded.has("wifi") || !/^-[0-9]+$/.test(r1) || !/^-[0-9]+$/.test(r2)) return alert("Najpierw odczytaj ustawienia i podaj progi sygnału.");
    try {
      const result=await apiRequest("xqnetwork/set_aimesh_config","POST",{manual_roaming_setting:"1",roam_rssi_thr_2g:r1,roam_rssi_threshold1:r1,roam_rssi_thr_5g:r2,roam_rssi_threshold2:r2});
      alert(result.code === 0 ? "Router potwierdził ustawienia roamingu." : "Błąd routera: " + (result.msg || result.code));
    } catch(e) { alert("Nie udało się zapisać progów roamingu."); }
  });
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
    const ssid = document.getElementById("wifi-2g-ssid")?.value || "";
    const pwd = document.getElementById("wifi-2g-pwd")?.value || "";
    const enc = document.getElementById("wifi-2g-enc")?.value || "WPA2/WPA3";

    document.getElementById("wcard-type-badge").textContent = isSmart 
      ? "★ Domowa Sieć Wi-Fi (Smart Connect)" 
      : "★ Domowa Sieć Wi-Fi (Pasmo 2.4 GHz & 5 GHz)";
    document.getElementById("wcard-ssid-val").textContent = ssid;
    document.getElementById("wcard-enc-val").textContent = enc;
    document.getElementById("wcard-pwd-val").textContent = pwd || "(Brak hasła)";

    const qrBox = document.getElementById("wcard-qr-code");
    if (qrBox) qrBox.textContent = "Kod QR jest niedostępny w tej wersji.";

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
      success = await loginWithPassword(pwd);
      if (window.AndroidRouter) {
        if (success && document.getElementById("login-remember-pwd").checked) {
          if (!window.AndroidRouter.savePassword(state.ip, pwd)) alert("Zalogowano, ale nie udało się bezpiecznie zapamiętać hasła.");
        } else if (!document.getElementById("login-remember-pwd").checked) window.AndroidRouter.forgetPassword();
      }
    } else {
      const stokVal = document.getElementById("login-stok-input").value.trim();
      success = await loginWithStok(stokVal);
    }

    btnSubmit.disabled = false;
    btnSubmit.textContent = state.lang === "en" ? "Connect and log in" : "Połącz i Zaloguj";

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
  const saved = window.AndroidRouter ? window.AndroidRouter.readPassword(state.ip) : "";
  document.getElementById("login-pwd-input").value = saved;
  document.getElementById("login-remember-pwd").checked = Boolean(saved);
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
    if (!state.connected || !viewLoaded.has("reboot")) return alert("Najpierw odczytaj stan diod.");
    const stateVal = ledSw.checked ? "1" : "0";
    try {
      const res = await apiRequest("misystem/led", "POST", { state: stateVal });
      alert(res.code === 0 ? t("msg_save_success") : "Błąd routera: " + (res.msg || res.code));
    } catch (e) { alert("Nie udało się zapisać stanu diod."); }
  });

  // Reboot
  document.getElementById("btn-reboot-router")?.addEventListener("click", async () => {
    if (confirm(t("msg_confirm_reboot"))) {
      try {
        const res = await apiRequest("xqsystem/reboot");
        if (res.code !== 0) { alert("Błąd routera: " + (res.msg || res.code)); return; }
        disconnect();
        alert("Polecenie restartu wysłane. Router uruchamia się ponownie.");
      } catch (e) { alert("Nie udało się potwierdzić polecenia restartu."); }
    }
  });

  // Optymalizacja Wi-Fi
  document.getElementById("btn-wifi-opt")?.addEventListener("click", async () => {
    const btn = document.getElementById("btn-wifi-opt");
    btn.disabled = true;
    btn.textContent = "Skanowanie pasm...";
    try {
      const res = await apiRequest("xqnetwork/wifi_channel_optimize");
      alert(res.code === 0 ? t("msg_opt_complete") : "Błąd routera: " + (res.msg || res.code));
    } catch (e) {
      alert("Nie udało się potwierdzić optymalizacji Wi-Fi.");
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

    saveTextToDevice(`miwifi_raport_${fileStamp()}.md`, "text/markdown", md);
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

function natProto(value) { return ({1:"TCP",2:"UDP",3:"TCP/UDP"})[Number(value)] || String(value || "?"); }
function natPayload(rule, isRange) {
  const src=rule.srcport, proto=Number(rule.proto);
  return isRange ? {name:rule.name || "",ip:rule.destip || "",fport:src?.f,tport:src?.t,proto} :
    {name:rule.name || "",ip:rule.destip || "",sport:src,dport:rule.destport,proto};
}
async function natRequest(endpoint, payload) {
  const result=await apiRequest(endpoint,"POST",payload);
  if (result.code !== 0) throw Error(result.msg || `kod ${result.code}`);
  return result;
}
async function reloadNat() { viewLoaded.delete("nat"); await loadViewData("nat"); }
function renderNat() {
  const snapshot=state.natSnapshot;
  if (!snapshot) return;
  for (const type of ["single","range"]) {
    const target=$id(`nat-${type}-list`), rules=snapshot[type]; target.replaceChildren();
    if (rules === null) { target.textContent=state.lang === "en" ? "Could not load forwarding rules." : "Nie udało się odczytać przekierowań."; continue; }
    if (!rules.length) { target.textContent=state.lang === "en" ? "No forwarding rules." : "Brak przekierowań."; continue; }
    rules.forEach(rule => {
      const row=document.createElement("div"); row.className="nat-rule";
      const label=document.createElement("span"); label.className="nat-rule-info";
      const port=type === "range" && typeof rule.srcport === "object" ? `${rule.srcport.f} - ${rule.srcport.t}` : String(rule.srcport ?? "");
      label.textContent=`${natProto(rule.proto)}  ${rule.name || ""}  ${port} → ${rule.destip || ""}${type === "single" ? `:${rule.destport ?? ""}` : ""}`;
      const edit=document.createElement("button"); edit.className="btn-secondary btn-sm"; edit.textContent=state.lang === "en" ? "Edit" : "Edytuj"; edit.onclick=()=>openNatEditor(type,rule);
      const del=document.createElement("button"); del.className="btn-danger btn-sm"; del.textContent=state.lang === "en" ? "Delete" : "Usuń"; del.onclick=()=>deleteNat(type,rule);
      row.append(label,edit,del); target.append(row);
    });
  }
  const upnp=snapshot.upnp, toggle=$id("upnp-switch"), list=$id("upnp-list"); list.replaceChildren();
  toggle.disabled=!(upnp && (upnp.code === undefined || Number(upnp.code) === 0) && upnp.status !== undefined && upnp.status !== null && (Number(upnp.status) === 0 || Number(upnp.status) === 1));
  const stateText=$id("upnp-state-text");
  if (!toggle.disabled) {
    toggle.checked=Number(upnp.status) === 1;
    stateText.textContent=state.lang === "en" ? (toggle.checked ? "UPnP enabled" : "UPnP disabled") : (toggle.checked ? "UPnP włączone" : "UPnP wyłączone");
  } else {
    toggle.checked=false;
    stateText.textContent=state.lang === "en" ? "UPnP state unavailable" : "Stan UPnP nieodczytany";
  }
  if (!upnp || (upnp.code !== undefined && Number(upnp.code) !== 0) || !Array.isArray(upnp.list)) { list.textContent=state.lang === "en" ? "The router did not provide UPnP mappings." : "Router nie udostępnił listy UPnP."; return; }
  if (!upnp.list.length) { list.textContent=state.lang === "en" ? "No active UPnP mappings." : "Brak aktywnych przekierowań UPnP."; return; }
  upnp.list.forEach(rule => {
    const row=document.createElement("div"); row.className="nat-rule";
    row.textContent=`${rule.desc || rule.name || "UPnP"}: ${rule.ip || rule.destip || ""}  ${rule.ext_port || rule.srcport || ""}`;
    list.append(row);
  });
}
async function deleteNat(type, rule) {
  if (!state.connected || !viewLoaded.has("nat") || !confirm("Usunąć to przekierowanie?")) return;
  const port=type === "range" ? rule.srcport?.f : rule.srcport;
  if (!Number.isInteger(Number(port)) || !Number.isInteger(Number(rule.proto))) return alert("Router nie podał danych potrzebnych do usunięcia.");
  try {
    await natRequest("xqsystem/delete_redirect",{port,proto:rule.proto});
    await natRequest("xqsystem/redirect_apply",{});
    await reloadNat(); alert("Usunięto przekierowanie.");
  } catch(e) { await reloadNat(); alert("Nie udało się potwierdzić usunięcia: " + e.message); }
}
function openNatEditor(type, rule = null) {
  if (!state.connected || !viewLoaded.has("nat") || !Array.isArray(state.natSnapshot?.[type])) return alert("Najpierw odczytaj wybrane reguły NAT.");
  const range=type === "range", original=rule ? natPayload(rule,range) : null;
  const modal=document.createElement("dialog"); modal.className="nat-dialog";
  modal.innerHTML=`<form method="dialog"><h3></h3><label>Nazwa <input name="name" required></label><label>Protokół <select name="proto"><option value="1">TCP</option><option value="2">UDP</option><option value="3">TCP/UDP</option></select></label><label>Port zewnętrzny <input name="first" type="number" min="1" max="65535" required></label><label class="nat-end-label"></label><label>Adres IP urządzenia <input name="ip" required></label><div class="nat-dialog-actions"><button type="button" class="btn-secondary nat-cancel">Anuluj</button><button type="submit" class="btn-primary">Zapisz</button></div></form>`;
  modal.querySelector("h3").textContent=rule ? "Edytuj przekierowanie" : "Dodaj zakres portów";
  const endLabel=modal.querySelector(".nat-end-label"); endLabel.append(document.createTextNode(range ? "Koniec zakresu " : "Port wewnętrzny "));
  const end=document.createElement("input"); end.name="last"; end.type="number"; end.min="1"; end.max="65535"; end.required=true; endLabel.append(end);
  document.body.append(modal); if (state.lang === "en") applyStaticTranslation(); const form=modal.querySelector("form");
  if (original) { form.elements.name.value=original.name; form.elements.ip.value=original.ip; form.elements.proto.value=String(original.proto); form.elements.first.value=range ? original.fport : original.sport; form.elements.last.value=range ? original.tport : original.dport; }
  const close=()=>{modal.close?.();modal.remove();}; modal.querySelector(".nat-cancel").onclick=close;
  modal.addEventListener("cancel",()=>modal.remove());
  form.addEventListener("submit", async event => {
    event.preventDefault();
    const name=form.elements.name.value.trim(),ip=form.elements.ip.value.trim(),first=Number(form.elements.first.value),last=Number(form.elements.last.value),proto=Number(form.elements.proto.value);
    if (!name || !validIPv4(ip) || !Number.isInteger(first) || first<1 || first>65535 || !Number.isInteger(last) || last<1 || last>65535 || (range && last<first)) return alert("Uzupełnij poprawnie nazwę, adres IP i porty.");
    if (!confirm("Zapisać przekierowanie na routerze?")) return;
    const payload=range ? {name,ip,fport:first,tport:last,proto} : {name,ip,sport:first,dport:last,proto};
    const addEndpoint=range ? "xqsystem/add_range_redirect" : "xqsystem/add_redirect";
    let removed=false;
    try {
      if (original) { await natRequest("xqsystem/delete_redirect",{port:range ? original.fport : original.sport,proto:original.proto}); removed=true; }
      try { await natRequest(addEndpoint,payload); }
      catch(e) {
        if (removed) { try { await natRequest(addEndpoint,original); } catch(_) { throw Error("Nowa reguła została odrzucona, a przywrócenie poprzedniej nie powiodło się. Sprawdź reguły routera."); } }
        throw e;
      }
      await natRequest("xqsystem/redirect_apply",{}); close(); await reloadNat(); alert("Router potwierdził zapis przekierowania.");
    } catch(e) { try { if (removed) await natRequest("xqsystem/redirect_apply",{}); } catch(_) {} await reloadNat(); alert("Nie udało się potwierdzić zmiany: " + e.message); }
  });
  if (modal.showModal) modal.showModal(); else modal.setAttribute("open","");
}
function setupNatControls() {
  $id("btn-add-range").addEventListener("click",()=>openNatEditor("range"));
  $id("upnp-switch").addEventListener("change",async event => {
    const toggle=event.target,on=toggle.checked ? 1 : 0;
    if (!state.connected || !viewLoaded.has("nat") || !confirm("Zmienić ustawienie UPnP?")) {toggle.checked=!toggle.checked;return;}
    toggle.disabled=true;
    try { const res=await apiRequest(`xqsystem/upnp_switch?switch=${on}`); if(res.code!==0) throw Error(res.msg || res.code); await reloadNat(); }
    catch(e) {toggle.checked=!toggle.checked;toggle.disabled=false;alert("Nie udało się zmienić UPnP: " + e.message);}
  });
}

function saveTextToDevice(name, mime, text) {
  if (window.AndroidRouter?.saveTextFile) { window.AndroidRouter.saveTextFile(name,mime,text); return; }
  const blob=new Blob([text],{type:mime}), url=URL.createObjectURL(blob), a=document.createElement("a");
  a.href=url; a.download=name; a.click(); setTimeout(()=>URL.revokeObjectURL(url),1000);
}
window.xrmSaveComplete = ok => alert(ok ? "Plik został zapisany." : "Nie udało się zapisać pliku.");
function fileStamp() { return new Date().toISOString().replace(/[:.]/g,"-").replace("T","_").slice(0,19); }
async function buildSnapshot() {
  if (!state.connected) throw Error("Najpierw połącz się z routerem.");
  const endpoints={status:"misystem/status",wan_info:"xqnetwork/wan_info",lan_info:"xqnetwork/lan_info",lan_dhcp:"xqnetwork/lan_dhcp",wifi_detail:"xqnetwork/wifi_detail_all",device_list:"misystem/devicelist",mac_bind:"xqnetwork/macbind_info",dmz:"xqsystem/dmz",upnp:"xqsystem/upnp",qos:"misystem/qos_info",topo_graph:"misystem/topo_graph",led_status:"misystem/led",ps_map:"misystem/get_ps_map",router_name:"misystem/router_name",reboot_task:"xqsystem/reboot_task",twt:"xqnetwork/get_twt",miotrelay:"xqnetwork/get_miotrelay_switch",wifi_silence:"xqnetwork/get_wifi_silence",aimesh:"xqnetwork/get_aimesh_config",ddns:"xqnetwork/ddns",vpn:"xqsystem/vpn",vpn_status:"xqsystem/vpn_status",country_code:"xqsystem/country_code",sys_time:"misystem/sys_time"};
  const snap={fetch_date:new Date().toISOString(),router_ip:state.ip,init_info:state.initInfo,errors:[]};
  for (const [key,endpoint] of Object.entries(endpoints)) {
    try { const res=await apiRequest(endpoint); if (!res || (res.code !== undefined && Number(res.code) !== 0)) throw Error(); snap[key]=res; }
    catch(e) {snap.errors.push(key);}
  }
  snap.port_forward={single:[],range:[]};
  // Match the Windows snapshot layout: DMZ and UPnP belong to the NAT section.
  if (snap.dmz) snap.port_forward.dmz=snap.dmz;
  if (snap.upnp) snap.port_forward.upnp=snap.upnp;
  delete snap.dmz; delete snap.upnp;
  for(const [key,ftype] of [["single",1],["range",2]]) {
    try { const res=await apiRequest(`xqsystem/portforward?ftype=${ftype}`); if(!res || (res.code !== undefined && Number(res.code)!==0) || !Array.isArray(res.list)) throw Error(); snap.port_forward[key]=res.list; }
    catch(e) {snap.errors.push(`port_forward_${key}`);}
  }
  snap.ps_services={};
  for(const service of ["multiwan","lag","iptv","game"]) {
    try {const res=await apiRequest(`misystem/get_ps_service?service=${service}`); if(!res || (res.code!==undefined && Number(res.code)!==0) || !res[service] || res[service].enable===undefined) throw Error(); snap.ps_services[service]=res;}
    catch(e) {snap.errors.push(`ps_${service}`);}
  }
  return snap;
}
async function shaPasswordChange(oldPassword,newPassword) {
  let id=state.deviceId || state.initInfo.id || state.initInfo.routerId;
  if (!id || String(id).includes("/")) {
    try { const html=await requestRaw("/cgi-bin/luci/web"); id=html.match(/deviceId\s*:\s*['"]([^'"]+)['"]/)?.[1]; } catch (_) {}
  }
  if (!id || String(id).includes("/")) id="00:00:00:00:00:00";
  const nonce=`0_${id}_${Math.floor(Date.now()/1000)}_${Math.floor(Math.random()*9000+1000)}`;
  const oldHash=await digest("SHA-256",oldPassword+PUBLIC_KEY);
  const oldPwd=await digest("SHA-256",nonce+oldHash);
  const iv=Uint8Array.from("64175472480004614961023454661220".match(/../g),h=>parseInt(h,16));
  async function encrypted(hashAlg) {
    const keyHex=(await digest(hashAlg,oldPassword+PUBLIC_KEY)).slice(0,32);
    const keyBytes=Uint8Array.from(keyHex.match(/../g),h=>parseInt(h,16));
    const key=await crypto.subtle.importKey("raw",keyBytes,{name:"AES-CBC"},false,["encrypt"]);
    const plain=new TextEncoder().encode(await digest(hashAlg,newPassword+PUBLIC_KEY));
    const encrypted=await crypto.subtle.encrypt({name:"AES-CBC",iv},key,plain);
    return btoa(String.fromCharCode(...new Uint8Array(encrypted)));
  }
  return {nonce,oldPwd,newPwd:await encrypted("SHA-1"),newPwd256:await encrypted("SHA-256")};
}
function passwordDialog() {
  if (!state.connected) return alert("Najpierw połącz się z routerem.");
  const dialog=document.createElement("dialog");dialog.className="nat-dialog";
  dialog.innerHTML='<form method="dialog"><h3>Zmiana hasła administratora</h3><label>Obecne hasło<input name="old" type="password" required></label><label>Nowe hasło<input name="next" type="password" required minlength="8"></label><label>Powtórz nowe hasło<input name="repeat" type="password" required minlength="8"></label><div class="nat-dialog-actions"><button type="button" class="btn-secondary cancel">Anuluj</button><button class="btn-primary" type="submit">Zmień hasło</button></div></form>';
  document.body.append(dialog); if (state.lang === "en") applyStaticTranslation(); const form=dialog.querySelector("form"), close=()=>{dialog.close?.();dialog.remove();};
  dialog.querySelector(".cancel").onclick=close;dialog.addEventListener("cancel",()=>dialog.remove());
  form.onsubmit=async event=>{event.preventDefault();const old=form.elements.old.value, next=form.elements.next.value;
    if(next.length<8 || next!==form.elements.repeat.value || old===next) return alert("Hasła muszą być zgodne, nowe musi mieć co najmniej 8 znaków i różnić się od obecnego.");
    if(!confirm("Zmienić hasło administratora routera?")) return;
    try {const payload=await shaPasswordChange(old,next);const res=await apiRequest("xqsystem/set_name_password","POST",payload);if(res.code!==0) throw Error(res.msg || res.code); window.AndroidRouter?.forgetPassword(); close(); alert("Router potwierdził zmianę hasła.");}
    catch(e){alert("Nie udało się potwierdzić zmiany hasła: "+e.message);}
  };
  if(dialog.showModal)dialog.showModal();else dialog.setAttribute("open","");
}
// Buduje select stref czasowych - wywolywane raz przy starcie
function buildTzSelect(selectId) {
  const sel = $id(selectId);
  if (!sel || sel.dataset.built) return;
  sel.dataset.built = "1";
  const deviceTz = Intl.DateTimeFormat().resolvedOptions().timeZone;
  TZ_DISPLAY_LIST.forEach(item => {
    const opt = document.createElement("option");
    opt.value = item.iana;
    opt.textContent = item.label;
    if (item.iana === deviceTz) opt.selected = true;
    sel.appendChild(opt);
  });
}

// Buduje select kodow regionow
function buildRegionSelect(selectId, currentCode) {
  const sel = $id(selectId);
  if (!sel) return;
  sel.innerHTML = "";
  REGION_LIST.forEach(item => {
    const opt = document.createElement("option");
    opt.value = item.code;
    opt.textContent = item.label;
    if (currentCode && item.code === currentCode.toUpperCase()) opt.selected = true;
    sel.appendChild(opt);
  });
}

// Odczytuje aktualny region z routera i aktualizuje select
async function loadRegionFromRouter(selectId) {
  if (!state.connected) return;
  try {
    const r = await apiRequest("xqsystem/country_code");
    if (r.code === 0 && r.country) buildRegionSelect(selectId, r.country);
  } catch (_) {}
}

function setupSystemEnhancements() {
  $id("system-change-password").onclick=passwordDialog;
  for(const [id,on] of [["btn-nfc-enable",1],["btn-nfc-disable",0]]) $id(id).onclick=async()=>{
    if(!state.connected || !confirm(`${on ? "Włączyć" : "Wyłączyć"} NFC na routerze?`)) return;
    try {const r=await apiRequest("xqnetwork/set_nfc_status","POST",{status:on});if(r.code!==0)throw Error(r.msg||r.code);alert("Router potwierdził zmianę NFC.");}catch(e){alert("Nie udało się potwierdzić zmiany NFC: "+e.message);}
  };
  // Buduj selektory strefy i regionu po zaladowaniu DOM
  buildTzSelect("system-tz-select");
  buildTzSelect("wiz-tz-select");
  buildRegionSelect("system-region-select", "PL");
  buildRegionSelect("wiz-region-select", "PL");

  // Synchronizacja czasu z urzadzeniem + strefa z selecta
  $id("btn-sync-time").onclick=async()=>{
    if(!state.connected) return;const d=new Date(),pad=n=>String(n).padStart(2,"0");
    const time=`${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
    const selEl = $id("system-tz-select");
    const tz = selEl ? selEl.value : Intl.DateTimeFormat().resolvedOptions().timeZone;
    const posix = TZ_POSIX_MAP[tz] || "";
    if(!confirm(`Ustawić czas routera na ${time}\nStrefa: ${tz}${posix ? " (" + posix + ")" : ""}?`))return;
    const query=new URLSearchParams({time});
    if(posix) query.set("timezone", posix);
    try {const r=await apiRequest(`misystem/set_sys_time?${query}`);if(r.code!==0)throw Error(r.msg||r.code);alert("Router potwierdził ustawienie czasu.");}catch(e){alert("Nie udało się ustawić czasu: "+e.message);}
  };
  // Zapisz strefę czasową (bez synchronizacji czasu)
  const btnSaveTz = $id("btn-save-tz");
  if (btnSaveTz) btnSaveTz.onclick = async () => {
    if (!state.connected) return alert("Najpierw połącz się z routerem.");
    const selEl = $id("system-tz-select");
    const tz = selEl ? selEl.value : "";
    const posix = TZ_POSIX_MAP[tz] || "";
    if (!posix) return alert("Nieznana strefa czasowa. Wybierz strefę z listy.");
    if (!confirm(`Ustawić strefę czasową routera na: ${tz} (${posix})?`)) return;
    const d = new Date(), pad = n => String(n).padStart(2, "0");
    const time = `${d.getFullYear()}-${pad(d.getMonth()+1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
    try {
      const query = new URLSearchParams({time, timezone: posix});
      const r = await apiRequest(`misystem/set_sys_time?${query}`);
      if (r.code !== 0) throw Error(r.msg || r.code);
      alert("Router potwierdził zmianę strefy czasowej.");
    } catch(e) { alert("Nie udało się zmienić strefy: " + e.message); }
  };
  // Odczyt aktualnego regionu z routera
  const btnReadRegion = $id("btn-read-region");
  if (btnReadRegion) btnReadRegion.onclick = async () => {
    if (!state.connected) return alert("Najpierw połącz się z routerem.");
    await loadRegionFromRouter("system-region-select");
    alert("Odczytano aktualny region routera.");
  };
  // Zapis regionu (country code / RegDomain)
  const btnSaveRegion = $id("btn-save-region");
  if (btnSaveRegion) btnSaveRegion.onclick = async () => {
    if (!state.connected) return alert("Najpierw połącz się z routerem.");
    const sel = $id("system-region-select");
    const code = sel ? sel.value : "";
    if (!code) return alert("Wybierz kod regionu z listy.");
    const isCN = code === "CN";
    const warn = isCN
      ? "\n\nUWAGA: Kod CN (Chiny) odblokowuje pelna moc TX radia. Upewnij sie, ze jest to zgodne z lokalnym prawem."
      : (code === "US" || code === "CA" ? "\n\nKod FCC (USA/CA) moze odblokowac wyzsze pasma 5 GHz i wyzsza moc TX niz dozwolona w UE." : "");
    if (!confirm(`Ustawić region routera na: ${code}?${warn}`)) return;
    try {
      const r = await apiRequest("xqsystem/set_country_code", "POST", {country: code});
      if (r.code !== 0) throw Error(r.msg || r.code);
      alert(`Router potwierdził zmianę regionu na ${code}. Efekt moze wymagac restartu routera.`);
    } catch(e) { alert("Nie udało się zmienić regionu: " + e.message); }
  };
  $id("btn-check-firmware").onclick=async()=>{if(!state.connected)return;try{const r=await apiRequest("xqsystem/check_rom_update");if(r.code!==0)throw Error(r.msg||r.code);alert(Number(r.needUpdate)===1 ? "Router zgłasza dostępną aktualizację firmware." : "Router nie zgłasza dostępnej aktualizacji firmware.");}catch(e){alert("Nie udało się sprawdzić aktualizacji: "+e.message);}};
  $id("btn-factory-reset").onclick=async()=>{if(!state.connected || !confirm("Przywrócić ustawienia fabryczne? Zostanie usunięta konfiguracja routera."))return;if(!confirm("Potwierdź ponownie przywrócenie ustawień fabrycznych."))return;try{const r=await apiRequest("xqsystem/reset");if(r.code!==0)throw Error(r.msg||r.code);disconnect();alert("Router potwierdził polecenie przywrócenia.");}catch(e){alert("Nie udało się potwierdzić operacji: "+e.message);}};
  $id("btn-save-snapshot").onclick=async()=>{
    if(!state.connected || !confirm("Utworzyć kopię? Plik może zawierać hasła i inne wrażliwe dane konfiguracji."))return;
    const button=$id("btn-save-snapshot");button.disabled=true;
    try {const snap=await buildSnapshot();if(snap.errors.length)alert(`Nie udało się odczytać wszystkich sekcji: ${snap.errors.join(", ")}. Kopia będzie niepełna.`);saveTextToDevice(`miwifi_backup_${fileStamp()}.json`,"application/json",JSON.stringify(snap,null,2));}catch(e){alert("Nie udało się utworzyć kopii: "+e.message);}finally{button.disabled=false;}
  };
  let loadedBackup=null;
  $id("backup-file-input").onchange=async event=>{
    const file=event.target.files?.[0];if(!file)return;
    loadedBackup=null;$id("btn-apply-json").disabled=true;
    try {
      if(file.size>4_000_000)throw Error(state.lang === "en" ? "File is too large." : "Plik jest za duży.");
      const parsed=JSON.parse(await file.text());
      if(!parsed || Array.isArray(parsed) || typeof parsed!=="object" || !["mac_bind","port_forward","dmz","upnp","qos","ps_services","wifi_detail"].some(key=>parsed[key])) throw Error(state.lang === "en" ? "No supported backup sections found." : "Nie znaleziono obsługiwanych sekcji kopii.");
      // Windows stores these sections inside port_forward; newer Android copies use top-level fields.
      if (parsed.dmz == null && parsed.port_forward?.dmz) parsed.dmz=parsed.port_forward.dmz;
      if (parsed.upnp == null && parsed.port_forward?.upnp) parsed.upnp=parsed.port_forward.upnp;
      loadedBackup=parsed;$id("btn-apply-json").disabled=false;$id("backup-file-status").dataset.filename=file.name;
      $id("backup-file-status").textContent=(state.lang === "en" ? "Loaded: " : "Wczytano: ")+file.name;
    } catch(e) {
      delete $id("backup-file-status").dataset.filename;$id("backup-file-status").textContent=state.lang === "en" ? "No JSON backup loaded." : "Nie wczytano kopii JSON.";
      alert((state.lang === "en" ? "Unable to load backup: " : "Nie udało się wczytać kopii: ")+e.message);
    }
    event.target.value="";
  };
  $id("btn-apply-json").onclick=()=>{if(loadedBackup)openSelectiveRestore(loadedBackup);};
  $id("btn-official-backup").onclick=async()=>{if(!state.connected)return;try{const q=new URLSearchParams({keys:"mi_wifi_info,mi_network_info,mi_lan_info,mi_basic_info"});const r=await apiRequest(`misystem/c_backup?${q}`);if(r.code!==0 || !/^[A-Za-z0-9._-]+$/.test(r.file || ""))throw Error(r.msg || "Router nie podał nazwy kopii.");if(!window.AndroidRouter?.saveRouterFile)throw Error("Pobieranie pliku wymaga aplikacji Android.");window.AndroidRouter.saveRouterFile(state.ip,`/cgi-bin/luci/;stok=${state.stok}/api/misystem/c_download/${r.file}`,`xiaomi_backup_${fileStamp()}.tar.gz`);}catch(e){alert("Nie udało się przygotować kopii: "+e.message);}};
}

function openSelectiveRestore(snapshot) {
  if (!state.connected) return alert("Najpierw połącz się z routerem.");
  const errors=Array.isArray(snapshot.errors) ? snapshot.errors : [];
  const validSwitch=value=>value===0 || value===1 || value==="0" || value==="1";
  const wifi=snapshot.wifi_detail, radios=wifi?.info;
  const validResponse=r=>r && typeof r==="object" && !r.error && (r.code===undefined || Number(r.code)===0);
  const possible={wan:false,lan:false,wifi:validResponse(wifi) && Array.isArray(radios) && radios.length>=2 && wifi.bsd!==undefined && radios.slice(0,2).every(r=>r && r.ssid && r.encryption && (r.encryption==="none" || r.password)) && !errors.includes("wifi_detail"),mac_bind:validResponse(snapshot.mac_bind) && Array.isArray(snapshot.mac_bind?.list) && !errors.includes("mac_bind"),port_forward:validResponse(snapshot.port_forward) && Array.isArray(snapshot.port_forward?.single) && Array.isArray(snapshot.port_forward?.range) && !errors.some(x=>String(x).startsWith("port_forward_")),dmz:validResponse(snapshot.dmz) && validSwitch(snapshot.dmz?.status) && (Number(snapshot.dmz.status)===0 || validIPv4(String(snapshot.dmz.ip || snapshot.dmz.lanip || ""))) && !errors.includes("dmz"),upnp:validResponse(snapshot.upnp) && validSwitch(snapshot.upnp?.status) && !errors.includes("upnp"),ps_services:["multiwan","lag","iptv","game"].every(name=>validResponse(snapshot.ps_services?.[name]) && snapshot.ps_services?.[name]?.[name]?.enable!==undefined) && !errors.some(x=>String(x).startsWith("ps_")),qos:validResponse(snapshot.qos) && validSwitch(snapshot.qos?.status?.on) && !errors.includes("qos"),vpn:false,password:false};
  const names={wan:"WAN",lan:"LAN i serwer DHCP",wifi:"Wi-Fi",mac_bind:"Rezerwacje DHCP",port_forward:"Przekierowania portów",dmz:"DMZ",upnp:"UPnP",ps_services:"Funkcje portów",qos:"QoS",vpn:"VPN",password:"Hasło administratora"};
  const dialog=document.createElement("dialog");dialog.className="nat-dialog";
  const form=document.createElement("form");form.method="dialog";
  const heading=document.createElement("h3");heading.textContent="Przywracanie wybranych sekcji";form.append(heading);
  const selectAll=document.createElement("label"), all=document.createElement("input"), allName=document.createElement("span");all.type="checkbox";all.name="select_all";all.disabled=!Object.values(possible).some(Boolean);allName.textContent="Zaznacz wszystkie dostępne sekcje";selectAll.className="restore-option";selectAll.append(all,allName);form.append(selectAll);
  for(const key of Object.keys(possible)) {const label=document.createElement("label"), input=document.createElement("input"), name=document.createElement("span");label.className="restore-option";input.type="checkbox";input.name=key;input.disabled=!possible[key];name.textContent=names[key];label.append(input,name);if(!possible[key]){const unavailable=document.createElement("span");unavailable.textContent=["wan","lan","vpn","password"].includes(key) ? " (jeszcze nieobsługiwane)" : " (brak pełnych danych)";label.append(unavailable);}form.append(label);}
  all.onchange=()=>{for(const key of Object.keys(possible))if(possible[key])form.elements[key].checked=all.checked;};
  form.addEventListener("change",event=>{if(event.target!==all)all.checked=Object.keys(possible).filter(key=>possible[key]).every(key=>form.elements[key].checked);});
  const warn=document.createElement("p");warn.textContent="Zmiany są wykonywane kolejno. Wi-Fi zostanie przywrócone jako ostatnie i może przerwać połączenie.";form.append(warn);
  const limits=document.createElement("p");limits.textContent="Rezerwacje i przekierowania są dodawane. Istniejące wpisy nie są usuwane. UPnP przywraca stan usługi, nie jej tymczasowe mapowania.";form.append(limits);
  const actions=document.createElement("div");actions.className="nat-dialog-actions";
  const cancel=document.createElement("button");cancel.type="button";cancel.className="btn-secondary";cancel.textContent="Anuluj";
  const save=document.createElement("button");save.type="submit";save.className="btn-primary";save.textContent="Przywróć";actions.append(cancel,save);form.append(actions);dialog.append(form);document.body.append(dialog); if (state.lang === "en") applyStaticTranslation();
  const close=()=>{dialog.close?.();dialog.remove();};cancel.onclick=close;dialog.addEventListener("cancel",()=>dialog.remove());
  form.onsubmit=async event=>{event.preventDefault();const selected=Object.keys(possible).filter(key=>form.elements[key].checked);
    if(!selected.length)return alert("Wybierz co najmniej jedną sekcję.");
    if(!confirm("Przywrócić wybrane sekcje? Operacja może zmienić dostęp do sieci."))return;
    save.disabled=true;const done=[];
    const checked=async(endpoint,method="GET",payload=null)=>{const res=await apiRequest(endpoint,method,payload);if(res.code!==0)throw Error(res.msg||`kod ${res.code}`);return res;};
    try {
      if(selected.includes("dmz") && Number(snapshot.dmz.status)===1) {
        const current=await Promise.all([apiRequest("xqsystem/portforward?ftype=1"),apiRequest("xqsystem/portforward?ftype=2")]);
        if(current.some(r=>!r || (r.code!==undefined && Number(r.code)!==0) || !Array.isArray(r.list)))throw Error("Nie udało się sprawdzić istniejących przekierowań przed włączeniem DMZ.");
        if(current.some(r=>r.list.length) || (selected.includes("port_forward") && (snapshot.port_forward.single.length || snapshot.port_forward.range.length)))throw Error("Nie można włączyć DMZ, gdy istnieją lub mają zostać dodane przekierowania.");
      }
      if(selected.includes("mac_bind")) {for(const item of snapshot.mac_bind.list){if(!item.mac || !validIPv4(String(item.ip)))throw Error("Niepoprawna rezerwacja DHCP w kopii.");await checked("xqnetwork/mac_bind","POST",{data:JSON.stringify([{mac:item.mac,ip:item.ip,name:item.name||"Host"}])});}done.push("DHCP");}
      if(selected.includes("port_forward")) {
        for(const rule of snapshot.port_forward.single){const p=natPayload(rule,false);if(!validIPv4(String(p.ip)) || !p.sport || !p.dport)throw Error("Niepoprawna reguła portu w kopii.");await checked("xqsystem/add_redirect","POST",p);}
        for(const rule of snapshot.port_forward.range){const p=natPayload(rule,true);if(!validIPv4(String(p.ip)) || !p.fport || !p.tport)throw Error("Niepoprawny zakres portów w kopii.");await checked("xqsystem/add_range_redirect","POST",p);}
        await checked("xqsystem/redirect_apply","POST",{});done.push("NAT");
      }
      if(selected.includes("dmz")) {const d=snapshot.dmz;if(Number(d.status)===1)await checked("xqsystem/set_dmz","POST",{ip:d.ip || d.lanip});else await checked("xqsystem/dmz_off");done.push("DMZ");}
      if(selected.includes("upnp")) {await checked(`xqsystem/upnp_switch?switch=${Number(snapshot.upnp.status)}`);done.push("UPnP");}
      if(selected.includes("ps_services")) {
        for(const name of ["multiwan","lag","iptv","game"]) {const info=snapshot.ps_services[name]?.[name];if(!info || info.enable === undefined)throw Error(`Brak ustawień portów: ${name}`);
          const payload={service:name,enable:info.enable};
          if(name==="multiwan"){payload.port=(info.port_map||[]).find(x=>x.name==="WAN2")?.port ?? "";payload.mode=info.policy?.mode ?? 0;}
          else {payload.ports=info.ports ?? "";if(name==="lag")payload.mode=info.mode ?? 2;if(name==="iptv"){payload.vid=info.vid ?? -1;payload.profile=info.profile ?? 0;payload.priority=info.priority ?? -1;}}
          if(Number(payload.enable)===1 && !(payload.port||payload.ports))throw Error(`Brak portu usługi ${name}.`);
          await checked("misystem/set_ps_service","POST",payload);
        }done.push("porty");
      }
      if(selected.includes("qos")) {const q=snapshot.qos;if(q.status.on!==undefined)await checked(`misystem/qos_switch?on=${Number(q.status.on)}`);if(q.status.mode!==undefined)await checked(`misystem/qos_mode?mode=${Number(q.status.mode)}`);if(q.band?.upload!==undefined&&q.band?.download!==undefined)await checked(`misystem/set_band?upload=${Number(q.band.upload)}&download=${Number(q.band.download)}`);done.push("QoS");}
      if(selected.includes("wifi")) {const w=snapshot.wifi_detail.info, a=w[0], b=w[1], bsd=snapshot.wifi_detail.bsd;
        if(bsd===undefined || !a.ssid || !b.ssid || !a.encryption || !b.encryption || (a.encryption!=="none"&&!a.password) || (b.encryption!=="none"&&!b.password))throw Error("Kopia nie zawiera pełnych danych obu pasm Wi-Fi.");
        const x={bsd:String(bsd),isDFS:"0"};for(const [idx,radio] of [[1,a],[2,b]]){x[`on${idx}`]=String(radio.status ?? 1);x[`ssid${idx}`]=radio.ssid;x[`pwd${idx}`]=radio.password || "";x[`encryption${idx}`]=radio.encryption;x[`channel${idx}`]=String(radio.channel ?? 0);x[`bandwidth${idx}`]=String(radio.bandwidth ?? 0);x[`hidden${idx}`]=String(radio.hidden ?? 0);x[`txpwr${idx}`]=radio.txpwr || "max";}
        Object.assign(x,{channel:x.channel1,bandwidth:x.bandwidth1,txpwr:x.txpwr1,channel50:x.channel2,bandwidth50:x.bandwidth2,txpwr50:x.txpwr2});
        await checked("xqnetwork/set_all_wifi","POST",x);done.push("Wi-Fi");
      }
      close();viewLoaded.clear();void refreshData();alert("Router potwierdził przywrócenie: "+done.join(", "));
    }catch(e){save.disabled=false;viewLoaded.clear();void refreshData();alert(`Operacja została przerwana. Potwierdzone sekcje: ${done.join(", ") || "brak"}. Powód: ${e.message}. Sprawdź stan routera.`);}
  };
  if(dialog.showModal)dialog.showModal();else dialog.setAttribute("open","");
}

async function serviceAction(endpoint,method="GET",payload=null,question="Wykonać operację?") {
  if (!state.connected || !viewLoaded.has("services")) return alert("Najpierw odczytaj ustawienia usług.");
  if (!confirm(question)) return;
  try {const res=await apiRequest(endpoint,method,payload);if(res.code!==0)throw Error(res.msg||res.code);viewLoaded.delete("services");await loadViewData("services");alert("Router potwierdził operację.");}
  catch(e){alert("Nie udało się potwierdzić operacji: "+e.message);}
}
function serviceButton(text,fn) {const b=document.createElement("button");b.className="btn-secondary btn-sm";b.textContent=text;b.onclick=fn;return b;}
function renderServices() {
  const data=state.serviceSnapshot || {};
  for(const kind of ["ddns","vpn"]) {
    const target=$id(`${kind}-list`),response=data[kind];target.replaceChildren();
    if(!response || response.code!==0 || !Array.isArray(response.list)) {target.textContent="Router nie udostępnił danych.";continue;}
    if(!response.list.length){target.textContent=kind==="vpn"?"Brak profili VPN.":"Brak usług DDNS.";continue;}
    response.list.forEach(item=>{
      const row=document.createElement("div");row.className="nat-rule";const label=document.createElement("span");label.className="nat-rule-info";
      label.textContent=kind==="ddns" ? `${item.service || "DDNS"}: ${item.domain || ""} (${Number(item.on)===1 ? "włączone" : "wyłączone"})` : `${item.proto || "VPN"}: ${item.server || ""}`;row.append(label);
      const id=String(item.id ?? "");
      if(/^\d+$/.test(id)) {
        if(kind==="ddns") {row.append(serviceButton(Number(item.on)===1?"Wyłącz":"Włącz",()=>serviceAction(`xqnetwork/ddns_switch?id=${id}&on=${Number(item.on)===1?0:1}`)),serviceButton("Odśwież",()=>serviceAction(`xqnetwork/ddns_reload?id=${id}`)),serviceButton("Usuń",()=>serviceAction(`xqnetwork/ddns_del?id=${id}`,"GET",null,"Usunąć usługę DDNS?")));}
        else row.append(serviceButton("Połącz",()=>serviceAction(`xqsystem/vpn_connect?id=${id}`)),serviceButton("Usuń",()=>serviceAction(`xqsystem/del_vpn?id=${id}`,"GET",null,"Usunąć profil VPN?")));
      }
      target.append(row);
    });
  }
  $id("vpn-status").textContent=data.status?.code===0 ? `Stan VPN: ${String(data.status.status ?? "--")}` : "Stan VPN niedostępny";
  const smart=data.smart, val=smart?.enable ?? smart?.status;
  $id("smartvpn-enabled").disabled=val===undefined || smart?.code!==0;
  $id("smartvpn-mode").disabled=$id("smartvpn-enabled").disabled; $id("smartvpn-save").disabled=$id("smartvpn-enabled").disabled;
  if(val!==undefined)$id("smartvpn-enabled").checked=Number(val)===1;
  if(smart?.mode!==undefined)$id("smartvpn-mode").value=String(smart.mode);
}
function setupServices() {
  $id("ddns-add").onclick=async()=>{
    const payload={service:$id("ddns-provider").value,domain:$id("ddns-domain").value.trim(),username:$id("ddns-user").value.trim(),password:$id("ddns-password").value};
    if(!payload.domain || !payload.username || !payload.password)return alert("Uzupełnij dane DDNS.");
    await serviceAction("xqnetwork/ddns_add","POST",payload,"Dodać usługę DDNS?");$id("ddns-password").value="";
  };
  $id("vpn-add").onclick=async()=>{
    const payload={proto:$id("vpn-proto").value,server:$id("vpn-server").value.trim(),username:$id("vpn-user").value.trim(),password:$id("vpn-password").value,auto:$id("vpn-auto").checked?1:0};
    if(!payload.server || !payload.username || !payload.password)return alert("Uzupełnij dane VPN.");
    await serviceAction("xqsystem/set_vpn","POST",payload,"Dodać profil VPN?");$id("vpn-password").value="";
  };
  $id("vpn-disconnect").onclick=()=>serviceAction("xqsystem/vpn_disconnect","GET",null,"Rozłączyć VPN?");
  $id("smartvpn-save").onclick=()=>serviceAction(`misystem/smartvpn_switch?enable=${$id("smartvpn-enabled").checked?1:0}&mode=${Number($id("smartvpn-mode").value)}`,"GET",null,"Zapisać Smart VPN?");
}

// Never keep legacy plain-text credentials or stale tokens in WebView storage.
localStorage.removeItem("xrm_saved_pwd");
localStorage.removeItem("xrm_stok");
document.addEventListener("DOMContentLoaded", () => {
  initStaticTranslation();
  setupUI();
  applyLayoutMode(state.layout);
  document.querySelectorAll("#lang-toggle button").forEach(btn=>btn.classList.toggle("active",btn.dataset.lang===state.lang));
  document.querySelectorAll("#layout-toggle button").forEach(btn=>btn.classList.toggle("active",btn.dataset.layout===state.layout));
  applyStaticTranslation(); setConnected(state.connected);
  if (window.AndroidRouter?.isPreview?.()) {
    const banner = document.createElement("div");
    banner.textContent = "WERSJA TESTOWA: podgląd i logowanie. Zmiana ustawień routera jest zablokowana.";
    banner.className = "wifi-banner-info";
    document.getElementById("main-content").prepend(banner);
  }
});
