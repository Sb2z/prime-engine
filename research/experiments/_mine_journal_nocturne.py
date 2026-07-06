"""Mining DESCRIPTIF (report-only, NON jugeable harness) des 78 trades USER reels.
Backlog #2 analyste 23h : sequences post-perte, sessions, regimes (ADX/score).
AVERTISSEMENT : score = composite prod ABSENT du lake -> ceci CLASSE, ne TRANCHE
rien. n=78 brut, sous-echantillons fins -> purement indicatif, aucun IC fiable."""
import json
from collections import Counter, defaultdict

d = json.load(open("journal.json"))
sigs = d["signals"]
real = [s for s in sigs if s.get("source") == "REAL_TRADE"]
# decisifs = WIN/LOSS (exclut WIN_TIME/LOSS_TIME/FLAT/NOFILL = sorties horizon/flat)
dec = [s for s in real if s.get("result") in ("WIN", "LOSS")]
print(f"REAL_TRADE n={len(real)} | decisifs WIN/LOSS n={len(dec)}")


def wr(rows):
    w = sum(1 for r in rows if r["result"] == "WIN")
    n = len(rows)
    return (w, n, round(100 * w / n, 1) if n else None)


def exp_pct(rows):
    vals = [r.get("pnl_pct") for r in rows if isinstance(r.get("pnl_pct"), (int, float))]
    return round(sum(vals) / len(vals), 3) if vals else None


print("\n== GLOBAL (decisifs) ==", wr(dec), "exp%", exp_pct(dec))

# 1) SEQUENCES POST-PERTE : le trade qui SUIT immediatement une perte
real_sorted = sorted(real, key=lambda s: s.get("ts", ""))
post_loss, post_win = [], []
prev = None
for s in real_sorted:
    if prev is not None and s.get("result") in ("WIN", "LOSS"):
        if prev.get("result") == "LOSS":
            post_loss.append(s)
        elif prev.get("result") == "WIN":
            post_win.append(s)
    if s.get("result") in ("WIN", "LOSS"):
        prev = s
print("\n== POST-PERTE (trade suivant une LOSS) ==", wr([x for x in post_loss if x["result"] in ("WIN","LOSS")]), "exp%", exp_pct(post_loss))
print("== POST-GAIN  (trade suivant une WIN)  ==", wr([x for x in post_win if x["result"] in ("WIN","LOSS")]), "exp%", exp_pct(post_win))

# 2) SESSION
by_sess = defaultdict(list)
for s in dec:
    by_sess[s.get("session", "?")].append(s)
print("\n== PAR SESSION ==")
for k, v in sorted(by_sess.items()):
    print(f"  {k:12s}", wr(v), "exp%", exp_pct(v))

# 3) REGIME ADX (bandes)
def adx_band(a):
    if a is None: return "?"
    if a < 20: return "ADX<20 (range)"
    if a < 30: return "ADX 20-30"
    return "ADX>=30 (trend)"
by_adx = defaultdict(list)
for s in dec:
    by_adx[adx_band(s.get("adx"))].append(s)
print("\n== PAR REGIME ADX ==")
for k, v in sorted(by_adx.items()):
    print(f"  {k:18s}", wr(v), "exp%", exp_pct(v))

# 4) BANDES DE SCORE (composite prod)
def score_band(sc):
    if sc is None: return "?"
    if sc < 6: return "score<6"
    if sc < 7: return "score 6-7"
    if sc < 8: return "score 7-8"
    return "score>=8"
by_sc = defaultdict(list)
for s in dec:
    by_sc[score_band(s.get("score"))].append(s)
print("\n== PAR BANDE DE SCORE (composite prod, HORS lake) ==")
for k, v in sorted(by_sc.items()):
    print(f"  {k:12s}", wr(v), "exp%", exp_pct(v))

# 5) DIRECTION
by_dir = defaultdict(list)
for s in dec:
    by_dir[s.get("direction", "?")].append(s)
print("\n== PAR DIRECTION ==")
for k, v in sorted(by_dir.items()):
    print(f"  {k:6s}", wr(v), "exp%", exp_pct(v))
