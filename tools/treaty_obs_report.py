"""
Read the Smart Treaties observer's ST_OBS| lines and test the draft's price
rule against what goods transfers actually did. Plan: docs/smart-treaties-next.md
section 1. The mod: smart_trade_observer/ (dev only, never uploaded).

    python tools/treaty_obs_report.py                     # live logs folder
    python tools/treaty_obs_report.py --logs-dir <dir>    # log_archiver's output
    python tools/treaty_obs_report.py --csv out.csv       # one row per deal x horizon
    python tools/treaty_obs_report.py --selftest          # synthetic data, no game

What it answers, per deal signed during the run (a SIGN line, then MON lines):
  1. The draft's first-week prediction: sender price with buy orders + q,
     receiver price with sell orders + q, through vanilla's price rule
     base x (1 + 0.75 x clamp((buy - sell) / min(buy, sell))). The same rule
     Market in tools/gen_smart_trade_gui.py uses.
  2. The real per-unit margin (receiver price - sender price) 1, 3, 6, 12 and
     24 months after signing, against that prediction.
  3. Whether the transfer adds trade or replaces it: change in the receiver's
     imports and sell orders, per unit transferred.
  4. Self-check: does the rule reproduce each logged price from its own logged
     orders? If not, every prediction below inherits the error.

Acceptance (plan): at least 30 deals with a SIGN row and at least 6 MON rows.

Numbers in the log are whatever the game's formatter printed, so a thousands
comma or a K/M suffix is parsed; the PROBE line shows which the game uses.
"""
import argparse
import csv
import re
import statistics
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from vic3_paths import VIC3_USER_DIR  # noqa: E402

GAME_ROOT = Path(r"C:\Program Files (x86)\Steam\steamapps\common\Victoria 3\game")
DEFAULT_LOGS = VIC3_USER_DIR / "logs"
HORIZONS = [1, 3, 6, 12, 24]   # months after signing
MIN_DEALS, MIN_MONTHS = 30, 6  # acceptance, from the plan
PRICE_RANGE = 0.75             # vanilla define, see gen_smart_trade_gui.f_imb

LINE_RE = re.compile(r"ST_OBS\|(.*?)\s*$")
MONTHS = {m: i for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july",
     "august", "september", "october", "november", "december"], 1)}


# ---------- parsing ----------

def num(text):
    """'1,234.5' -> 1234.5, '12.3K' -> 12300. None if unparseable."""
    t = text.strip().replace(",", "").replace(" ", "")
    mult = 1.0
    if t[-1:] in ("K", "k"):
        mult, t = 1e3, t[:-1]
    elif t[-1:] in ("M", "m"):
        mult, t = 1e6, t[:-1]
    try:
        return float(t) * mult
    except ValueError:
        return None


def parse_date(text):
    """'1837.7.7', '7 July 1837' or 'July 7, 1837'. None if none of those."""
    t = text.strip()
    m = re.fullmatch(r"(\d{3,4})\.(\d{1,2})\.(\d{1,2})", t)
    if m:
        return date(int(m[1]), int(m[2]), int(m[3]))
    m = re.fullmatch(r"(\d{1,2})\s+([A-Za-z]+),?\s+(\d{4})", t)
    if m and m[2].lower() in MONTHS:
        return date(int(m[3]), MONTHS[m[2].lower()], int(m[1]))
    m = re.fullmatch(r"([A-Za-z]+)\s+(\d{1,2}),?\s+(\d{4})", t)
    if m and m[1].lower() in MONTHS:
        return date(int(m[3]), MONTHS[m[1].lower()], int(m[2]))
    return None


MARKET_FIELDS = ["price", "buy", "sell", "imp", "exp", "prod", "cons"]


