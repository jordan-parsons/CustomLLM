#!/usr/bin/env python3
"""Serve the dashboard locally, regenerating it periodically from live state."""
import argparse, http.server, os, socketserver, subprocess, threading, time

ROOT = os.path.dirname(os.path.abspath(__file__))
DASH = os.path.join(ROOT, "dashboard")


def rebuild_loop(interval):
    while True:
        try:
            subprocess.run(["python3", os.path.join(ROOT, "build_dashboard.py")],
                           capture_output=True, timeout=300)
        except Exception:
            pass
        time.sleep(interval)


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=DASH, **kw)

    def do_GET(self):
        if self.path in ("/", ""):
            self.path = "/index.html"
        return super().do_GET()

    def log_message(self, fmt, *args):
        pass


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--interval", type=int, default=60,
                    help="seconds between regenerations (0 = never)")
    a = ap.parse_args()
    subprocess.run(["python3", os.path.join(ROOT, "build_dashboard.py")])
    if a.interval > 0:
        threading.Thread(target=rebuild_loop, args=(a.interval,), daemon=True).start()
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("0.0.0.0", a.port), Handler) as httpd:
        print(f"dashboard on http://localhost:{a.port}  (rebuild every {a.interval}s)")
        httpd.serve_forever()


if __name__ == "__main__":
    main()
