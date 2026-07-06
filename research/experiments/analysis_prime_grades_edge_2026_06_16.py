"""Edge measure of Prime's own A_SETUP/WATCH signals (NOT a harness test).
Gate apprentissage just crossed 500 (975/500). Report-level analysis only:
realized ret signed by the signalled direction, with bootstrap-by-day IC.
"""
import os, random
import pandas as pd

EXP = "/Users/sam/trading/feature_exports"
feat = pd.read_parquet(os.path.join(EXP, "features.parquet"))
out = pd.read_parquet(os.path.join(EXP, "outcomes.parquet"))
print("features cols:", list(feat.columns))
print("outcomes cols:", list(out.columns))

df = feat.merge(out, on=["ts", "asset"], how="inner")
# keep only complete, non-MIXED outcomes
if "outcome_quality" in df.columns:
    df = df[df["outcome_quality"] != "MIXED"]
df = df.dropna(subset=["ret_4h"])
print("merged rows with ret_4h:", len(df))
print("grades:", df["grade"].value_counts().to_dict())


def signed(row, col):
    d = str(row.get("direction", "")).upper()
    r = row[col]
    if d.startswith("LONG"):
        return r
    if d.startswith("SHORT"):
        return -r
    return None


def boot_ci(vals, days, iters=2000, seed=42):
    blocks = {}
    for v, d in zip(vals, days):
        blocks.setdefault(d, []).append(v)
    bl = list(blocks.values())
    if len(bl) < 2:
        return None
    rng = random.Random(seed)
    means = []
    for _ in range(iters):
        s = []
        for _ in range(len(bl)):
            s.extend(rng.choice(bl))
        means.append(sum(s) / len(s))
    means.sort()
    return (round(means[int(0.025 * iters)], 4), round(means[int(0.975 * iters) - 1], 4))


df["day"] = pd.to_datetime(df["ts"], unit="s").dt.strftime("%Y-%m-%d")
for grade in ["A_SETUP", "WATCH"]:
    for col in ["ret_1h", "ret_4h"]:
        sub = df[df["grade"] == grade].copy()
        sub["edge"] = sub.apply(lambda r: signed(r, col), axis=1)
        sub = sub.dropna(subset=["edge"])
        if len(sub) == 0:
            continue
        mean = sub["edge"].mean()
        ci = boot_ci(sub["edge"].tolist(), sub["day"].tolist())
        wr = (sub["edge"] > 0).mean() * 100
        print(f"  {grade:8} {col}: n={len(sub):4d} edge_mean={mean:+.4f}% "
              f"WR={wr:.1f}% IC95_bootjours={ci} "
              f"dir={sub['direction'].value_counts().to_dict()}")
