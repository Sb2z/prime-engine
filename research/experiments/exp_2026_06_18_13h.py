#!/usr/bin/env python3
"""PRIME ANALYST — slot MIDI 13h (2026-06-18). DIAGNOSTIC DESCRIPTIF, *PAS* un verdict.

================================================================================
POURQUOI ZÉRO hypothèse soumise au juge ce midi (décision assumée)
================================================================================
Au 18/06 13h le registry compte 28 hypothèses réelles (+4 fixtures TEST_JUDGE),
TOUTES KILLED — les 7 familles exprimables sont épuisées sur le lake 2021-2026 :
  momentum            : H1(6h), HX/HY(1d uncond)                → KILLED
  momentum_regime     : HA, HH/HI(1h), HL/HM, HP, HQ/HR(1d), HU → KILLED
  momentum_breakout   : HS/HT(1h), HV(1d)                       → KILLED
  mean_reversion      : H2, HK, HW                              → KILLED
  session_hour        : H3(open drift), HB(overnight drift)     → KILLED (standalone)
  cot_extreme         : HD, HE                                  → KILLED
  ichimoku (×5)       : HF,HG,HC,HJ,HN/HO                       → KILLED
Ce matin (09h) le momentum 1d a été clos AVEC PUISSANCE (HX n_eff=181 +0.14% n.s.).
Re-tester une famille morte avec d'autres knobs = cosmétique qui DURCIT Bonferroni
pour tout le monde (RESEARCH_PROTOCOL, état d'esprit). Max 2 ≠ minimum 2. Donc 0.

Le SEUL angle nommé non encore exploré = le momentum CONDITIONNÉ À LA SESSION
(interaction momentum × heure), qui n'est PAS exprimable : `session_hour` est un
signal directionnel autonome (déjà mort), pas un FILTRE de session sur un momentum.
Il faut la famille `momentum_regime_session` (spec'd le 17/06, TOKEN SAM requis).

================================================================================
CE QUE CE SCRIPT FAIT — motivation chiffrée pour (ou contre) la demande de famille
================================================================================
Avant de demander à Sam de dépenser son token sur `momentum_regime_session`, on
REGARDE LA DONNÉE : le momentum 1h a-t-il une espérance qui dépend de la session
d'entrée ? Si même une coupe descriptive ne montre AUCUNE session où le momentum
penche positif, la famille ne vaut pas le token → la porte se referme honnêtement.
Si une session ressort nettement → argument concret pour la spec.

⚠️ CECI N'EST PAS UN VERDICT : pas de walk-forward, pas d'IC bootstrap-jours, pas
de déflation. Retours BRUTS (hors coûts). Les coûts (~0.05-0.10%/trade) frappent
TOUTES les sessions ~uniformément → seul le CLASSEMENT RELATIF inter-session est
informatif ici. Toute hypothèse retenue PASSERA par harness.evaluate si Sam crée
la famille. Source homogène : GC=F 1h (GOLD) et ES=F 1h (US500), jamais mélangées.
"""
import os
import sys
import datetime as dt

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "research"))
import datalake  # noqa: E402

try:
    import tz_util as tz  # production helper if present
except Exception:
    tz = None


def paris_hour(ts_epoch):
    d = dt.datetime.fromtimestamp(float(ts_epoch), dt.timezone.utc)
    # GC=F/ES=F yfinance ts sont UTC ; Paris = UTC+2 en été (juin). Approx fixe +2
    # suffit pour un bucket descriptif (l'objet n'est pas une précision DST fine).
    return (d.hour + 2) % 24, d.weekday()


def session_bucket(h):
    if 0 <= h < 8:
        return "ASIE/NUIT 0-8"
    if 8 <= h < 14:
        return "LONDRES 8-14"
    if 14 <= h < 22:
        return "NY 14-22"
    return "LATE 22-24"


def ret_pct(candles, i, k):
    if i - k < 0:
        return None
    c0 = float(candles[i - k][4])
    c1 = float(candles[i][4])
    return (c1 - c0) / c0 * 100.0 if c0 else None


def diagnose(ticker, label, k=6, thr=0.5, horizon=6):
    candles, _ = datalake.load_candles(ticker, "1h")
    n = len(candles)
    buckets = {}  # session -> [list of signed forward returns]
    dir_count = {"LONG": 0, "SHORT": 0}
    for i in range(k, n - horizon):
        r = ret_pct(candles, i, k)
        if r is None:
            continue
        sig = "LONG" if r > thr else ("SHORT" if r < -thr else None)
        if sig is None:
            continue
        h, wd = paris_hour(candles[i][0])
        if wd >= 5:
            continue
        entry = float(candles[i + 1][1])  # open i+1 (pas de lookahead)
        exit_ = float(candles[i + horizon][4])
        fwd = (exit_ - entry) / entry * 100.0
        signed = fwd if sig == "LONG" else -fwd
        b = session_bucket(h)
        buckets.setdefault(b, []).append(signed)
        dir_count[sig] += 1
    print(f"\n===== {label} ({ticker} 1h, k={k}/thr={thr}, horizon={horizon}h) =====")
    print(f"signaux: {dir_count} (total {sum(dir_count.values())})")
    print(f"{'session':16} {'n':>6} {'moy% brut':>10} {'win%':>7} {'somme%':>9}")
    order = ["ASIE/NUIT 0-8", "LONDRES 8-14", "NY 14-22", "LATE 22-24"]
    for b in order:
        xs = buckets.get(b, [])
        if not xs:
            print(f"{b:16} {0:>6}")
            continue
        mean = sum(xs) / len(xs)
        win = sum(1 for x in xs if x > 0) / len(xs) * 100
        print(f"{b:16} {len(xs):>6} {mean:>10.4f} {win:>7.1f} {sum(xs):>9.2f}")
    allx = [x for xs in buckets.values() for x in xs]
    if allx:
        print(f"{'TOUTES':16} {len(allx):>6} {sum(allx)/len(allx):>10.4f} "
              f"{sum(1 for x in allx if x>0)/len(allx)*100:>7.1f} {sum(allx):>9.2f}")


if __name__ == "__main__":
    diagnose("GC=F", "GOLD momentum 1h par session", k=6, thr=0.5, horizon=6)
    diagnose("ES=F", "ES momentum 1h par session", k=6, thr=0.5, horizon=6)
    print("\n⚠️ DESCRIPTIF hors coûts, hors IC, hors walk-forward — motivation pour la "
          "demande de famille `momentum_regime_session` à Sam, PAS un verdict.")
