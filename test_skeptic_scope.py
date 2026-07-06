import json, statistics

def load(p):
    with open(p) as f:
        return json.load(f)

day2 = load("C:/Users/sam/trading/user_trades_day2.json")
imp  = load("C:/Users/sam/trading/user_trades_import.json")

# Dedup by (open, inst, dir, entry)
seen = {}
for t in day2 + imp:
    k = (t["open"], t["inst"], t["dir"], t["entry"])
    if k not in seen:
        seen[k] = t
trades = list(seen.values())
print("Raw day2:", len(day2), "Raw imp:", len(imp), "Total raw:", len(day2)+len(imp))
print("Deduped distinct trades:", len(trades))

def agg(ts):
    n=len(ts); pnl=sum(t["pnl_usd"] for t in ts)
    wins=sum(1 for t in ts if t["pnl_usd"]>0)
    wr = wins/n*100 if n else 0
    return n, pnl, wr

# Instrument grouping: GOLD = XAU. US500 = SPX500. Indiv stocks = everything else mapped
def fam(inst):
    if inst in ("XAU","GOLD"): return "GOLD"
    if inst in ("SPX500","US500"): return "US500"
    return "OTHER:"+inst

from collections import defaultdict
byfam=defaultdict(list)
for t in trades:
    byfam[fam(t["inst"])].append(t)

print("\n== Per-family (deduped) ==")
total_all=0
for k in sorted(byfam):
    n,pnl,wr=agg(byfam[k]); total_all+=pnl
    print(f"{k:14s} n={n:3d} pnl={pnl:+8.2f} wr={wr:4.1f}%")
print(f"{'TOTAL':14s} pnl={total_all:+8.2f}")

# Scope restriction: GOLD + US500 only
restricted=[t for t in trades if fam(t["inst"]) in ("GOLD","US500")]
removed=[t for t in trades if fam(t["inst"]) not in ("GOLD","US500")]
n_r,pnl_r,wr_r=agg(restricted)
n_x,pnl_x,wr_x=agg(removed)
n_a,pnl_a,wr_a=agg(trades)
print(f"\nFULL      n={n_a} pnl={pnl_a:+.2f}")
print(f"RESTRICTED(GOLD+US500) n={n_r} pnl={pnl_r:+.2f}  delta={pnl_r-pnl_a:+.2f}")
print(f"REMOVED   n={n_x} pnl={pnl_x:+.2f} wr={wr_x:.1f}%")

# Decompose REMOVED: SPX vs stocks
spx=[t for t in removed if fam(t["inst"])=="US500"]  # actually US500 kept; removed is OTHER only
others=removed
print("\n== REMOVED breakdown (the 'cut' instruments) ==")
byinst=defaultdict(list)
for t in others: byinst[t["inst"]].append(t)
for k in sorted(byinst):
    n,pnl,wr=agg(byinst[k]); print(f"{k:10s} n={n:3d} pnl={pnl:+8.2f} wr={wr:4.1f}%")

# US500 inside restricted: is US500 itself profitable?
us500=[t for t in trades if fam(t["inst"])=="US500"]
n,pnl,wr=agg(us500)
print(f"\nUS500 (KEPT by scope) n={n} pnl={pnl:+.2f} wr={wr:.1f}%  <-- scope KEEPS this")

# GOLD beta confound: was gold directional this month? check SHORT vs LONG on gold
gold=[t for t in trades if fam(t["inst"])=="GOLD"]
gs=[t for t in gold if t["dir"]=="SHORT"]; gl=[t for t in gold if t["dir"]=="LONG"]
print("\n== GOLD direction (beta check) ==")
for nm,grp in [("SHORT",gs),("LONG",gl)]:
    n,pnl,wr=agg(grp); print(f"GOLD {nm:5s} n={n:3d} pnl={pnl:+8.2f} wr={wr:4.1f}%")

# Walk-forward: split by date. Train = before 06-05, Test = 06-05 onward (rough)
def wf(cut):
    train=[t for t in trades if t["open"]<cut]
    test=[t for t in trades if t["open"]>=cut]
    return train,test
for cut in ["2026-06-01","2026-06-05","2026-06-08"]:
    tr,te=wf(cut)
    # does "cut OTHER" rule help in TEST half?
    tr_full=agg(tr); te_full=agg(te)
    te_restr=[t for t in te if fam(t["inst"]) in ("GOLD","US500")]
    te_rem=[t for t in te if fam(t["inst"]) not in ("GOLD","US500")]
    print(f"\ncut={cut}: TRAIN n={tr_full[0]} pnl={tr_full[1]:+.2f} | TEST n={te_full[0]} pnl={te_full[1]:+.2f}")
    print(f"   TEST removed-instruments n={agg(te_rem)[0]} pnl={agg(te_rem)[1]:+.2f}  (>0 means cutting them WOULD have hurt)")

# Sample size of the 'cut' instruments
print("\n== SAMPLE SIZE of evidence for the rule ==")
print(f"OTHER (non gold/us500) total trades that justify the cut: {n_x}")
print(f"Distinct OTHER instruments: {sorted(set(t['inst'] for t in others))}")
print(f"Distinct days OTHER traded: {sorted(set(t['open'] for t in others))}")
