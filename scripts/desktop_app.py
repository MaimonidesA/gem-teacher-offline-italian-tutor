#!/usr/bin/env python3
"""Open Gem Teacher in an isolated, tab-free desktop window."""
from pathlib import Path
import os
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from teacher import config


def main():
    config.prepare()
    log_path = config.DATA / "desktop.log"
    try:
        # The server launcher is idempotent; opening the dock shortcut twice
        # reuses the service and the browser's dedicated profile.
        subprocess.run([sys.executable, str(ROOT / "scripts/launcher.py"), "start", "--no-browser"],
                       cwd=ROOT, check=True, timeout=25)
        browser = next((str(path) for path in (
            Path("/snap/bin/brave"), Path("/usr/bin/brave-browser"),
            Path("/usr/bin/google-chrome"), Path("/usr/bin/chromium"),
        ) if path.is_file()), None)
        if not browser:
            raise RuntimeError("Install Brave or Chromium to open the desktop window.")
        if browser == "/snap/bin/brave":
            # Snap browsers can write their own common directory. This profile
            # is independent of the personal browser and Wombat Station.
            profile = Path.home() / "snap/brave/common/gem-teacher/profile"
        else:
            profile = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / "gem-teacher/browser"
        profile.mkdir(parents=True, exist_ok=True)
        command = [browser, f"--user-data-dir={profile}", "--class=gem-teacher", "--name=gem-teacher",
                   "--ozone-platform=x11", "--no-first-run", "--no-default-browser-check",
                   "--disable-background-networking", "--disable-component-update", "--disable-sync",
                   "--disable-features=Translate,MediaRouter", "--window-size=1280,900",
                   f"--app=http://127.0.0.1:{config.PORT}"]
        with log_path.open("a") as log:
            process = subprocess.Popen(command, cwd=ROOT, stdin=subprocess.DEVNULL,
                                       stdout=log, stderr=log, start_new_session=True)
        try:
            result = process.wait(timeout=2)
            if result:
                raise RuntimeError(f"The desktop window could not start. See {log_path}")
        except subprocess.TimeoutExpired:
            pass
    except Exception as exc:
        with log_path.open("a") as log:
            log.write(f"{exc}\n")
        if shutil.which("notify-send"):
            subprocess.run(["notify-send", "--icon=gem-teacher", "Gem Teacher", str(exc)], check=False)
        raise SystemExit(str(exc))


if __name__ == "__main__":
    main()
