"""Build one record per signed deal, for both data sets, with any number of MON rows."""
import sys, json
import os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import series as S
T = S.T
def draft_factor(real):
    # ASSUMPTION: the draft used x1.6 for other-continent routes and x1.0 within a continent;
    # the log has no continent, so map by the lane's measured factor (measured: 1.00 same continent, 1.52-1.62 others)
    return 1.6 if real > 1.25 else 1.0
out = {}
for name in S.SETS:
    rows, deals = S.load(name)
    res = []
    for d in deals:
        s = d["sign"]
        if not s or s.get("hist"): continue
        mons = [r for r in d["rows"] if r["kind"] == "MON" and r["date"] > s["date"]]
        good = d["key"][2]; q = s["q"]
        p_s = T.rule(S.BASES[good], s["s_buy"] + q, s["s_sell"]); p_t = T.rule(S.BASES[good], s["t_buy"], s["t_sell"] + q)
        pg = q * (p_t - p_s)
        pts = [(T.months_between(s["date"], r["date"]), *S.net(r)) for r in mons if S.net(r)]
        if s.get("lane") == 1:
            fac = next((r["factor"] for r in mons if r.get("factor")), None)
            unit = q / S.TQ[good] * s["mm"]
            pred = {"real": pg - unit * fac if fac else None, "draft": pg - unit * draft_factor(fac) if fac else None,
                    "f1.0": pg - unit, "f1.6": pg - unit * 1.6}
        else:
            fac = 0; pred = {k: pg for k in ("real", "draft", "f1.0", "f1.6")}
        res.append({"src": d["key"][0], "tgt": d["key"][1], "good": good, "signed": s["date"].isoformat(),
                    "q": q, "lane": s.get("lane"), "factor": fac, "pred": pred, "pts": pts,
                    "ended": "end" in d})
    out[name] = res
    print(name, "signed non-historical:", len(res), "with >=1 MON:", sum(bool(e["pts"]) for e in res),
          ">=6 MON:", sum(len(e["pts"]) >= 6 for e in res), "ended by END row:", sum(e["ended"] for e in res))
json.dump(out, open("deals.json", "w"))
