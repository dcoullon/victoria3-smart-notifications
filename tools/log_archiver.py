"""
Capture Victoria 3's debug.log continuously, so a long run does not lose its
own beginning.

The problem
-----------
The game rotates debug.log at ~512KB DURING a session, keeping only
debug.1.log..debug.5.log. That caps total capture at roughly 3MB per session.
The 2026-09-15 calibrate run produced 2.8MB for THREE in-game years and came
within a hair of overflowing; the planned ten-year measure run would produce
something like 9-10MB and would silently discard its earliest years. The loss
is invisible -- you get a complete-looking report of the wrong window. That
already happened once in miniature: the report read only debug.log and saw 762
of 7,842 lines.

The fix
-------
Every line the game writes passes through debug.log before rotation moves it,
so tailing that one file captures everything. Rotation shows up as the file
shrinking; we notice, rewind to 0, and keep going.

Run this BEFORE launching the game and leave it running:

    python tools/log_archiver.py

It writes an append-only `debug.log` into its own directory, which means every
existing tool works against it unchanged:

    python tools/scan_logs.py --census --logs-dir <the path it prints>

Stop it with Ctrl+C when you quit the game.
"""
import argparse
import sys
import time
from pathlib import Path

DEFAULT_SRC = (Path.home() / "Documents" / "Paradox Interactive" / "Victoria 3"
               / "logs" / "debug.log")
DEFAULT_OUT = (Path.home() / "Documents" / "Paradox Interactive" / "Victoria 3"
               / "logs" / "census_archive")


def archive(src: Path, out_dir: Path, poll: float, quiet: bool) -> int:
    out_dir.mkdir(parents=True, exist_ok=True)
    dest = out_dir / "debug.log"
    # Start clean: a stale archive silently merged with a new run would be
    # worse than no archive at all.
    if dest.exists():
        backup = out_dir / "debug.previous.log"
        dest.replace(backup)
        if not quiet:
            print(f"existing archive moved aside -> {backup.name}")

    print(f"source : {src}")
    print(f"archive: {dest}")
    print("Leave this running, launch the game, and Ctrl+C when you quit.\n")

    # Start at the CURRENT end of file, like `tail -f`. The debug.log sitting
    # there now is the previous session's leftover; archiving it would silently
    # merge two runs into one analysis. The game truncates the file when it
    # launches, which we detect as a rotation and follow from byte zero.
    try:
        pos = src.stat().st_size
    except FileNotFoundError:
        pos = 0
    if pos and not quiet:
        print(f"skipping {pos / 1024:.0f} KB of pre-existing log "
              f"(previous session); capturing from here on.\n")
    rotations = 0
    written = 0
    last_report = 0.0
    handle = dest.open("ab")
    try:
        while True:
            try:
                size = src.stat().st_size
            except FileNotFoundError:
                time.sleep(poll)
                continue

            if size < pos:
                # The game rotated (or truncated) the file. Everything before
                # this point is already in our archive; start reading the new
                # one from its beginning.
                rotations += 1
                pos = 0
                if not quiet:
                    print(f"  [rotation {rotations} detected -- continuing]")

            if size > pos:
                with src.open("rb") as f:
                    f.seek(pos)
                    chunk = f.read(size - pos)
                handle.write(chunk)
                handle.flush()
                written += len(chunk)
                pos = size

            now = time.time()
            if not quiet and now - last_report > 10:
                last_report = now
                print(f"  captured {written / 1024 / 1024:.1f} MB, "
                      f"{rotations} rotation(s)")

            time.sleep(poll)
    except KeyboardInterrupt:
        print()
    finally:
        handle.close()

    print(f"captured {written / 1024 / 1024:.2f} MB across {rotations} rotation(s)")
    print(f"archive: {dest}")
    if rotations == 0 and written:
        print("No rotation happened -- the plain logs folder would have been")
        print("enough this time, but the archive is still the complete record.")
    print()
    print("Read it with:")
    print(f"  python tools/scan_logs.py --census --logs-dir \"{out_dir}\"")
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--src", type=Path, default=DEFAULT_SRC,
                    help="the game's live debug.log")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT,
                    help="directory to write the append-only archive into")
    ap.add_argument("--poll", type=float, default=0.5,
                    help="seconds between checks (default 0.5; rotation took "
                         "1-2 minutes on the calibrate run, so this is ample)")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()
    return archive(args.src, args.out, args.poll, args.quiet)


if __name__ == "__main__":
    sys.exit(main())
