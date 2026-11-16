"""
SODOM: Kompleksowe przywrocenie konfiguracji routera Xiaomi BE7000 po resecie.
Wbija:
1. Wszystkie 42 rezerwacje DHCP z rezerwacje_dhcp.xlsx
2. Wszystkie reguly Port Forwarding z przekierowania_portow.xlsx

Uzycie:
  python restore_router_config.py <stok_lub_pelny_url_z_przegladarki>
"""
import sys
import re
import subprocess
from pathlib import Path

def extract_stok(raw_input: str) -> str:
    m = re.search(r';stok=([a-f0-9]+)', raw_input)
    if m:
        return m.group(1)
    if re.fullmatch(r'[a-f0-9]{32}', raw_input.strip()):
        return raw_input.strip()
    return raw_input.strip()

def main():
    if len(sys.argv) < 2:
        print("Uzycie: python restore_router_config.py <stok_lub_url_z_przegladarki>")
        print("Przyklad: python restore_router_config.py fccdbff7c6f8c09ca81da7143c524cfd")
        print("lub: python restore_router_config.py http://192.168.31.1/cgi-bin/luci/;stok=.../web/home")
        sys.exit(1)

    stok = extract_stok(sys.argv[1])
    print(f"=== SODOM Router Recovery Tool (XRM CLI v1.0.0 / Xiaomi BE7000) ===")
    print(f"Rozpoznany stok: {stok}\n")

    scripts_dir = Path(__file__).resolve().parent

    print("==================================================")
    print(" Krok 1/2: Wgrywanie rezerwacji DHCP")
    print("==================================================")
    ret1 = subprocess.run([sys.executable, str(scripts_dir / "apply_dhcp.py"), stok])
    if ret1.returncode != 0:
        print("Ostrzezenie: apply_dhcp zwrocil kod bledu.")

    print("\n==================================================")
    print(" Krok 2/2: Wgrywanie przekierowan portow (NAT)")
    print("==================================================")
    ret2 = subprocess.run([sys.executable, str(scripts_dir / "apply_portforward.py"), stok])
    if ret2.returncode != 0:
        print("Ostrzezenie: apply_portforward zwrocil kod bledu.")

    print("\n=== Zakonczono przywracanie routera ===")

if __name__ == '__main__':
    main()
