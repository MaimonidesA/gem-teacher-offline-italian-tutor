#!/usr/bin/env python3
"""Start/stop only this project's own localhost service."""
import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time
import urllib.request
import webbrowser

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from teacher import config

def identity(pid):
    try:
        command = Path(f"/proc/{pid}/cmdline").read_bytes().split(b"\0")
        return Path(f"/proc/{pid}/cwd").resolve() == ROOT and b"teacher" in command and b"-m" in command
    except (OSError, ValueError):
        return False

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["start", "stop", "status"], nargs="?", default="start")
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    config.prepare()
    pidfile = config.DATA / "server.pid"
    pid = int(pidfile.read_text()) if pidfile.exists() else None
    running = pid and identity(pid)
    url = f"http://127.0.0.1:{config.PORT}"
    if args.command == "status":
        print(f"Running: {url} (PID {pid})" if running else "Parliamo is stopped.")
        return
    if args.command == "stop":
        if running:
            os.kill(pid, signal.SIGTERM)
            for _ in range(50):
                if not identity(pid): break
                time.sleep(.1)
            if identity(pid):
                raise SystemExit("The server is still finishing a request. Try stop again shortly.")
        pidfile.unlink(missing_ok=True)
        print("Parliamo stopped. Shared Ollama models retain their normal 15-minute idle timeout.")
        return
    if not running:
        with (config.DATA / "server.log").open("a") as log:
            process = subprocess.Popen([sys.executable, "-m", "teacher", "--port", str(config.PORT)], cwd=ROOT,
                stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True,
                env=dict(os.environ, PYTHONNOUSERSITE="1"))
        pidfile.write_text(str(process.pid))
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        for _ in range(80):
            if process.poll() is not None:
                pidfile.unlink(missing_ok=True)
                raise SystemExit(f"Server failed to start. Check {config.DATA / 'server.log'}")
            try:
                with opener.open(url + "/api/state", timeout=1) as response:
                    if "topics" in json.load(response):
                        break
            except OSError:
                time.sleep(.1)
        else:
            process.terminate()
            pidfile.unlink(missing_ok=True)
            raise SystemExit("Server did not become ready; see data/server.log.")
    print(url)
    if not args.no_browser:
        webbrowser.open(url)

if __name__ == "__main__":
    main()
