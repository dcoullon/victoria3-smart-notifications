import json
from analyse import turn_month
D = json.load(open("subsets.json")); ai = D["ai"]
rows = []
for h in (12, 24, 36, 60):
    obs = [e for e in ai if e["pts"][-1][0] >= h - 0.6]
    for run in (1, 3, 6):
        k = sum(1 for e in obs if (t := turn_month(e, run)) is not None and t <= h)
        st_ = sum(1 for e in obs if e["pts"][0][1] < 0)
        print(f"followed >= {h//12}y: {len(obs)} deals | losing in first month {st_} ({st_/len(obs):.0%}) | losing {run} mo running by {h//12}y: {k} ({k/len(obs):.0%})")
