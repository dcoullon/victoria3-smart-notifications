"""Regenerate the table of contents in docs/engine-notes.md.

engine-notes.md is ~1200 lines across 40+ sections, and CLAUDE.md tells every
session to "read the relevant section" before relying on a rule. Without a
contents list that meant either reading the whole file (~17k tokens) or a
grep/read/grep round trip each time. The TOC makes it one targeted read.

Run after adding or renaming a section:
    python tools/gen_engine_notes_toc.py

check_references.check_engine_notes_toc_is_current() fails the validator if
the TOC and the headings have drifted, so this can't silently go stale.
"""
import re
import sys
import unicodedata
from pathlib import Path

DOC = Path(__file__).resolve().parent.parent / "docs" / "engine-notes.md"
START = "<!-- TOC -->"
END = "<!-- /TOC -->"


def anchor(title: str) -> str:
    """github-slugger's rule, followed exactly so the links work on GitHub as
    well as in a local viewer: lowercase and trim, keep only letters, numbers,
    connector punctuation (_) and dash punctuation (- and em dash), then turn
    each remaining space into a hyphen. Note it does NOT collapse runs -- an
    em dash surrounded by spaces becomes "-—-", not "-"."""
    kept = []
    for ch in title.strip().lower():
        if ch.isalnum() or ch.isspace() or unicodedata.category(ch) in ("Pd", "Pc"):
            kept.append("-" if ch.isspace() else ch)
    return "".join(kept)


def section_titles(text: str) -> list[str]:
    return re.findall(r"(?m)^## (.+?)\s*$", text)


def render(titles: list[str]) -> str:
    lines = [START, ""]
    for t in titles:
        # Strip code marks so the list reads as plain prose, and escape square
        # brackets -- several headings contain them ([THIS.GetCountry...],
        # "Literal [...] in loc text") and an unescaped [ inside a link label
        # terminates the label early, breaking the link.
        label = t.replace("`", "").replace("[", r"\[").replace("]", r"\]")
        lines.append(f"- [{label}](#{anchor(t)})")
    lines += ["", END]
    return "\n".join(lines)


def main() -> int:
    raw = DOC.read_bytes()
    crlf = b"\r\n" in raw
    bom = raw.startswith(b"\xef\xbb\xbf")
    text = raw.decode("utf-8-sig").replace("\r\n", "\n")

    titles = section_titles(text)
    if not titles:
        print("no '## ' sections found -- nothing to do")
        return 1
    toc = render(titles)

    if START in text and END in text:
        text = re.sub(re.escape(START) + r".*?" + re.escape(END), lambda _: toc,
                      text, count=1, flags=re.S)
    else:
        # First run: place the TOC after the intro paragraph, before the very
        # first section heading.
        first = text.index("\n## ")
        text = text[:first] + "\n" + toc + "\n" + text[first:]

    if crlf:
        text = text.replace("\n", "\r\n")
    out = text.encode("utf-8")
    if bom:
        out = b"\xef\xbb\xbf" + out
    DOC.write_bytes(out)
    print(f"engine-notes.md: TOC written, {len(titles)} sections")
    return 0


if __name__ == "__main__":
    sys.exit(main())
