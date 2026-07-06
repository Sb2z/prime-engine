#!/usr/bin/env python3
"""
1er MODÈLE, edge personnel de Sam (user_trade_context, 15 jours / 114 captures).
═══════════════════════════════════════════════════════════════════════════════
PROTOCOLE PRÉ-ENREGISTRÉ (figé le 2026-07-02 AVANT d'avoir vu le moindre résultat) :

  TARGET   y = 1 si ret_1h > 0 (la direction prise était la bonne à 1h de marché).
           ret_1h = outcome marché signé par la direction, ANTI-lookahead, backfillé
           depuis le parquet. PAS le pnl réel (confondu par la gestion des sorties).
  FEATURES (10, fixées d'avance, dérivées des règles minées, aucune ajoutée après) :
    us_hours       session ∈ {PRE_NY, NY, NY_PM, US_AM, US_PM, US_OPEN, US_CLOSE}
    asia_eu        session ∈ {ASIAN, EU_PREMARKET, OVERNIGHT}   (référence: LONDON)
    reg_transition « TRANSITION » dans le régime
    reg_tendance   « TENDANCE » dans le régime
    grade_a        grade == A_SETUP
    dir_short      direction == SHORT
    align_tf1h     dir_sign × tf_1h   (trader AVEC ou CONTRE la tendance 1h)
    align_tf4h     dir_sign × tf_4h
    imb_x_dir      dir_sign × (of_imbalance − 0.5)  (0 si absent)
    of_missing     of_imbalance absent (jours pré-18/06)
  MODÈLE   régression logistique L2 (Newton, lambda=1.0), features standardisées.
           Simple et interprétable À DESSEIN : n=114 / 15 jours, tout modèle plus
           gros mémoriserait les jours.
  VALIDATION leave-one-day-out (15 folds), l'unité statistique est le JOUR.
  MÉTRIQUES  AUC LODO, accuracy LODO vs base rate, et le TEST EN $ : PnL réel
           (pnl_usd des imports CSV) gardé en ne tradant que si p̂ ≥ 0.5, comparé
           (a) au total sans filtre et (b) à la RÈGLE SIMPLE « us_hours seulement ».
  CRITÈRE DE RÉTENTION (honnêteté) : le modèle n'est retenu QUE s'il bat la règle
           simple en LODO sur le $ ET l'AUC. Sinon verdict = « les règles simples
           suffisent, pas de modèle », un non-résultat est un résultat.
  SORTIE   research/models/user_edge_model_v1.json + rapport console.
           RIEN n'est branché en prod (le chercheur propose, Sam promeut).
"""
import datetime as dt
import json
import os

import numpy as np

SRC = "C:/Users/sam/trading/user_trade_context.jsonl"
JOURNAL = "C:/Users/sam/trading/journal.json"
OUT_MODEL = "C:/Users/sam/trading/research/models/user_edge_model_v1.json"
US = {"PRE_NY", "NY", "NY_PM", "US_AM", "US_PM", "US_OPEN", "US_CLOSE"}
ASIA_EU = {"ASIAN", "EU_PREMARKET", "OVERNIGHT"}
FEATS = ["us_hours", "asia_eu", "reg_transition", "reg_tendance", "grade_a",
         "dir_short", "align_tf1h", "align_tf4h", "imb_x_dir", "of_missing"]
LAMBDA = 1.0


def load():
    recs = [json.loads(l) for l in open(SRC, encoding="utf-8") if l.strip()]
    recs = [r for r in recs if not r.get("quality") and r.get("context")
            and (r.get("outcome") or {}).get("ret_1h") is not None]
    jj = json.load(open(JOURNAL, encoding="utf-8"))
    pnl = {}
    for s in jj["signals"]:
        if s.get("note") == "csv-import" and s.get("pnl_usd") is not None:
            pnl[(s["asset"], s["ts"][:16])] = s["pnl_usd"]
    rows = []
    for r in recs:
        c = r["context"]; sign = 1.0 if r["direction"] == "LONG" else -1.0
        imb = c.get("of_imbalance")
        reg = c.get("regime") or ""
        rows.append({
            "day": r["ts"][:10],
            "y": 1.0 if r["outcome"]["ret_1h"] > 0 else 0.0,
            "pnl": pnl.get((r["asset"], r["ts"][:16])),
            "x": [
                1.0 if c.get("session") in US else 0.0,
                1.0 if c.get("session") in ASIA_EU else 0.0,
                1.0 if "TRANSITION" in reg else 0.0,
                1.0 if "TENDANCE" in reg else 0.0,
                1.0 if c.get("grade") == "A_SETUP" else 0.0,
                1.0 if r["direction"] == "SHORT" else 0.0,
                sign * float(c.get("tf_1h") or 0.0),
                sign * float(c.get("tf_4h") or 0.0),
                sign * ((float(imb) - 0.5) if imb is not None else 0.0),
                1.0 if imb is None else 0.0,
            ],
        })
    return rows