def parse_row(body):
    """One article line -> dict, or None if it is not a data line."""
    parts = body.split("|")
    if len(parts) < 6 or parts[0] not in ("SIGN", "MON", "END"):
        return None
    row = {"kind": parts[0], "date_raw": parts[1], "date": parse_date(parts[1]),
           "src": parts[2], "tgt": parts[3], "good": parts[4]}
    for p in parts[5:]:
        if "=" not in p:
            continue
        k, v = p.split("=", 1)
        if k == "start":
            row[k] = v.strip()
        elif k in ("s", "t"):
            vals = [num(x) for x in v.split(";")]
            for name, val in zip(MARKET_FIELDS, vals):
                row[f"{k}_{name}"] = val
        else:
            row[k] = num(v)
    return row


def read_lines(paths):
    seen, out = set(), []
    for p in paths:
        with open(p, encoding="utf-8", errors="replace") as f:
            for line in f:
                m = LINE_RE.search(line)
                if m and m[1] not in seen:
                    seen.add(m[1])
                    out.append(m[1])
    return out


def log_files(logs_dir):
    files = sorted(logs_dir.glob("debug.[0-9].log"), reverse=True)  # oldest first
    files += [logs_dir / "debug.log"]
    return [f for f in files if f.exists()]


# ---------- game data ----------

def goods_table(game_root, field):
    """Goods key -> a numeric field of 00_goods.txt ("cost" is the base
    price, "traded_quantity" the units one merchant marine carries)."""
    out = {}
    text = (game_root / "common/goods/00_goods.txt").read_text(encoding="utf-8-sig")
    for m in re.finditer(r"^(\w+)\s*=\s*\{(.*?)^\}", text, re.M | re.S):
        c = re.search(rf"\b{field}\s*=\s*([\d.]+)", m[2])
        if c:
            out[m[1]] = float(c[1])
    return out


def base_prices(game_root):
    return goods_table(game_root, "cost")


def rule(base, buy, sell):
    """Vanilla price rule (confirmed in game 2026-10-03)."""
    lo = max(min(buy, sell), 0.01)
    r = max(-1.0, min(1.0, (buy - sell) / lo))
    return base * (1 + PRICE_RANGE * r)


# ---------- deals ----------

def months_between(a, b):
    return (b.year - a.year) * 12 + (b.month - a.month) + (b.day - a.day) / 30.0


def build_deals(rows):
    """Chain rows per (sender, receiver, good, treaty start date). A SIGN
    starts a deal; MON rows join the open deal; END or a gap over 45 days
    closes it. MON rows with no open deal start an unsigned one (a treaty
    older than the run). Historical treaties also fire SIGN on 1 January 1836,
    before any market has orders, so those count as unsigned."""
    deals, open_ = [], {}
    for r in sorted((r for r in rows if r["date"]), key=lambda r: r["date"]):
        key = (r["src"], r["tgt"], r["good"], r.get("start", ""))
        d = open_.get(key)
        if d and (r["date"] - d["rows"][-1]["date"]).days > 45:
            open_.pop(key)
            d = None
        if r["kind"] == "SIGN" and r.get("hist"):
            if d is None:
                d = {"key": key, "sign": None, "rows": []}
                deals.append(d)
                open_[key] = d
            d["rows"].append(r)
        elif r["kind"] == "SIGN":
            d = {"key": key, "sign": r, "rows": [r]}
            deals.append(d)
            open_[key] = d
        elif r["kind"] == "MON":
            if d is None:
                d = {"key": key, "sign": None, "rows": []}
                deals.append(d)
                open_[key] = d
            d["rows"].append(r)
        elif r["kind"] == "END" and d:
            d["end"] = r
            open_.pop(key, None)
    return deals


def at_horizon(deal, months):
    """The MON row closest to `months` after signing, within half a month."""
    t0 = deal["sign"]["date"]
    best = None
    for r in deal["rows"]:
        if r["kind"] != "MON":
            continue
        dm = abs(months_between(t0, r["date"]) - months)
        if dm <= 0.6 and (best is None or dm < best[0]):
            best = (dm, r)
    return best[1] if best else None


