"""
SODOM: Wgrywanie rezerwacji DHCP do routera Xiaomi BE7000 przez API MiWiFi.
Zrodlo danych: rezerwacje_dhcp.xlsx w tym samym folderze lub w PLIKI_SYSTEMU\\SIEC.
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
    local_path = current_dir / "rezerwacje_dhcp.xlsx"
    if local_path.is_file():
        return local_path
    candidates = [
        current_dir.parent.parent.parent / "SIEC" / "rezerwacje_dhcp.xlsx",
        Path(r"N:\ChatGPT\HAOS\PLIKI_SYSTEMU\SIEC\rezerwacje_dhcp.xlsx"),
        Path(r"S:\ChatGPT\HAOS\PLIKI_SYSTEMU\SIEC\rezerwacje_dhcp.xlsx"),
        Path(r"\\HOOKMTSRV\AI\ChatGPT\HAOS\PLIKI_SYSTEMU\SIEC\rezerwacje_dhcp.xlsx"),
    ]
    for c in candidates:
        if c.is_file():
            return c
    raise FileNotFoundError("Nie znaleziono pliku rezerwacje_dhcp.xlsx!")

def load_reservations(xlsx_path: Path):
    with zipfile.ZipFile(xlsx_path, 'r') as z:
        shared_strings = []
        if 'xl/sharedStrings.xml' in z.namelist():
            root = ET.fromstring(z.read('xl/sharedStrings.xml'))
            for si in root.findall('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}si'):
                text = ''.join(t.text for t in si.iter('{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t') if t.text)
                shared_strings.append(text)

        sheet1 = ET.fromstring(z.read('xl/worksheets/sheet1.xml'))
        reservations = []
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

            ip = cells.get('B', '')
            mac = cells.get('C', '')
            name = cells.get('D', '')
            if mac and len(mac) >= 12 and ':' in mac:
                parts = ip.split('.')
                if len(parts) == 4:
                    clean_ip = f'{parts[0]}.{parts[1]}.{parts[2]}.{int(parts[3])}'
                    reservations.append({'ip': clean_ip, 'mac': mac.upper(), 'name': name})
        return reservations

def run():
    if len(sys.argv) < 2:
        print("Uzycie: python apply_dhcp.py <stok>")
        sys.exit(1)

    stok = sys.argv[1].strip()
    xlsx_path = get_xlsx_path()
    reservations = load_reservations(xlsx_path)
    print(f"Zaladowano {len(reservations)} rezerwacji z {xlsx_path.name}")

    info_url = f'http://192.168.31.1/cgi-bin/luci/;stok={stok}/api/xqnetwork/macbind_info'
    bind_url = f'http://192.168.31.1/cgi-bin/luci/;stok={stok}/api/xqnetwork/mac_bind'

    # Pobierz istniejace
    req = urllib.request.Request(info_url)
    with urllib.request.urlopen(req, timeout=5) as resp:
        curr_data = json.loads(resp.read().decode('utf-8'))
        existing_macs = {b['mac'].upper(): b['ip'] for b in curr_data.get('list', [])}
        print(f"Obecnie w routerze powiazanych: {len(existing_macs)} urzadzen")

    added = 0
    skipped = 0
    errors = 0

    for r in reservations:
        mac = r['mac']
        ip = r['ip']
        name = r['name']
        if mac in existing_macs and existing_macs[mac] == ip:
            skipped += 1
            continue

        payload = {'name': name, 'mac': mac, 'ip': ip}
        data = urllib.parse.urlencode(payload).encode('utf-8')
        post_req = urllib.request.Request(bind_url, data=data, method='POST')
        try:
            with urllib.request.urlopen(post_req, timeout=5) as resp:
                res = json.loads(resp.read().decode('utf-8'))
                if res.get('code') == 0:
                    added += 1
                    print(f"  [OK] {ip} -> {mac} ({name})")
                else:
                    errors += 1
                    print(f"  [BLAD {res.get('code')}] {ip} -> {mac} ({name}): {res.get('msg')}")
        except Exception as e:
            errors += 1
            print(f"  [WYJATEK] {ip} -> {mac} ({name}): {e}")

    print(f"\nPodsumowanie DHCP: dodano {added}, pominieto istniejacych {skipped}, bledow {errors}")

if __name__ == '__main__':
    run()
