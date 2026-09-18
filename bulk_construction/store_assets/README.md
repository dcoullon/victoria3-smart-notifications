Store assets — Workshop page and Reddit post
=============================================

**Not shipped to subscribers.** `package_release.py` copies only
`.metadata/`, `common/`, `events/`, `gui/`, `localization/` and
`thumbnail.png`, so this whole folder stays on the dev side. Built from the
user's own 2026-09-18 captures of the **release** build.

The numbered stills map onto the `>>> IMAGE n <<<` placeholders in
[../STEAM_WORKSHOP_DESCRIPTION.bbcode](../STEAM_WORKSHOP_DESCRIPTION.bbcode).
Host them somewhere (Imgur) and replace each placeholder with
`[img]<url>[/img]`. Steam renders description images at roughly 627px wide,
which is why nothing here is wider than ~605px — bigger only costs upload
time.

| file | what it proves | goes where |
|---|---|---|
| `build-all.gif` | the whole thing, in motion | IMAGE 1, above the Electricity section |
| `01-hero-panel.png` | what is being built, where, how many | IMAGE 2, above "How it works" |
| `04-filter-changes-count.png` | the filter decides: Domestic 47 vs Abroad 76 | IMAGE 3, under bullet 1 |
| `05-queue-result.png` | the result — two existing buildings, then the flood, page 1 of 5 | IMAGE 4, under bullet 3 |
| `06-japanese.png` | the eleven-language claim, in one glance | IMAGE 5, by the Languages section |
| `02-tooltip.png` | the mod says out loud which states it will skip | optional, in the no-cheat section |
| `03-location-filter.png` | the Location selector itself, Abroad active | optional, alternative to 04 |

## The first 230 characters are the hover preview

Steam shows the opening of the description when someone hovers a Workshop
item in a list, before they click. Roughly 230 characters, BBCode stripped.

That window is the whole pitch for anyone browsing, so the description opens
with one self-contained sentence covering what it does, the scale, and the
no-cheat point, and **nothing else is allowed into it**:

- no `[h1]` repeating the title — Steam already shows the title above, so it
  would spend the budget saying it twice;
- **no image in the first paragraph.** Stripping `[img]...[/img]` leaves the
  bare URL as text, so an image there puts `https://i.imgur.co` in the middle
  of the preview. IMAGE 1 sits after the first Electricity paragraph for
  exactly this reason, which also happens to be where it reads best — the
  problem is stated, then the GIF answers it.

Check it after any edit:

```bash
python - <<'EOF'
import pathlib, re
t = pathlib.Path("bulk_construction/STEAM_WORKSHOP_DESCRIPTION.bbcode").read_text(encoding="utf-8-sig")
print(re.sub(r"\s+", " ", re.sub(r"\[[^\]]*\]", "", t)).strip()[:230])
EOF
```

## The GIF

`build-all.gif` — 600x612, 85 frames, 8.9s, **1.3 MB**. Comfortably under
Imgur's 5MB threshold, above which it transcodes to MP4 and the direct `.gif`
link stops animating on Steam.

### The cut

The source sat on a static panel for 1.3s after the build had already
registered, so the gap between the rows flipping to `0+1` and the queue
appearing was 1.8s of nothing. Frames 23-35 are dropped and frame 22 is held
for 500ms instead: **the gap is now 0.7s**, with one deliberate beat on the
result rather than a stare.

The first attempt cut frames 17-35, which was wrong in a way worth recording
— the rows do not flip until frame ~21, so that splice landed *on* the moment
of change and removed the causal link between the click and the result. The
join has to sit after the thing the viewer needs to see, not across it.
Checked by rendering the frames either side: the surviving join is between
two identical frames, so it is invisible.

The queue paging that follows is still 6.2s. That is the payoff, but it is
the obvious next trim if a shorter loop is wanted.

`build-all-master.gif` is the untouched 1110x612 export, 14.8 MB. Kept only so
the optimised one can be rebuilt at different settings; it is 15 MB of repo,
so delete it once the store page is live if that bothers you.

### How 14.8 MB became 1.5 MB, in case this needs doing again

Almost all of it was one line. Pillow's `disposal=2` ("restore to background")
makes every frame a full redraw, which defeats the inter-frame compression a
mostly-static UI recording is ideal for. **Dropping `disposal` alone took an
identical encode from 13.7 MB to 1.4 MB.**

The other two, both much smaller:

- **Crop the map out.** The right ~45% of the frame was ocean and clouds,
  which animate, so those pixels changed every frame and compressed at zero
  ratio. Cropping to `x < 600` loses nothing: the construction panel and the
  queue panel both fit inside it (verified frame by frame).
- **Never dither.** `Image.NONE`, not Floyd-Steinberg. Dither noise is
  incompressible, and game UI is flat colour that does not need it.

With those, 256 colours at native resolution and every frame kept still lands
at 1.5 MB, so there was no need to trade away frame rate or sharpness at all.
Reach for quality reductions last, not first.

## Re-recording

`tools/shot.py` crops the user's in-game screenshots. The recording settings
that produced this: ScreenToGif, region over the panel, ~10fps, then the
editor's Remove Duplicates before export.