def analyse(deals, bases):
    signed = [d for d in deals if d["sign"]]
    usable = [d for d in signed if sum(r["kind"] == "MON" for r in d["rows"]) >= MIN_MONTHS]
    out = []
    for d in signed:
        s = d["sign"]
        base = bases.get(d["key"][2])
        q = s.get("q")
        if base is None or q is None or None in (s.get("s_buy"), s.get("s_sell"), s.get("t_buy"), s.get("t_sell")):
            continue
        p_s = rule(base, s["s_buy"] + q, s["s_sell"])
        p_t = rule(base, s["t_buy"], s["t_sell"] + q)
        for h in HORIZONS:
            r = at_horizon(d, h)
            if not r or r.get("t_price") is None or r.get("s_price") is None:
                continue
            out.append({
                "sender": d["key"][0], "receiver": d["key"][1], "good": d["key"][2],
                "signed": s["date_raw"], "q": q, "lane": s.get("lane"), "months": h,
                "margin_sign": s["t_price"] - s["s_price"],
                "margin_pred": p_t - p_s,
                "margin_real": r["t_price"] - r["s_price"],
                "t_sell_delta_per_q": (r["t_sell"] - s["t_sell"]) / q if q else None,
                # A market's imports/exports INCLUDE the treaty's own goods
                # (first v0.02 run: a lone 20-wine transfer showed exactly 20
                # imported and 20 exported). So other trade = logged - q once
                # the transfer runs; at SIGN it does not run yet.
                "t_imp_delta_per_q": (r["t_imp"] - q - s["t_imp"]) / q if q and r.get("t_imp") is not None and s.get("t_imp") is not None else None,
                "s_exp_delta_per_q": (r["s_exp"] - q - s["s_exp"]) / q if q and r.get("s_exp") is not None and s.get("s_exp") is not None else None,
            })
    return signed, usable, out


def rule_selfcheck(rows, bases):
    errs = []
    for r in rows:
        base = bases.get(r["good"])
        for side in ("s", "t"):
            p, b, s = r.get(f"{side}_price"), r.get(f"{side}_buy"), r.get(f"{side}_sell")
            if base and p and b is not None and s is not None and p > 0:
                errs.append(abs(rule(base, b, s) - p) / p)
    return errs


def route_factors(rows, traded):
    """Real lane cost against the draft's x1.00 estimate, per treaty lane and
    month. Draft: q / traded_quantity merchant marine per article, x1.25 for
    sea routes. Real: the lane's merchant marine demand, shared by every lane
    article the same sender has in that treaty (as smart_trade's ST_A_SHIP
    splits it), so the factor is lanemm / sum(q / traded_quantity)."""
    groups = {}
    for r in rows:
        if r["kind"] != "MON" or not r.get("lane") or r.get("lanemm") is None:
            continue
        tq = traded.get(r["good"])
        if not tq or not r.get("q"):
            continue
        g = groups.setdefault((r["date"], r["src"], r["tgt"], r.get("start", "")), [0.0, set()])
        g[0] += r["q"] / tq
        g[1].add(r["lanemm"])
    return [next(iter(lm)) / units for units, lm in groups.values() if units > 0 and len(lm) == 1]


def q(values, p):
    v = sorted(values)
    return v[min(len(v) - 1, int(p * len(v)))] if v else None


def fmt(x, nd=2):
    return "n/a" if x is None else f"{x:.{nd}f}"


