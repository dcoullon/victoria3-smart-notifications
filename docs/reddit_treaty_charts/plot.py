import json
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from analyse import turn_month
D = json.load(open("subsets.json"))
SURF, INK, INK2, GRID, BLUE, GRAY = "#fcfcfb", "#0b0b0b", "#52514e", "#e6e5e0", "#2a78d6", "#a9a8a2"
def style(ax):
    ax.set_facecolor(SURF); ax.grid(axis="y", color=GRID, lw=0.8); ax.set_axisbelow(True)
    for sp in ["top", "right"]: ax.spines[sp].set_visible(False)
    for sp in ["left", "bottom"]: ax.spines[sp].set_color(GRID)
    ax.tick_params(colors=INK2, labelsize=9)

# ---- 1) Spain, predicted-positive only
sp = [e for e in D["spain"] if e["pred"]["draft"] > 0]
fig, ax = plt.subplots(figsize=(10, 5.6), facecolor=SURF); style(ax)
for e in sp:
    xs = [p[0] / 12 for p in e["pts"]]; ys = [p[1] for p in e["pts"]]
    ax.plot(xs, ys, color=GRAY, lw=1.2, marker="o" if len(xs) < 3 else None, ms=3)
ax.axhline(0, color=INK2, lw=0.8)
lab = {("hardwood", "Great Qing"): "hardwood to Great Qing", ("tobacco", "France"): "tobacco to France",
       ("clippers", "Siam"): "clippers to Siam"}
for e in sp:
    k = (e["good"], e["tgt"])
    if k in lab and not (k == ("silk", "France") and e["signed"] > "1850"):
        m, n = e["pts"][-1][0], e["pts"][-1][1]
        left = k == ("clippers", "Siam")
        ax.annotate(lab[k], (m / 12, n), xytext=(6 if left else -4, -3 if left else 6), textcoords="offset points",
                    ha="left" if left else "right", va="center" if left else "baseline", fontsize=8.5, color=INK2)
ax.set_xlabel("Years since signing", color=INK2, fontsize=9)
ax.set_ylabel("Weekly net to Spain (£)", color=INK2, fontsize=9)
fig.suptitle("My Spain campaign: weekly net of each goods transfer after signing", x=0.01, ha="left", fontsize=13.5, color=INK, fontweight="bold")
fig.text(0.01, 0.905, f"{len(sp)} deals Spain sent that Smart Treaties predicted profitable. One line per deal; sale price minus home price, minus shipping.\n"
         "Monthly snapshots from the observer log, 1836 to 1867.", fontsize=9, color=INK2, va="top")
fig.tight_layout(rect=(0, 0, 1, 0.84)); fig.savefig("spain_predicted_positive.png", dpi=150, facecolor=SURF); plt.close(fig)

# ---- 2) AI: share losing money
ai = D["ai"]; n = len(ai)
def obs(h): return [e for e in ai if e["pts"][-1][0] >= h - 0.6]
def lost_by(h): o = obs(h); return sum(1 for e in o if (t := turn_month(e, 3)) is not None and t <= h), len(o)
bars = [("Predicted to lose money at signing", sum(e["pred"]["draft"] <= 0 for e in ai), n),
        ("Losing money in its first month", sum(e["pts"][0][1] < 0 for e in ai), n),
        ("Lost money 3 months running\nwithin 1 year", *lost_by(12)),
        ("Lost money 3 months running\nwithin 5 years", *lost_by(60))]
print([(b[0].replace("\n", " "), b[1], b[2], f"{b[1]/b[2]:.1%}") for b in bars])
fig, ax = plt.subplots(figsize=(10, 4.6), facecolor=SURF); style(ax); ax.grid(False); ax.grid(axis="x", color=GRID, lw=0.8)
ys = list(range(len(bars)))[::-1]
ax.barh(ys, [k / m * 100 for _, k, m in bars], color=BLUE, height=0.55)
for y, (t, k, m) in zip(ys, bars):
    ax.text(k / m * 100 + 1, y, f"{k/m:.0%}  ({k} of {m})", va="center", fontsize=9.5, color=INK)
ax.set_yticks(ys); ax.set_yticklabels([b[0] for b in bars], fontsize=9.5, color=INK)
ax.set_xlim(0, 115); ax.set_xticks([0, 25, 50, 75, 100]); ax.set_xticklabels(["0%", "25%", "50%", "75%", "100%"])
fig.suptitle("AI-only game: how often the AI's goods transfers lose money for the sender", x=0.01, ha="left", fontsize=13.5, color=INK, fontweight="bold")
fig.text(0.01, 0.9, f"{n} goods transfers signed between AI countries, observer game 1836 to 1909. Later bars count only deals still running\n"
         "1 or 5 years after signing. Net = sale price minus home price, minus shipping.", fontsize=9, color=INK2, va="top")
fig.tight_layout(rect=(0, 0, 1, 0.8)); fig.savefig("ai_losing_share.png", dpi=150, facecolor=SURF); plt.close(fig)
