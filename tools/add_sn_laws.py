"""Add law types a game patch introduced to Smart Notifications.

Each law needs one entry in five hand-maintained dispatch files plus the
English loc. This clones law_protectionism's entry in each, swapping the law
name (and, in the loc, the law group). check_every_vanilla_law_is_dispatched
in check_references.py fails the build while a vanilla law is missing, so
this script is what that failure points at.

Works on bytes so each file keeps its BOM and line endings.

Usage:  python tools/add_sn_laws.py     (then rerun the three generators it names)
"""
import re
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SN = REPO / "smart_notifications"
GAME = Path(r"C:\Program Files (x86)\Steam\steamapps\common\Victoria 3\game")
MODEL = "law_protectionism"
MODEL_GROUP = "lawgroup_trade_policy"
DISPATCH = SN / "common/on_actions/09_smart_notifications_law_ready_toast.txt"
BLOCK_FILES = [
    DISPATCH,
    SN / "common/scripted_guis/smart_notifications_law_commitment_list_sgui.txt",
    SN / "common/scripted_guis/smart_notifications_law_notify_sgui.txt",
    SN / "common/scripted_triggers/01_smart_notifications_law_wanted_trigger.txt",
]
MESSAGES = SN / "common/messages/99_smart_notifications_messages.txt"
LOC = SN / "localization/english/smart_notifications_l_english.yml"


def vanilla_laws() -> dict[str, str]:
    """law -> its law group, from the installed game."""
    out = {}
    for path in (GAME / "common/laws").glob("*.txt"):
        text = path.read_text(encoding="utf-8-sig")
        for m in re.finditer(r"(?ms)^(law_\w+)\s*=\s*\{(.*?)^\}", text):
            out[m.group(1)] = re.search(r"group\s*=\s*(\w+)", m.group(2)).group(1)
    return out


def balance(line: bytes) -> int:
    code = line.split(b"#", 1)[0]
    return code.count(b"{") - code.count(b"}")


def model_spans(lines: list[bytes]) -> list[tuple[int, int]]:
    """(first, last) line index of each entry naming MODEL, outermost
    if/else_if (or a self-contained one-liner), without duplicates."""
    spans = []
    needle = b"law_type:" + MODEL.encode()
    for i, line in enumerate(lines):
        if needle not in line or (spans and i <= spans[-1][1]):
            continue
        head = line.strip()
        if balance(line) == 0 and head.startswith((b"if = {", b"AND = {")):
            spans.append((i, i))
            continue
        depth, start = 0, i
        while True:
            depth -= balance(lines[start])
            if depth < 0 and lines[start].strip() in (b"if = {", b"else_if = {"):
                break
            start -= 1
        depth, end = 0, start
        while True:
            depth += balance(lines[end])
            if depth == 0:
                break
            end += 1
        spans.append((start, end))
    if not spans:
        raise SystemExit(f"no {MODEL} entry found")
    return spans


def clone(lines: list[bytes], law: str, group: str) -> list[bytes]:
    return [l.replace(MODEL.encode(), law.encode())
            .replace(MODEL_GROUP.encode(), group.encode()) for l in lines]


def add_blocks(path: Path, laws: dict[str, str]):
    lines = path.read_bytes().splitlines(keepends=True)
    for start, end in reversed(model_spans(lines)):
        block = lines[start:end + 1]
        new = [l for law in sorted(laws) for l in clone(block, law, laws[law])]
        lines[end + 1:end + 1] = new
    path.write_bytes(b"".join(lines))


def add_messages(laws: dict[str, str]):
    lines = MESSAGES.read_bytes().splitlines(keepends=True)
    head = f"smart_notifications_law_ready_toast_{MODEL} = {{".encode()
    start = next(i for i, l in enumerate(lines) if l.startswith(head))
    end = next(i for i in range(start, len(lines)) if lines[i].rstrip() == b"}")
    block = lines[start:end + 1]
    new = [l for law in sorted(laws) for l in clone(block, law, laws[law])]
    lines[end + 1:end + 1] = new
    MESSAGES.write_bytes(b"".join(lines))


def add_loc(laws: dict[str, str]):
    lines = LOC.read_bytes().splitlines(keepends=True)
    wanted = [i for i, l in enumerate(lines) if MODEL.encode() in l]
    for i in reversed(wanted):
        new = [c for law in sorted(laws) for c in clone([lines[i]], law, laws[law])]
        lines[i + 1:i + 1] = new
    LOC.write_bytes(b"".join(lines))


def main():
    vanilla = vanilla_laws()
    known = set(re.findall(r"law_type:(law_\w+)", DISPATCH.read_text(encoding="utf-8-sig")))
    missing = {law: group for law, group in vanilla.items() if law not in known}
    if not missing:
        print("Every vanilla law is already dispatched.")
        return
    print(f"Adding {len(missing)}: {', '.join(sorted(missing))}")
    for path in BLOCK_FILES:
        add_blocks(path, missing)
    add_messages(missing)
    add_loc(missing)
    print("Now run: gen_law_flag_clear.py, gen_law_cooldown.py, gen_sn_translations.py")


if __name__ == "__main__":
    main()