def report(lines, bases, csv_path=None, traded=None):
    probes = [l for l in lines if l.startswith(("PROBE", "START"))]
    rows = [r for r in (parse_row(l) for l in lines) if r]
    undated = sum(1 for r in rows if r["date"] is None)
    print(f"ST_OBS lines: {len(lines)}, article rows: {len(rows)}, undated: {undated}")
    if rows and undated == len(rows):
        print("  every date failed to parse -- the date tap is broken, see the raw line:")
        print("  ", lines[0][:200])
    for p in probes:
        print("  " + p[:300])
    blank = sum(1 for r in rows if not (r["src"] and r["tgt"] and r["good"]))
    if blank:
        print(f"  {blank} rows with an empty sender, receiver or goods key: the name tap is broken")
    missing = sorted({r["good"] for r in rows} - set(bases))
    if missing:
        print(f"  goods keys with no base price in 00_goods.txt: {missing}")
    if traded:
        rf = route_factors(rows, traded)
        if rf:
            print(f"\nRoute factor (real lane cost / draft x1.00 estimate), n={len(rf)} lane-months: "
                  f"median {fmt(statistics.median(rf))}, 10th pct {fmt(q(rf, 0.1))}, "
                  f"90th pct {fmt(q(rf, 0.9))}. The draft assumes 1.25.")

    errs = rule_selfcheck(rows, bases)
    if errs:
        print(f"\nPrice rule reproduces logged price: median error {fmt(100 * statistics.median(errs))}%, "
              f"90th pct {fmt(100 * q(errs, 0.9))}%, n={len(errs)}")

    deals = build_deals(rows)
    signed, usable, out = analyse(deals, bases)
    unsigned = len(deals) - len(signed)
    print(f"\nDeals: {len(deals)} ({len(signed)} signed during the run, {unsigned} older)")
    verdict = "MET" if len(usable) >= MIN_DEALS else "NOT MET"
    print(f"Acceptance (>= {MIN_DEALS} signed deals with >= {MIN_MONTHS} monthly rows): "
          f"{len(usable)} -> {verdict}")

    print("\nMargin per unit, draft prediction vs real (receiver price - sender price):")
    print(f"  {'months':>6} {'n':>4} {'median real-pred':>17} {'|err| median':>13} "
          f"{'sign agrees':>12} {'recv sell +/q':>14} {'oth imp +/q':>13} {'oth exp +/q':>13}")
    for h in HORIZONS:
        sub = [o for o in out if o["months"] == h]
        if not sub:
            print(f"  {h:>6} {0:>4}")
            continue
        diff = [o["margin_real"] - o["margin_pred"] for o in sub]
        agree = sum((o["margin_real"] > 0) == (o["margin_pred"] > 0) for o in sub) / len(sub)
        med = lambda k: statistics.median([o[k] for o in sub if o[k] is not None]) if any(o[k] is not None for o in sub) else None
        print(f"  {h:>6} {len(sub):>4} {fmt(statistics.median(diff)):>17} "
              f"{fmt(statistics.median([abs(x) for x in diff])):>13} {fmt(100 * agree, 0) + '%':>12} "
              f"{fmt(med('t_sell_delta_per_q')):>14} {fmt(med('t_imp_delta_per_q')):>13} {fmt(med('s_exp_delta_per_q')):>13}")
    print("\n  oth imp +/q: change in the receiver's OTHER imports (treaty goods taken out) per unit sent."
          "\n  Near -1: the transfer replaced trade-center imports (treaty profit moved, not added)."
          " Near 0: it added trade. oth exp +/q: the same for the sender's other exports.")

    if csv_path and out:
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(out[0]))
            w.writeheader()
            w.writerows(out)
        print(f"\nwrote {len(out)} rows to {csv_path}")
    return len(usable)


# ---------- self-test ----------

