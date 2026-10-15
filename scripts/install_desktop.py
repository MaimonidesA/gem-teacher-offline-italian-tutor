#!/usr/bin/env python3
"""Install a per-user GNOME launcher and preserve existing dock favorites."""
import argparse
import ast
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent.parent
APP_ID = "gem-teacher.desktop"


def desktop_value(value):
    return str(value).replace("\\", "\\\\").replace("\n", "\\n").replace("\t", "\\t").replace("\r", "\\r")


def exec_arg(value):
    # Desktop Entry Exec quoting is not shell quoting.
    value = str(value).replace("%", "%%")
    for char in ("\\", '"', "`", "$"):
        value = value.replace(char, "\\" + char)
    return desktop_value('"' + value + '"')


def favorites():
    value = subprocess.check_output(["gsettings", "get", "org.gnome.shell", "favorite-apps"], text=True).strip()
    return ast.literal_eval(value.removeprefix("@as "))


def set_favorites(value):
    subprocess.run(["gsettings", "set", "org.gnome.shell", "favorite-apps", repr(value)], check=True)
    if favorites() != value:
        raise RuntimeError("GNOME did not retain the dock change.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--uninstall", action="store_true")
    parser.add_argument("--no-pin", action="store_true")
    args = parser.parse_args()
    share = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share"))
    applications = share / "applications"
    icons = share / "icons/hicolor"
    desktop = applications / APP_ID
    svg = icons / "scalable/apps/gem-teacher.svg"
    png = icons / "256x256/apps/gem-teacher.png"
    if args.uninstall:
        old = favorites()
        if APP_ID in old:
            set_favorites([item for item in old if item != APP_ID])
        for path in (desktop, svg, png):
            path.unlink(missing_ok=True)
        print("Gem Teacher removed from the applications menu and dock. Learning data was kept.")
    else:
        for directory in (applications, svg.parent, png.parent):
            directory.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / "web/app-icon.svg", svg)
        # Scalable SVG is the primary icon; a PNG is supplied for other shells.
        if (ROOT / "web/app-icon.png").exists():
            shutil.copy2(ROOT / "web/app-icon.png", png)
        content = "\n".join([
            "[Desktop Entry]", "Version=1.0", "Type=Application", "Name=Gem Teacher",
            "GenericName=Offline Language Teacher", "GenericName[fr]=Professeur de langues hors ligne",
            "Comment=Parliamo — learn Italian with your own local Gemma teacher",
            "Comment[fr]=Parliamo — apprenez l’italien avec votre professeur Gemma local",
            f"Exec={exec_arg(ROOT / 'open_teacher.sh')}", f"Path={desktop_value(ROOT)}",
            "Icon=gem-teacher", "Terminal=false", "Categories=Education;Languages;",
            "Keywords=Parliamo;Gemma;Italian;French;English;teacher;language;offline;",
            "StartupNotify=true", "StartupWMClass=gem-teacher", "Actions=StopTeacher;", "",
            "[Desktop Action StopTeacher]", "Name=Stop teacher service", "Name[fr]=Arrêter le professeur",
            f"Exec={exec_arg(ROOT / 'stop_teacher.sh')}", "",
        ])
        # Validate the concrete launcher before installing/pinning it.
        draft = ROOT / "data" / APP_ID
        draft.parent.mkdir(parents=True, exist_ok=True)
        draft.write_text(content)
        if shutil.which("desktop-file-validate"):
            subprocess.run(["desktop-file-validate", str(draft)], check=True)
        shutil.copy2(draft, desktop)
        desktop.chmod(0o644)
        if not args.no_pin:
            old = favorites()
            if APP_ID not in old:
                new = list(old)
                position = new.index("gemradio.desktop") + 1 if "gemradio.desktop" in new else len(new)
                new.insert(position, APP_ID)
                (ROOT / "data/desktop-install.json").write_text(json.dumps({"previous_favorites": old,
                    "desktop": str(desktop), "icon": str(svg)}, indent=2))
                set_favorites(new)
        print(f"Installed Gem Teacher: {desktop}")
        print("Pinned beside GemRadio." if not args.no_pin else "Available in the applications menu.")
    if shutil.which("update-desktop-database"):
        subprocess.run(["update-desktop-database", str(applications)], check=False)
    if shutil.which("gtk-update-icon-cache"):
        subprocess.run(["gtk-update-icon-cache", "-f", "-t", str(icons)], capture_output=True, check=False)


if __name__ == "__main__":
    main()
