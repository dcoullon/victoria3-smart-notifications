"""Print each mod's Most Popular rank and lifetime subscribers as JSON.

Rank is the position in the Most Popular list on the Workshop home page, which
is what a player sees first. Steam keeps no history of it. null means the mod
is not in the list today. Run by the scheduled task vic3-workshop-rank, which
writes the result to columns K and L of the "Mod subscribers daily" sheet.

Cloud routines cannot run this: their proxy refuses Steam (tested 2026-11-05).
"""
import json
import re
import urllib.parse
import urllib.request

MODS = {"Smart notifs": "3799284646", "Build all": "3803950977", "Smart treaties": "3814823352"}
HOME = "https://steamcommunity.com/app/529340/workshop/"
DETAILS = "https://api.steampowered.com/ISteamRemoteStorage/GetPublishedFileDetails/v1/"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}


def fetch(url: str, data: bytes | None = None) -> str:
    request = urllib.request.Request(url, data, HEADERS)
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", "replace")


def main():
    html = fetch(HOME)
    start = html.find(">Most Popular<")
    listed = list(dict.fromkeys(re.findall(r"filedetails/\?id=(\d+)", html[start:]))) if start >= 0 else []
    form = {"itemcount": len(MODS)}
    form.update({f"publishedfileids[{n}]": item for n, item in enumerate(MODS.values())})
    details = json.loads(fetch(DETAILS, urllib.parse.urlencode(form).encode()))
    lifetime = {f["publishedfileid"]: f.get("lifetime_subscriptions")
                for f in details["response"]["publishedfiledetails"]}
    print(json.dumps({
        "ok": start >= 0 and len(listed) >= 5,
        "list_len": len(listed),
        "mods": {tab: {"rank": listed.index(item) + 1 if item in listed else None,
                       "lifetime": lifetime.get(item)}
                 for tab, item in MODS.items()},
    }))


if __name__ == "__main__":
    main()
