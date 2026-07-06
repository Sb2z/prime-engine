"""Reconduction edge signaux Prime CONDITIONNE au regime (backlog #1, report-only).
Gate 1324/500. NON un test harness. ret signe par direction signalee, IC boot-jours.
Chemin feature_exports corrige -> racine projet (pas research/)."""
import os, random
import pandas as pd
ROOT=os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
EXP=os.path.join(ROOT,"feature_exports")
feat=pd.read_parquet(os.path.join(EXP,"features.parquet"))
out=pd.read_parquet(os.path.join(EXP,"outcomes.parquet"))
df=feat.merge(out,on=["ts","asset"],how="inner")
if "outcome_quality" in df.columns: df=df[df["outcome_quality"]!="MIXED"]
df=df.dropna(subset=["ret_4h"])
df["day"]=pd.to_datetime(df["ts"],unit="s").dt.strftime("%Y-%m-%d")
def signed(row,col):
    d=str(row.get("direction","")).upper(); r=row[col]
    if d.startswith("LONG"): return r
    if d.startswith("SHORT"): return -r
    return None
def boot(vals,days,iters=2000,seed=42):
    b={}
    for v,d in zip(vals,days): b.setdefault(d,[]).append(v)
    bl=list(b.values())
    if len(bl)<2: return None
    rng=random.Random(seed); m=[]
    for _ in range(iters):
        s=[]
        for _ in range(len(bl)): s.extend(rng.choice(bl))
        m.append(sum(s)/len(s))
    m.sort(); return (round(m[int(.025*iters)],4),round(m[int(.975*iters)-1],4))
print("merged non-MIXED w/ ret_4h:",len(df),"| n days:",df['day'].nunique())
print("grades:",df["grade"].value_counts().to_dict())
print("=== overall by grade ===")
for g in ["A_SETUP","WATCH"]:
    for col in ["ret_1h","ret_4h"]:
        sub=df[df["grade"]==g].copy()
        sub["e"]=sub.apply(lambda r:signed(r,col),axis=1); sub=sub.dropna(subset=["e"])
        if not len(sub): continue
        ci=boot(sub["e"].tolist(),sub["day"].tolist())
        wr=(sub["e"]>0).mean()*100
        print(f"  {g:8} {col}: n={len(sub):4d} njours={sub['day'].nunique():3d} edge={sub['e'].mean():+.4f}% WR={wr:.1f}% IC={ci} dir={sub['direction'].value_counts().to_dict()}")
print("=== A_SETUP ret_4h conditioned on regime ===")
a=df[df["grade"]=="A_SETUP"].copy()
a["e"]=a.apply(lambda r:signed(r,"ret_4h"),axis=1); a=a.dropna(subset=["e"])
for reg,sub in a.groupby("regime"):
    ci=boot(sub["e"].tolist(),sub["day"].tolist()) if len(sub)>=5 else None
    print(f"  {str(reg):22} n={len(sub):4d} njours={sub['day'].nunique():3d} edge={sub['e'].mean():+.4f}% WR={(sub['e']>0).mean()*100:.0f}% IC={ci}")
