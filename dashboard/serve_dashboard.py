"""
serve_dashboard.py
Lightweight local HTTP server to launch the AuraCommerce Interactive BI Dashboard.
Runs on standard Python with 0 extra pip dependencies.
"""

import http.server
import socketserver
import webbrowser
import os
from pathlib import Path

PORT = 8080
DASHBOARD_DIR = Path(__file__).resolve().parent

os.chdir(DASHBOARD_DIR)

Handler = http.server.SimpleHTTPRequestHandler

print("=" * 65)
print("  🚀 AuraCommerce Interactive BI & Customer Analytics Dashboard")
print("=" * 65)
print(f"[INFO] Serving dashboard at: http://localhost:{PORT}")
print("[INFO] Press Ctrl+C in terminal to stop server.")
print("=" * 65)

# Open browser automatically
try:
    webbrowser.open(f"http://localhost:{PORT}")
except Exception:
    pass

with socketserver.TCPServer(("", PORT), Handler) as httpd:
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[INFO] Dashboard server stopped gracefully.")
