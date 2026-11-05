"""Warn when a Victoria 3 update is coming or has landed.

The 1.15 changelog was posted a week before release, and the open beta weeks
before that. This reads Steam's news feed and prints one ALERT line for
each thing worth acting on, so patch day can start before players see the
game's "Unsupported Mods Detected" popup.

    python tools/patch_watch.py                  (prints ALERT lines, or QUIET)
    python tools/patch_watch.py --supported 1.13 (pretend, to test the alert)

Alerts on:
  - Steam news naming a game version newer than the one the mods declare
  - an installed game newer than the one the mods declare
Hotfixes inside the declared minor version (1.15.1) stay quiet: `1.15.*`
already covers them. Reads and prints only; nothing here touches the mods.
"""
import argparse
import json
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
APP_ID = 529340
NEWS = (f"https://api.steampowered.com/ISteamNews/GetNewsForApp/v2/"
        f"?appid={APP_ID}&count=30&maxlength=300&format=json")
INSTALL = Path(r"C:\Program Files (x86)\Steam\steamapps\common\Victoria 3")
METADATA = REPO / "smart_trade" / ".metadata" / "metadata.json"
OFFICIAL_FEED = "steam_community_announcements"
# 2 to 3 digits after "1." would be a date or a price, not a game version.
VERSION = re.compile(r"(?<![\d.])1\.(\d{1,2})(?:\.\d+)?(?![\d%])")


def declared_minor() -> int:
    value = json.loads(METADATA.read_text(encoding="utf-8"))["supported_game_version"]
    return int(value.split(".")[1])


def news_items() -> list[dict]:
    request = urllib.request.Request(NEWS, headers={"User-Agent": "vic3mods-patch-watch"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)["appnews"]["newsitems"]


def news_alerts(minor: int) -> list[str]:
    alerts = []
    for item in news_items():
        if item.get("feedname") != OFFICIAL_FEED:
            continue
        title = item["title"]
        newer = sorted({int(n) for n in VERSION.findall(title) if int(n) > minor})
        if newer:
            date = datetime.fromtimestamp(item["date"], timezone.utc).date()
            alerts.append(f"ALERT: 1.{newer[-1]} in Steam news, {date}: {title} {item.get('url', '')}")
    return alerts


def installed_alert(minor: int) -> str | None:
    settings = INSTALL / "launcher" / "launcher-settings.json"
    if not settings.is_file():
        return None
    raw = json.loads(settings.read_text(encoding="utf-8"))["rawVersion"]
    installed = int(raw.split(".")[1])
    if installed > minor:
        return f"ALERT: game {raw} is installed, the mods declare 1.{minor}.*. Run python tools/patch_day.py"
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--supported", help="pretend the mods declare this version, such as 1.13")
    args = parser.parse_args()
    minor = int(args.supported.split(".")[1]) if args.supported else declared_minor()
    alerts = [a for a in [installed_alert(minor)] if a] + news_alerts(minor)
    for line in alerts:
        print(line.encode("ascii", "replace").decode())
    if not alerts:
        print(f"QUIET: nothing newer than 1.{minor}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
