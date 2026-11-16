import json, statistics as st
D = json.load(open("deals.json"))
spain = [e for e in D["spain"] if e["src"] == "Spain" and e["pts"]]
ai = [e for e in D["ai"] if e["pts"]]
print("Spain-sent with >=1 MON:", len(spain), "| draft pred > 0:", sum(e["pred"]["draft"] > 0 for e in spain))
print("AI with >=1 MON:", len(ai))

def at(e, m):
    c = [p for p in e["pts"] if abs(p[0] - m) <= 0.6]
    return min(c, key=lambda p: abs(p[0] - m))[1] if c else None

def turn_month(e, run):
    """months since signing when net first starts a run of `run` consecutive negative snapshots; None if never."""
    p = e["pts"]
    for i in range(len(p) - run + 1):
        if all(x[1] < 0 for x in p[i:i + run]): return p[i][0]
    return None

# ---- 2) AI: losing at start, then turning negative (Kaplan-Meier, censored at last snapshot)
def km(deals, run, horizons):
    ev = []
    for e in deals:
        t = turn_month(e, run)
        # a run of `run` snapshots needs `run` months to be seen: censor at last snapshot minus run-1
        ev.append((t, True) if t is not None else (e["pts"][-1][0] - (run - 1), False))
    out, surv = {}, 1.0
    times = sorted(set(t for t, x in ev if x))
    hz = list(horizons); res = {}
    for t in times:
        at_risk = sum(1 for u, x in ev if u >= t)
        d = sum(1 for u, x in ev if x and u == t)
        while hz and hz[0] < t:
            h = hz.pop(0); res[h] = (1 - surv, sum(1 for u, x in ev if u >= h))
        surv *= 1 - d / at_risk
    for h in hz: res[h] = (1 - surv, sum(1 for u, x in ev if u >= h))
    return res

n = len(ai)
pred_neg = sum(e["pred"]["draft"] <= 0 for e in ai)
pred_neg_lo = sum(e["pred"]["f1.0"] <= 0 for e in ai); pred_neg_hi = sum(e["pred"]["f1.6"] <= 0 for e in ai)
first_neg = sum(e["pts"][0][1] < 0 for e in ai)
print(f"\nAI deals: {n}. Predicted to lose at signing (draft factor): {pred_neg} = {pred_neg/n:.0%}"
      f"  [shipping x1.0 for every lane: {pred_neg_lo/n:.0%}, x1.6: {pred_neg_hi/n:.0%}]")
print(f"Losing in the first month observed: {first_neg} = {first_neg/n:.0%}; first snapshot at median {st.median(e['pts'][0][0] for e in ai):.2f} months")
for run in (1, 3, 6):
    r = km(ai, run, [0.01, 12, 24, 36, 60])
    print(f"  ever losing for {run} month(s) in a row, cumulative share (KM) by: " +
          ", ".join(f"{h/12:.0f}y {v:.0%} (at risk {k})" if h > 1 else f"start {v:.0%}" for h, (v, k) in r.items()))
pos_start = [e for e in ai if e["pts"][0][1] >= 0]
r = km(pos_start, 3, [12, 36, 60])
print(f"  of the {len(pos_start)} that started profitable, losing 3 months running by: " + ", ".join(f"{h/12:.0f}y {v:.0%} (at risk {k})" for h, (v, k) in r.items()))
print("  AI deals with an END row:", sum(e["ended"] for e in ai), "| median net over life < 0:", sum(st.median(p[1] for p in e["pts"]) < 0 for e in ai))

# ---- 3) accuracy
def acc(deals, key, label):
    print(f"\n{label} (prediction: {key})")
    print("  months | pred+ n, still + | pred- n, still - | pred+ : real/pred median [IQR], within +-25%, +-50%")
    for m in (1, 3, 6, 12, 24):
        pp = [(e["pred"][key], at(e, m)) for e in deals if e["pred"][key] is not None and at(e, m) is not None]
        pos = [(p, r) for p, r in pp if p > 0]; neg = [(p, r) for p, r in pp if p <= 0]
        rat = sorted(r / p for p, r in pos)
        s = f"  {m:>6} | {len(pos):>3}, {sum(r>0 for p,r in pos)/len(pos):>4.0%}" if pos else f"  {m:>6} |   -"
        s += f"     | {len(neg):>3}, {sum(r<=0 for p,r in neg)/len(neg):>4.0%}" if neg else "     |   -      "
        if len(rat) >= 4:
            qs = st.quantiles(rat, n=4)
            s += f"     | {st.median(rat):.2f} [{qs[0]:.2f}, {qs[2]:.2f}], {sum(abs(x-1)<=.25 for x in rat)/len(rat):.0%}, {sum(abs(x-1)<=.5 for x in rat)/len(rat):.0%}"
        print(s)
for key in ("draft", "real", "f1.0", "f1.6"):
    acc(spain + ai, key, "BOTH RUNS POOLED")
acc(spain, "draft", "SPAIN ONLY"); acc(ai, "draft", "AI ONLY")
json.dump({"spain": spain, "ai": ai}, open("subsets.json", "w"))
