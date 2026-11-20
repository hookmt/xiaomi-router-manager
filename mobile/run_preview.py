#!/usr/bin/env python3
"""
Lekki lokalny serwer podglądu dla aplikacji mobilnej i tabletowej XRM.
Uruchamia podgląd na porcie 8088, dostępny w sieci lokalnej (dla tabletu i telefonu).
Zawiera wbudowany transparentny reverse-proxy dla API routera (/cgi-bin/luci/...),
dzięki czemu w przeglądarce i emulatorze nie występują blokady CORS.
"""

import http.server
import os
import socket
import socketserver
import sys
import urllib.request
import urllib.error

PORT = 8088
WWW_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "www")
ROUTER_IP = "192.168.31.1"

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
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Cache-Control", "no-cache, no-store, must-revalidate")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_GET(self):
        if self.path.startswith("/cgi-bin/") or self.path.startswith("/api/"):
            self._proxy_request("GET")
        else:
            super().do_GET()

    def do_POST(self):
        if self.path.startswith("/cgi-bin/") or self.path.startswith("/api/"):
            self._proxy_request("POST")
        else:
            super().do_POST()

    def _proxy_request(self, method):
        target_url = f"http://{ROUTER_IP}{self.path}"
        content_len = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_len) if content_len > 0 else None

        req = urllib.request.Request(target_url, data=body, method=method)
        req.add_header("User-Agent", "XRM-Preview-Proxy/1.0")
        if self.headers.get("Content-Type"):
            req.add_header("Content-Type", self.headers.get("Content-Type"))

        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                resp_data = resp.read()
                self.send_response(resp.status)
                ct = resp.headers.get("Content-Type", "application/json")
                self.send_header("Content-Type", ct)
                self.send_header("Content-Length", str(len(resp_data)))
                self.end_headers()
                self.wfile.write(resp_data)
        except urllib.error.HTTPError as e:
            resp_data = e.read()
            self.send_response(e.code)
            self.send_header("Content-Type", e.headers.get("Content-Type", "application/json"))
            self.send_header("Content-Length", str(len(resp_data)))
            self.end_headers()
            self.wfile.write(resp_data)
        except Exception as e:
            err_msg = f'{{"code": -1, "msg": "Proxy error: {str(e)}"}}'.encode("utf-8")
            self.send_response(502)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(err_msg)))
            self.end_headers()
            self.wfile.write(err_msg)

def main():
    if not os.path.isdir(WWW_DIR):
        print(f"Błąd: folder www nie istnieje: {WWW_DIR}")
        sys.exit(1)

    lan_ips = get_lan_ips()
    
    print("=" * 60)
    print("  XIAOMI ROUTER MANAGER (XRM) - SERWER PODGLĄDU Z PROXY")
    print("=" * 60)
    print(f"Katalog źródłowy: {WWW_DIR}")
    print(f"Router docelowy:  http://{ROUTER_IP}/")
    print("\nAdresy do otwarcia:")
    print(f"  ● Lokalnie (na tym PC):    http://localhost:{PORT}/")
    for ip in lan_ips:
        print(f"  ● W sieci LAN (tablet/tel): http://{ip}:{PORT}/")
    print("=" * 60)
    print("Naciśnij Ctrl+C, aby zatrzymać serwer.\n")

    socketserver.ThreadingTCPServer.allow_reuse_address = True
    with socketserver.ThreadingTCPServer(("0.0.0.0", PORT), CustomHTTPHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nZatrzymano serwer podglądu.")

if __name__ == "__main__":
    main()
