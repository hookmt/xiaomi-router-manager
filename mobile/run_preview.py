#!/usr/bin/env python3
"""
Lekki lokalny serwer podglądu dla aplikacji mobilnej i tabletowej XRM.
Uruchamia podgląd na porcie 8088, dostępny w sieci lokalnej (dla tabletu i telefonu).
"""

import http.server
import socket
import socketserver
import os
import sys

PORT = 8088
WWW_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "www")

def get_lan_ips():
    ips = []
    try:
        hostname = socket.gethostname()
        for ip in socket.gethostbyname_ex(hostname)[2]:
            if not ip.startswith("127."):
                ips.append(ip)
    except Exception:
        pass
    return ips

class CustomHTTPHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WWW_DIR, **kwargs)

    def end_headers(self):
        # Nagłówki CORS i cache-control ułatwiające testowanie
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        super().end_headers()

def main():
    if not os.path.isdir(WWW_DIR):
        print(f"Błąd: folder www nie istnieje: {WWW_DIR}")
        sys.exit(1)

    lan_ips = get_lan_ips()
    
    print("=" * 60)
    print("  XIAOMI ROUTER MANAGER (XRM) - SERWER PODGLĄDU MOBILNEGO")
    print("=" * 60)
    print(f"Katalog źródłowy: {WWW_DIR}")
    print("\nAdresy do otwarcia:")
    print(f"  ● Lokalnie (na tym PC):    http://localhost:{PORT}/")
    for ip in lan_ips:
        print(f"  ● W sieci LAN (tablet/tel): http://{ip}:{PORT}/")
    print("=" * 60)
    print("Naciśnij Ctrl+C, aby zatrzymać serwer.\n")

    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("0.0.0.0", PORT), CustomHTTPHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nZatrzymano serwer podglądu.")

if __name__ == "__main__":
    main()