def selftest():
    """Synthetic run: 31 deals, the receiver's imports fall by exactly q, the
    margin lands where the rule says, every lane runs at x1.30. Checks parsing,
    chaining and maths."""
    bases = {"copper": 50.0, "coffee": 30.0}
    traded = {"copper": 5.0, "coffee": 5.0}
    lines = ["START|January 1, 1836|observer v0.02",
             # a historical treaty: SIGN at game start, must not count as signed
             "SIGN|January 1, 1836|Old|Treaty|coffee|start=1 January 1830|q=5|lane=0|bind=3650|left=3000|inscope=1|hist=1|s=1;0;0;0;0;0;0|t=1;0;0;0;0;0;0|mm=1"]
    for i in range(31):
        good = "copper" if i % 2 else "coffee"
        base, qn = bases[good], 10 + i
        sb, ss, tb, ts, ti = 100.0, 140.0, 120.0, 60.0, 40.0
        ps, pt = rule(base, sb, ss), rule(base, tb, ts)
        y = 1837 + i // 12
        m = i % 12 + 1
        st = f"1 {list(MONTHS)[m - 1].title()} {y}"
        lanemm = 1.3 * qn / traded[good]
        lines.append(f"SIGN|{y}.{m}.1|Land{i}|Other{i}|{good}|start={st}|q={qn:.2f}|lane=1|bind=1825|left=1825|inscope=1|hist=0|"
                     f"s={ps:.2f};{sb:.2f};{ss:.2f};0;0;0;0|t={pt:.2f};{tb:.2f};{ts:.2f};{ti:.2f};0;0;0|mm=40|lanemm={lanemm:.2f}")
        ps2, pt2 = rule(base, sb + qn, ss), rule(base, tb, ts + qn)
        for k in range(1, 26):
            yy, mm = y + (m - 1 + k) // 12, (m - 1 + k) % 12 + 1
            lines.append(f"MON|{yy}.{mm}.1|Land{i}|Other{i}|{good}|start={st}|q={qn:,.2f}|lane=1|bind=1825|left=1000|inscope=1|hist=0|"
                         f"s={ps2:.2f};{sb + qn:.2f};{ss:.2f};0;{qn:.2f};0;0|t={pt2:.2f};{tb:.2f};{ts + qn:.2f};{ti:.2f};0;0;0|mm=40|lanemm={lanemm:.2f}")
    lines.append("MON|February 1, 1836|Old|Treaty|coffee|start=1 January 1830|q=5|lane=0|bind=3650|left=2970|inscope=1|hist=1|s=1;1;1;1;1;1;1|t=1;1;1;1;1;1;1|mm=1")
    assert num("1,234.5") == 1234.5 and num("12.3K") == 12300 and num("x") is None
    assert parse_date("7 July 1837") == date(1837, 7, 7) == parse_date("1837.7.7") == parse_date("July 7, 1837")
    n = report(lines, bases, traded=traded)
    assert n == 31, n
    rf = route_factors([r for r in (parse_row(l) for l in lines) if r], traded)
    assert rf and all(abs(x - 1.3) < 0.01 for x in rf), rf[:3]
    deals = build_deals([r for r in (parse_row(l) for l in lines) if r])
    _, _, out = analyse(deals, bases)
    assert all(abs(o["margin_real"] - o["margin_pred"]) < 0.02 for o in out)
    assert all(abs(o["t_imp_delta_per_q"] + 1) < 1e-6 for o in out)
    print("\nselftest OK")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--logs-dir", type=Path, default=DEFAULT_LOGS)
    ap.add_argument("--csv", type=Path)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        selftest()
        return
    files = log_files(a.logs_dir)
    if not files:
        sys.exit(f"no debug.log in {a.logs_dir}")
    lines = read_lines(files)
    if not lines:
        sys.exit(f"no ST_OBS lines in {[f.name for f in files]}: is the observer mod in the playset?")
    # Only the latest game: an archive can hold an earlier, abandoned session
    # (the v0.01 run whose names printed empty, 2026-11-10).
    starts = [i for i, l in enumerate(lines) if l.startswith("START|")]
    if len(starts) > 1:
        print(f"{len(starts)} game starts in the logs; reading only the last ({lines[starts[-1]]})")
        lines = lines[starts[-1]:]
    report(lines, base_prices(GAME_ROOT), a.csv, goods_table(GAME_ROOT, "traded_quantity"))


if __name__ == "__main__":
    main()
