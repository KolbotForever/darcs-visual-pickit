from __future__ import annotations

import sys
import re
from pathlib import Path


APP_NAME = "Darc's Visual Pickit"
APP_PUBLISHER = "KolbotForever"
APP_VENDOR = APP_PUBLISHER
APP_SLUG = "DarcsVisualPickit"
APP_VERSION = "V0.2.02"
PUBLIC_RELEASE_VERSION = "V0.2.02"
APP_BUILD_DATE = "2026-03-26T07:28:00-07:00"

ENTRY_SCRIPT = "app_main.py"
BUILD_SCRIPT = "build_release.bat"
INSTALLER_SCRIPT = "DarcsVisual_release.iss"
RELEASE_NOTES_FILE = "GITHUB_RELEASE.md"

EXE_NAME = "DarcsVisualPickit"
ICON_FILE = "darc.ico"
FONT_FILE = "exocent.ttf"

GITHUB_REPO = "KolbotForever/darcs-visual-pickit"
GITHUB_LATEST_RELEASE_API = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
GITHUB_RELEASES_PAGE = f"https://github.com/{GITHUB_REPO}/releases"
APP_USER_MODEL_ID = "KolbotForever.DarcsVisualPickit"


def numeric_version(version_text: str = PUBLIC_RELEASE_VERSION) -> str:
    return str(version_text or "").strip().lstrip("Vv")


def _iss_escape(value: str) -> str:
    return str(value or "").replace('"', '""')


def env_assignments() -> list[str]:
    values = {
        "RELEASE_APP_NAME": APP_NAME,
        "RELEASE_APP_PUBLISHER": APP_PUBLISHER,
        "RELEASE_APP_VENDOR": APP_VENDOR,
        "RELEASE_APP_SLUG": APP_SLUG,
        "RELEASE_APP_VERSION": APP_VERSION,
        "RELEASE_PUBLIC_RELEASE_VERSION": PUBLIC_RELEASE_VERSION,
        "RELEASE_VERSION_NUMERIC": numeric_version(),
        "RELEASE_APP_BUILD_DATE": APP_BUILD_DATE,
        "RELEASE_ENTRY_SCRIPT": ENTRY_SCRIPT,
        "RELEASE_BUILD_SCRIPT": BUILD_SCRIPT,
        "RELEASE_INSTALLER_SCRIPT": INSTALLER_SCRIPT,
        "RELEASE_NOTES_FILE": RELEASE_NOTES_FILE,
        "RELEASE_EXE_NAME": EXE_NAME,
        "RELEASE_ICON_FILE": ICON_FILE,
        "RELEASE_FONT_FILE": FONT_FILE,
        "RELEASE_GITHUB_REPO": GITHUB_REPO,
        "RELEASE_GITHUB_RELEASES_PAGE": GITHUB_RELEASES_PAGE,
        "RELEASE_APP_USER_MODEL_ID": APP_USER_MODEL_ID,
    }
    return [f'set "{key}={value}"' for key, value in values.items()]


def iss_include_text() -> str:
    lines = [
        "; Auto-generated from release_metadata.py",
        f'#define MyAppName "{_iss_escape(APP_NAME)}"',
        f'#define MyAppVersion "{_iss_escape(numeric_version())}"',
        f'#define MyAppPublisher "{_iss_escape(APP_PUBLISHER)}"',
        f'#define MyAppExeName "{_iss_escape(EXE_NAME)}.exe"',
        f'#define MyAppURL "{_iss_escape(GITHUB_RELEASES_PAGE)}"',
    ]
    return "\n".join(lines) + "\n"


def write_iss_include(path_text: str) -> None:
    path = Path(path_text)
    path.write_text(iss_include_text(), encoding="utf-8", newline="\r\n")


def sync_release_notes(path_text: str) -> None:
    path = Path(path_text)
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    build_line = f"Build-Date: {APP_BUILD_DATE}"
    if re.search(r"(?im)^Build-Date:\s*.+$", text):
        text = re.sub(r"(?im)^Build-Date:\s*.+$", build_line, text, count=1)
    else:
        lines = text.splitlines()
        if lines and lines[0].startswith("#"):
            lines.insert(1, "")
            lines.insert(2, build_line)
        else:
            lines.insert(0, build_line)
        text = "\n".join(lines) + ("\n" if text.endswith("\n") else "")
    path.write_text(text, encoding="utf-8", newline="\r\n")


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: release_metadata.py [env-cmd|write-issinc <path>|sync-release-notes <path>]", file=sys.stderr)
        return 1

    command = str(argv[1] or "").strip().lower()
    if command == "env-cmd":
        for line in env_assignments():
            print(line)
        return 0
    if command == "write-issinc":
        target = argv[2] if len(argv) > 2 else ".version_auto.issinc"
        write_iss_include(target)
        return 0
    if command == "sync-release-notes":
        target = argv[2] if len(argv) > 2 else RELEASE_NOTES_FILE
        sync_release_notes(target)
        return 0

    print(f"unknown command: {command}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