def fit_logistic(X, y, lam=LAMBDA, iters=30):
    n, p = X.shape
    Xb = np.hstack([np.ones((n, 1)), X])
    w = np.zeros(p + 1)
    R = lam * np.eye(p + 1); R[0, 0] = 0.0          # pas de pénalité sur le biais
    for _ in range(iters):
        z = Xb @ w
        mu = 1.0 / (1.0 + np.exp(-np.clip(z, -30, 30)))
        g = Xb.T @ (mu - y) + R @ w
        W = np.clip(mu * (1 - mu), 1e-6, None)
        H = (Xb * W[:, None]).T @ Xb + R
        try:
            w -= np.linalg.solve(H, g)
        except np.linalg.LinAlgError:
            break
    return w


def predict(w, X):
    Xb = np.hstack([np.ones((X.shape[0], 1)), X])
    return 1.0 / (1.0 + np.exp(-np.clip(Xb @ w, -30, 30)))


def auc(y, p):
    order = np.argsort(p)
    ranks = np.empty(len(p)); ranks[order] = np.arange(1, len(p) + 1)
    pos = y == 1
    n1, n0 = pos.sum(), (~pos).sum()
    if n1 == 0 or n0 == 0:
        return None
    return float((ranks[pos].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def main():
    rows = load()
    days = sorted({r["day"] for r in rows})
    X = np.array([r["x"] for r in rows]); y = np.array([r["y"] for r in rows])
    day_arr = np.array([r["day"] for r in rows])
    pnl = np.array([r["pnl"] if r["pnl"] is not None else np.nan for r in rows])
    print(f"n={len(rows)} | jours={len(days)} | base rate y=1 : {y.mean()*100:.0f}%")

    # ── LODO ──
    p_hat = np.zeros(len(rows))
    for d in days:
        tr = day_arr != d; te = ~tr
        mu, sd = X[tr].mean(0), X[tr].std(0); sd[sd == 0] = 1.0
        w = fit_logistic((X[tr] - mu) / sd, y[tr])
        p_hat[te] = predict(w, (X[te] - mu) / sd)

    a = auc(y, p_hat)
    acc = float(((p_hat >= 0.5) == (y == 1)).mean())
    base = max(y.mean(), 1 - y.mean())
    print(f"\nLODO : AUC={a:.3f} | accuracy={acc*100:.0f}% (base {base*100:.0f}%)")

    # ── test en $ (trades avec pnl réel) ──
    has = ~np.isnan(pnl)
    tot = float(pnl[has].sum())
    keep_model = has & (p_hat >= 0.5)
    keep_rule = has & (X[:, 0] == 1.0)              # règle simple : us_hours
    keep_both = keep_model & keep_rule
    print(f"\nTEST EN $ (n={int(has.sum())} trades, PnL réel net Revolut) :")
    print(f"  sans filtre           : {tot:+8.2f}$  ({int(has.sum())} tr)")
    print(f"  règle simple us_hours : {float(pnl[keep_rule].sum()):+8.2f}$  ({int(keep_rule.sum())} tr)")
    print(f"  modèle p>=0.5 (LODO)  : {float(pnl[keep_model].sum()):+8.2f}$  ({int(keep_model.sum())} tr)")
    print(f"  modèle ET règle       : {float(pnl[keep_both].sum()):+8.2f}$  ({int(keep_both.sum())} tr)")
    # robustesse jour : PnL modèle par jour, sans le meilleur
    dd = {}
    for i in np.where(keep_model)[0]:
        dd[day_arr[i]] = dd.get(day_arr[i], 0.0) + pnl[i]
    if dd:
        best = max(dd.values())
        print(f"  modèle sans son meilleur jour : {sum(dd.values())-best:+8.2f}$ "
              f"({len(dd)} jours, meilleur {best:+.2f}$)")

    # ── fit final (toutes données) pour l'interprétation + l'artefact ──
    mu, sd = X.mean(0), X.std(0); sd[sd == 0] = 1.0
    w = fit_logistic((X - mu) / sd, y)
    print("\nCOEFFICIENTS (standardisés, fit complet) :")
    for name, coef in sorted(zip(FEATS, w[1:]), key=lambda t: -abs(t[1])):
        print(f"  {name:15s} {coef:+.3f}")

    os.makedirs(os.path.dirname(OUT_MODEL), exist_ok=True)
    json.dump({
        "version": "v1", "trained_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "protocol": "pré-enregistré 2026-07-02 (voir docstring du script)",
        "n": len(rows), "days": len(days), "features": FEATS,
        "standardize": {"mean": mu.tolist(), "std": sd.tolist()},
        "weights_bias_first": w.tolist(),
        "lodo": {"auc": a, "accuracy": acc, "base_rate": float(base)},
        "status": "PROPOSÉ, non branché en prod (Sam promeut)",
    }, open(OUT_MODEL, "w", encoding="utf-8"), indent=1)
    print(f"\nartefact -> {OUT_MODEL}")


if __name__ == "__main__":
    main()
