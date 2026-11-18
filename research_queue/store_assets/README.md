Store assets: Reorder Research Queue
====================================

**Not shipped.** `package_release.py` copies only `.metadata/`, `common/`,
`events/`, `gui/`, `localization/` and `thumbnail.png`.

## Workshop item

ID `3841721873`, first published 2026-11-18 as 0.10:
https://steamcommunity.com/sharedfiles/filedetails/?id=3841721873
(images: https://steamcommunity.com/sharedfiles/managepreviews/?id=3841721873).

Gallery GIF: `gif/reorder_workshop.gif`, 1,502,924 bytes, under Steam's 2 MB
image limit. It has all 202 frames and the full 10.27 s of the 2,403,535-byte
recording, with unchanged pixels stored as transparent and one shared 255-colour
palette. That palette is built from 12 sample frames plus every distinct colour
of the recording, so the yellow click marker keeps a slot. Mean error against
the source is 1.74 per channel (0-255).

## Title

**Reorder Research Queue: drag & drop techs** (41 characters; user's call,
2026-11-15: spaces around the & so "drag" and "drop" are separate search
words). Measured 400 px (Arial) and 383 px (Segoe UI), against 405 and
401 px for the longest title seen to fit whole: inside, by 5 to 18 px. If
Steam's font runs wider, the list shows "drag & drop te..."; check the
real list after upload and drop "techs" if so. Mod name
"Reorder Research Queue": verb first, plain English, the same words as the
thumbnail (user's call, 2026-11-15; it replaced "Research Queue Reorder").
The in-game tag stays "(Reorder)".

The "In the past week" carousel cuts titles at about 24 to 26 characters
(counted on 2026-11-15 screenshots: "Construction Queue: Multi...",
"Dynamic Political Moveme..."), so it shows "Reorder Research Queue" (22)
whole. The popular list cuts at about 400 px: measured with Arial and Segoe
UI at 20px (Steam's Motiva Sans is not installed here), "Oops! Victoria
Reincarnated in Another World" fits at 401 to 405 px and "[BETA
1.13.11]The New Order..." is cut at 387 to 410 px. "Reorder Research Queue:
drag and drop techs" measures 400 to 420 px, on the edge; "...: Drag & Drop"
measures 337 to 352 px, about 15% inside. "drag and drop" stays in the
description's first sentence for search.

The two best-converting listings use the same "Name: plain benefit" shape.
Keyword research (Gemini, unverified; its Reddit scores and search claims
were not checked) suggested "Research Queue: Drag & Drop".

## Thumbnail

**Chosen: `thumb_B_amber_dark.png`** (copied to `../thumbnail.png`, user's
call 2026-11-15): option B's layout with the whole name, on E's amber.
Teal B nearly merged with the dark green Construction Queue tile beside it
in the carousel; amber is the brightest tile in the row, and dark text read
more easily than white with an outline (`previews/b_variants_carousel.png`).

`make_thumbnails.py` draws them from the game's own art (tech icons, the
queue's round frame and badge, the pointer cursor; Playfair Display and EB
Garamond are OFL fonts shipped with the game). `previews/` places each one
in the 2026-11-15 carousel and popular-list screenshots, at their real sizes
(244px and 136px). The chosen one is copied to `../thumbnail.png`.

| | look | carousel (priority) | 136px list |
|---|---|---|---|
| A | cream, Smart Treaties family; title, then the row with the 4th tech lifted to slot 1 | stands out: the only light tile among dark painted ones | title reads, row small |
| B | teal, "REORDER RESEARCH", one big arrow | stands out, unique colour | reads |
| C | cream, before/after rows | too busy at 244px | busy |
| D | navy and gold, Build All family | blends into the dark row | dark |
| E | amber, one giant tech mid-drag with the cursor, "DRAG & DROP / RESEARCH QUEUE" | stands out, and the only one showing the gesture at a glance | reads |

## What the three live listings suggest (2026-11-15, Steam Web API)

| | visitors | subscribers | rate (current / visitors) | lifetime subs / visitors |
|---|---|---|---|---|
| Smart Notifications | 1,954 | 511 | 26.2% | 30.1% |
| Build All | 1,976 | 758 | 38.4% | 42.2% |
| Smart Treaties | 5,983 | 3,080 | 51.5% | 54.3% |

Three items, with topic and traffic source mixed in, so these are leads,
not findings:
- The two higher converters open with the concrete result in plain words
  inside the ~230-character hover preview. Smart Notifications spends its
  preview on an `[h1]` repeating the title, then "less notification noise".
- Their titles carry a plain benefit ("what each goods trade earns you",
  "Bulk Construction, One Click"); "Smart Notifications" alone does not.
- Their thumbnails are a huge title plus a crop of the real UI; Smart
  Notifications' is a painted scene with small text.
- Smart Notifications asks for a settings reset before it works; the other
  two lead with "no cheating".

Applied here: plain-benefit title, the result and the differentiator
(prerequisites travel) in the first sentence, no-cheating inside the hover
preview, a short page (256 words against 434 and 629).

## Description

`../STEAM_WORKSHOP_DESCRIPTION.bbcode`. The GIF goes inline after the
opening paragraphs (https://i.imgur.com/gr5cjiT.gif, 2,403,513 bytes, set
2026-11-18; an Imgur direct `.gif` link under 5 MB:
above that Imgur turns it into MP4 and the link stops animating on Steam,
cf bulk_construction/store_assets/README.md). The opening is 280 characters
before the URL, so the URL stays out of the hover preview. Check after any
edit:

```bash
python - <<'EOF'
import pathlib, re
t = pathlib.Path("research_queue/STEAM_WORKSHOP_DESCRIPTION.bbcode").read_text(encoding="utf-8")
print(re.sub(r"\s+", " ", re.sub(r"\[[^\]]*\]", "", t)).strip()[:230])
EOF
```

## Gallery, in order

1. `research-queue.gif`: the demo (also inline in the description).
2. A mid-drag still (taken from the GIF's frames).
3. The prerequisite case, before and after (from the GIF's frames).
4. The "+N" pop-up with the arrow button's tooltip (one F12 screenshot).

## Recording the GIF (about 8 seconds)

Release build, game paused, Technology panel open. Queue, by shift-click:
Railways, Telephone, Camera, then Socialism (which queues Labor Movement
just before it, and Dialectics too if it is not researched), so the row
reads Railways, Telephone, Camera, Labor Movement, Socialism.

ScreenToGif, region over the queue row only: from just left of the first
queued tech to just right of the "+N" button, with a little margin above
and below (about 620 x 140 at 1920 x 1080). No map: animated map pixels do
not compress. 15 fps (a drag looks jerky at 10), cursor shown. Then:

1. drag Camera into the gap before Railways (one tech moves);
2. drag Socialism to the first slot: Labor Movement comes along, just in
   front of it (the differentiator);
3. pause one second on the result.

Then Remove Duplicates and export. The optimisation (no `disposal`, no
dither, crop) is in bulk_construction/store_assets/README.md.
