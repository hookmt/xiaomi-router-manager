"""
SODOM: Wgrywanie regul Port Forwarding (NAT) do routera Xiaomi BE7000 przez API MiWiFi.
Zrodlo danych: przekierowania_portow.xlsx w tym samym folderze lub zdefiniowane reguly kanoniczne.
Wymaga wylacznie standardowej biblioteki Pythona (zipfile, xml, urllib).
"""
import zipfile
import xml.etree.ElementTree as ET
import urllib.request
import urllib.parse
import json
import sys
from pathlib import Path

def get_xlsx_path() -> Path:
    current_dir = Path(__file__).resolve().parent
    local_path = current_dir / "przekierowania_portow.xlsx"
    if local_path.is_file():
        return local_path
    candidates = [
        current_dir.parent.parent.parent / "SIEC" / "przekierowania_portow.xlsx",
        Path(r"N:\ChatGPT\HAOS\PLIKI_SYSTEMU\SIEC\przekierowania_portow.xlsx"),
        Path(r"S:\ChatGPT\HAOS\PLIKI_SYSTEMU\SIEC\przekierowania_portow.xlsx"),
        Path(r"\\HOOKMTSRV\AI\ChatGPT\HAOS\PLIKI_SYSTEMU\SIEC\przekierowania_portow.xlsx"),
    ]
    for c in candidates:
        if c.is_file():
            return c
    return None

def load_rules_from_xlsx(xlsx_path: Path):
    with zipfile.ZipFile(xlsx_path, 'r') as z:
        shared_strings = []
        if 'xl/sharedStrings.xml' in z.namelist():
            root = ET.fromstring(z.read('xl/sharedStrings.xml'))
            for si in root.findall('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}si'):
                text = ''.join(t.text for t in si.iter('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t') if t.text)
                shared_strings.append(text)

        sheet1 = ET.fromstring(z.read('xl/worksheets/sheet1.xml'))
        single_rules = []
        range_rules = []
        for row in sheet1.iter('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}row'):
            cells = {}
            for c in row.findall('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}c'):
                r_coord = c.attrib.get('r', '')
                col = ''.join(filter(str.isalpha, r_coord))
                t = c.attrib.get('t')
                v = c.find('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}v')
                val = ''
                if v is not None and v.text:
                    if t == 's':
                        val = shared_strings[int(v.text)]
                    else:
                        val = v.text
                elif t == 'inlineStr':
                    val = ''.join(it.text for it in c.iter('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t') if it.text)
                cells[col] = val.strip()

            rule_type = cells.get('A', '')
            name = cells.get('B', '')
            proto_str = cells.get('C', '').upper()
            proto = '1' if 'TCP' in proto_str and 'UDP' not in proto_str else ('2' if 'UDP' in proto_str and 'TCP' not in proto_str else '3')
            port_from = cells.get('D', '')
            port_to = cells.get('E', '')
            ip = cells.get('F', '')
            port_int = cells.get('G', '')

            if rule_type == 'Pojedynczy port' and ip and port_from:
                single_rules.append({
                    'name': name,
                    'proto': proto,
                    'sport': port_from,
                    'ip': ip,
                    'dport': port_int or port_from
                })
            elif rule_type == 'Zakres portów' and ip and port_from and port_to:
                range_rules.append({
                    'name': name,
                    'proto': proto,
                    'fport': port_from,
                    'tport': port_to,
                    'ip': ip
                })
        return single_rules, range_rules

def run():
    if len(sys.argv) < 2:
        print("Uzycie: python apply_portforward.py <stok>")
        sys.exit(1)

    stok = sys.argv[1].strip()
    base_url = f'http://192.168.31.1/cgi-bin/luci/;stok={stok}/api/xqsystem'

    xlsx_path = get_xlsx_path()
    if xlsx_path and xlsx_path.is_file():
        try:
            single_rules, range_rules = load_rules_from_xlsx(xlsx_path)
            print(f"Zaladowano {len(single_rules)} pojedynczych i {len(range_rules)} zakresowych regul z {xlsx_path.name}")
        except Exception as e:
            print(f"Blad czytania XLSX ({e}), uzywam regul kanonicznych...")
            single_rules = None
    else:
        single_rules = None

    if not single_rules:
        single_rules = [
            {'name': 'NPM HTTPS', 'proto': '1', 'sport': '443', 'ip': '192.168.31.12', 'dport': '4443'},
            {'name': 'HAOS cert', 'proto': '1', 'sport': '80', 'ip': '192.168.31.12', 'dport': '80'},
            {'name': 'plex oryg', 'proto': '1', 'sport': '32400', 'ip': '192.168.31.10', 'dport': '32400'},
            {'name': 'NAS ftp 20', 'proto': '1', 'sport': '20', 'ip': '192.168.31.10', 'dport': '20'},
            {'name': 'NAS ftp21', 'proto': '1', 'sport': '21', 'ip': '192.168.31.10', 'dport': '21'},
        ]
        range_rules = [
            {'name': 'FTP pasive', 'proto': '1', 'fport': '50000', 'tport': '51000', 'ip': '192.168.31.10'},
        ]

    print("\n--- Wgrywanie regul pojedynczych portow ---")
    for rule in single_rules:
        data = urllib.parse.urlencode(rule).encode('utf-8')
        req = urllib.request.Request(f'{base_url}/add_redirect', data=data, method='POST')
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                res = json.loads(resp.read().decode('utf-8'))
                status = "OK" if res.get('code') == 0 else f"BLAD {res.get('code')}"
                print(f"  [{status}] {rule['name']} (zewn: {rule['sport']} -> {rule['ip']}:{rule['dport']})")
        except Exception as e:
            print(f"  [WYJATEK] {rule['name']}: {e}")

    print("\n--- Wgrywanie regul zakresowych ---")
    for rule in range_rules:
        data = urllib.parse.urlencode(rule).encode('utf-8')
        req = urllib.request.Request(f'{base_url}/add_range_redirect', data=data, method='POST')
        try:
            with urllib.request.urlopen(req, timeout=5) as resp:
                res = json.loads(resp.read().decode('utf-8'))
                status = "OK" if res.get('code') == 0 else f"BLAD {res.get('code')}"
                print(f"  [{status}] {rule['name']} (zewn: {rule['fport']}-{rule['tport']} -> {rule['ip']})")
        except Exception as e:
            print(f"  [WYJATEK] {rule['name']}: {e}")

    print("\nAplikowanie regul w firewallu routera (redirect_apply)...")
    req_apply = urllib.request.Request(f'{base_url}/redirect_apply', data=b'', method='POST')
    try:
        with urllib.request.urlopen(req_apply, timeout=5) as resp:
            res = json.loads(resp.read().decode('utf-8'))
            print(f"  Wynik redirect_apply: {res}")
    except Exception as e:
        print(f"  Blad redirect_apply: {e}")

if __name__ == '__main__':
    run()
