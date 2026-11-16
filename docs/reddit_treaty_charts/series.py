import sys, collections, json
sys.path.insert(0, r"D:/Dropbox/_Damien/Perso et tech/Claude-code/vic3mods/tools")
import treaty_obs_report as T
from pathlib import Path
L = Path(r"C:/Users/damie/OneDrive/Documents/Paradox Interactive/Victoria 3/logs")
BASES = T.base_prices(T.GAME_ROOT); TQ = T.goods_table(T.GAME_ROOT, "traded_quantity")
SETS = {
 "spain": [L/"treaty_obs_spain/debug.log"] + sorted((L/"treaty_obs_spain2").rglob("debug*.log")),
 "ai": [L/"treaty_obs_archive/debug.log"] + T.log_files(L/"treaty_obs_rotated_1300") + [L/"treaty_obs_archive2/debug.log"],
}
def load(name):
    rows = [r for r in (T.parse_row(x) for x in T.read_lines(SETS[name])) if r and r["date"] and r["good"] in TQ]
    # save reloads replay dates: keep the last logged version of each (deal, date, kind)
    last = {}
    for r in rows: last[(r["src"],r["tgt"],r["good"],r.get("start"),r["date"],r["kind"])] = r
    rows = list(last.values())
    # lane MM demand split: per (src,tgt,date) among lane=1 rows
    grp = collections.defaultdict(list)
    for r in rows:
        if r.get("lane") == 1 and r["kind"] in ("MON","SIGN"):
            grp[(r["src"], r["tgt"], r["date"], r["kind"])].append(r)
    for g in grp.values():
        tot = sum(r["q"]/TQ[r["good"]] for r in g)
        lm = g[0].get("lanemm")
        for r in g:
            r["ship_units"] = (r["q"]/TQ[r["good"]]) / tot * lm if lm is not None and tot else None
            r["factor"] = lm/tot if lm is not None and tot else None
    return rows, T.build_deals(rows)

def net(r):
    if r.get("t_price") is None or r.get("s_price") is None: return None
    gross = r["q"] * (r["t_price"] - r["s_price"])
    if r.get("lane") == 1:
        if r.get("ship_units") is None or r.get("mm") is None: return None
        return gross - r["ship_units"] * r["mm"], gross
    return gross, gross

def main():
  pass
out = {}
for name in (SETS if __name__=="__main__" else []):
    rows, deals = load(name)
    # duplicate check
    c = collections.Counter((r["src"],r["tgt"],r["good"],r.get("start"),r["date"],r["kind"]) for r in rows)
    print(name, "dup (deal,date,kind) keys:", sum(v>1 for v in c.values()))
    res = []
    for d in deals:
        s = d["sign"]
        if not s: continue
        mons = [r for r in d["rows"] if r["kind"]=="MON" and r["date"] > s["date"]]
        if len(mons) < 6: continue
        good = d["key"][2]; q = s["q"]; base = BASES.get(good)
        p_s = T.rule(base, s["s_buy"] + q, s["s_sell"]); p_t = T.rule(base, s["t_buy"], s["t_sell"] + q)
        pred_gross = q * (p_t - p_s)
        # draft shipping: q/tq x factor x mm at signing; factor 1.0 or 1.6 by continent (draft rule),
        # actual lane factor from the first MON row with one
        if s.get("lane") == 1:
            fac_real = next((r["factor"] for r in mons if r.get("factor")), None)
            unit = q / TQ[good] * s["mm"]
            pred = {"f1.0": pred_gross - unit*1.0, "f1.6": pred_gross - unit*1.6,
                    "freal": pred_gross - unit*fac_real if fac_real else None}
        else:
            fac_real = 0
            pred = {"f1.0": pred_gross, "f1.6": pred_gross, "freal": pred_gross}
        pts = []
        for r in mons:
            n = net(r)
            if n is None: continue
            pts.append((round(T.months_between(s["date"], r["date"]), 2), round(n[0], 2), round(n[1], 2)))
        res.append({"src": d["key"][0], "tgt": d["key"][1], "good": good, "signed": s["date"].isoformat(),
                    "q": q, "lane": s.get("lane"), "factor": fac_real, "pred": pred,
                    "pred_gross": pred_gross, "sign_gross": q*(s["t_price"]-s["s_price"]), "pts": pts})
    out[name] = res
    print(name, "deals with >=6 MON after signing:", len(res), "| Spain-sent:", sum(x["src"]=="Spain" for x in res))
    for x in res if name=="spain" else []:
        if x["src"]=="Spain":
            print(" ", x["tgt"], x["good"], x["signed"], "q", x["q"], "lane", x["lane"], "fac", x["factor"] and round(x["factor"],2),
                  "pred", {k: v and round(v) for k,v in x["pred"].items()}, "first", x["pts"][0][:2], "n", len(x["pts"]), "last m", x["pts"][-1][0])
json.dump(out, open("series.json","w"))
