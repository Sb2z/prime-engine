#!/usr/bin/env python3
"""
SWING BOOK — moteur de signaux ACHAT/VENTE hebdo (actions, hors CFD).
═══════════════════════════════════════════════════════════════════════════════
Ce que Sam veut voir (30-06) : un message Telegram DEAD SIMPLE — « achète telle
action, vends telle action ». C'est tout. ≤10 achats/sem (limite Revolut gratuite).

Le bot gère un PORTEFEUILLE MODÈLE (swing_portfolio.json) : il te dit quoi faire,
tu exécutes sur Revolut. Chaque semaine :
  1. règles de SORTIE sur les lignes tenues  -> VENDS
  2. on libère des slots, on classe les nouveaux candidats (swing_scanner) -> ACHÈTE
  3. message Telegram minimal + mise à jour de l'état.

Règles de sortie (le "vendre au pic" en version RÈGLE — on ne devine pas le sommet) :
  • cassure de tendance : prix < EMA50
  • trailing stop : repli > 15% depuis le plus-haut depuis l'entrée
  • durée max : 8 semaines (56 j)
  • momentum épuisé : 1 mois négatif ET prix sous l'EMA20

Données yfinance. notify.send pour Telegram. Écrit son propre état (aucune course).
CLI :  python swing_book.py          -> aperçu (dry-run, affiche le message)
       python swing_book.py send     -> envoie Telegram + met à jour le portefeuille
"""
import datetime as dt
import json
import os

import notify
import swing_scanner as ss

PORTFOLIO = "/Users/sam/trading/swing_portfolio.json"
MAX_HOLD_DAYS = 56          # 8 semaines
TRAIL_STOP = 0.15           # -15% depuis le pic depuis l'entrée
WEEKLY_BUY_CAP = 10         # plafond Revolut (achats gratuits/sem)


def _load():
    """Fichier ABSENT = init légitime (book vide). Fichier PRÉSENT mais illisible =
    on REFUSE de continuer : sinon le run croirait le book vide, recommanderait 7
    achats et écraserait l'état -> les positions réelles deviendraient orphelines."""
    if not os.path.exists(PORTFOLIO):
        return {"holdings": [], "updated": None}
    try:
        return json.load(open(PORTFOLIO, encoding="utf-8"))
    except Exception as e:
        try:
            import shutil
            shutil.copy2(PORTFOLIO, PORTFOLIO + ".corrupt")
            notify.send(f"🛑 SWING : swing_portfolio.json ILLISIBLE ({e}) — run annulé, "
                        f"copie .corrupt gardée. Le book réel n'est plus suivi !", silent=False)
        except Exception:
            pass
        raise SystemExit(f"swing_portfolio.json corrompu: {e}")


def _save(p):
    p["updated"] = dt.datetime.now(dt.timezone.utc).isoformat()
    tmp = PORTFOLIO + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(p, f, ensure_ascii=False, indent=1)
        f.flush(); os.fsync(f.fileno())
    os.replace(tmp, PORTFOLIO)


def _performance_line(p, holdings, sells):
    """Book (réalisé + latent, équipondéré) vs QQQ vs équipondéré de l'UNIVERS,
    depuis l'inception. Lève en cas de souci (l'appelant avale -> ligne absente)."""
    inception = p.get("inception") or "2026-06-30"
    tickers = sorted(set(ss.UNIVERSE + [ss.BENCHMARK] + [h["ticker"] for h in holdings]))
    bars = ss._fetch(tickers, period="6mo")
    import pandas as pd
    t0 = pd.Timestamp(inception)

    def _ret_since(tk):
        df = bars.get(tk)
        if df is None:
            return None
        c = df["Close"]
        idx = c.index.tz_localize(None) if getattr(c.index, "tz", None) is not None else c.index
        before = c[idx <= t0]
        if before.empty:
            return None
        return float(c.iloc[-1] / before.iloc[-1] - 1)

    # book = moyenne équipondérée : lignes CLOSES (pnl_pct réalisé) + lignes OUVERTES (latent)
    rets = [x["pnl_pct"] / 100 for x in (p.get("closed") or [])]
    rets += [s["pnl_pct"] / 100 for s in sells]              # closes de CE run
    for h in holdings:
        df = bars.get(h["ticker"])
        if df is not None and h.get("entry_px"):
            rets.append(float(df["Close"].iloc[-1]) / h["entry_px"] - 1)
    if not rets:
        return None
    book = sum(rets) / len(rets)
    qqq = _ret_since(ss.BENCHMARK)
    uni = [r for r in (_ret_since(t) for t in ss.UNIVERSE) if r is not None]
    ew = sum(uni) / len(uni) if uni else None
    fmt = lambda v: f"{v*100:+.1f}%" if v is not None else "?"
    return (f"📈 Book {fmt(book)} · QQQ {fmt(qqq)} · Univers-EW {fmt(ew)}  (depuis {inception[5:]})"
            + ("  ⚠️ sous les DEUX benchmarks" if (qqq is not None and ew is not None
                                                   and book < qqq and book < ew) else ""))


def _exit_reason(h, df):
    """Retourne (True, raison) si la ligne doit être vendue, sinon (False, '')."""
    import pandas as pd
    c = df["Close"]
    px = float(c.iloc[-1])
    ema20 = float(c.ewm(span=20).mean().iloc[-1])
    ema50 = float(c.ewm(span=50).mean().iloc[-1])
    ret21 = px / float(c.iloc[-22]) - 1 if len(c) > 22 else 0.0
    entry_date = dt.date.fromisoformat(h["entry_date"])
    held_days = (dt.date.today() - entry_date).days
    # défensif : yf.download rend un index tz-naïf aujourd'hui, mais un index
    # tz-aware (Ticker.history / future version yfinance) ferait TypeError et
    # tuerait TOUT le run hebdo — on neutralise le tz avant de comparer.
    idx = c.index.tz_localize(None) if getattr(c.index, "tz", None) is not None else c.index
    since = c[idx >= pd.Timestamp(entry_date)]
    peak = float(since.max()) if len(since) else px
    dd = px / peak - 1
    if px < ema50:
        return True, "tendance cassée (sous EMA50)"
    if dd <= -TRAIL_STOP:
        return True, f"trailing stop ({dd*100:.0f}% du pic)"
    if held_days >= MAX_HOLD_DAYS:
        return True, "durée max 8 sem atteinte"
    if ret21 < 0 and px < ema20:
        return True, "momentum épuisé"
    return False, ""


def weekly_signals():
    """Calcule VENDS + ACHÈTE. Retourne dict {sells, buys, message, new_holdings}."""
    p = _load()
    held = p.get("holdings", [])
    held_tickers = [h["ticker"] for h in held]

    # 1) sorties : on (re)tire les prix des lignes tenues
    sells, keep, no_data = [], [], []
    if held_tickers:
        bars = ss._fetch(held_tickers, period="9mo")
        for h in held:
            df = bars.get(h["ticker"])
            if df is None:
                # data manquante : on garde par prudence MAIS on le DIT — sinon
                # « ✅ Rien à faire » alors qu'aucune règle de sortie n'a tourné.
                keep.append(h); no_data.append(h["ticker"]); continue
            out, reason = _exit_reason(h, df)
            if out:
                px = float(df["Close"].iloc[-1])
                sells.append({**h, "px": px, "reason": reason,
                              "pnl_pct": round((px / h["entry_px"] - 1) * 100, 1)})
            else:
                keep.append(h)

    # 2) achats : combien de slots libres + caps secteur sur ce qui reste
    sector_start = {}
    for h in keep:
        s = h.get("sector", "?")
        sector_start[s] = sector_start.get(s, 0) + 1
    free = max(0, ss.N_LINES - len(keep))
    free = min(free, WEEKLY_BUY_CAP)
    buys = []
    if free > 0:
        rec = ss.recommend(n_lines=free, exclude=set(held_tickers), sector_start=sector_start)
        if not rec.get("error"):
            for r in rec["picks"]:
                buys.append({"ticker": r["ticker"], "entry_px": round(float(r["px"]), 2),
                             "sector": r.get("sector", "?"),
                             "entry_date": dt.date.today().isoformat()})

    # 2b) performance : book vs QQQ vs ÉQUIPONDÉRÉ-UNIVERS (le benchmark honnête —
    # l'univers choisi en 2026 bat QQQ tout seul ; le scoring doit battre l'EW,
    # sinon kill-switch : backtest 36 mois, skill au-dessus de l'EW non démontré).
    perf_line = None
    try:
        perf_line = _performance_line(p, keep, sells)
    except Exception:
        perf_line = None

    # 3) message DEAD SIMPLE
    week = dt.date.today().strftime("%d/%m")
    lines = [f"📊 SWING ACTIONS — {week}"]
    if perf_line:
        lines.append(perf_line)
    # Lancé pendant la séance US, la « barre du jour » est incomplète : les
    # règles (EMA, momentum) réagissent au bruit intraday -> churn (ex. vendre
    # ce qu'on a acheté le matin). La tâche du lundi 14h Paris tourne marché
    # fermé ; un run manuel en séance doit être pris avec des pincettes.
    from zoneinfo import ZoneInfo
    now_p = dt.datetime.now(ZoneInfo("Europe/Paris"))
    if now_p.weekday() < 5 and 15 <= now_p.hour < 22:
        lines.append("⚠️ marché US OUVERT — barre du jour incomplète, signaux à "
                     "confirmer à la clôture (préférer le run planifié 14h).")
    if buys:
        lines.append("\n🟢 ACHÈTE maintenant :")
        lines += [f"  • {b['ticker']}  (~{b['entry_px']:.0f}$)" for b in buys]
    if sells:
        lines.append("\n🔴 VENDS maintenant :")
        lines += [f"  • {s['ticker']}  ({s['pnl_pct']:+.0f}%, {s['reason']})" for s in sells]
    if not buys and not sells:
        lines.append("\n✅ Rien à faire cette semaine — on garde tout.")
    if no_data:
        lines.append(f"\n⚠️ {len(no_data)} ligne(s) SANS données ({', '.join(no_data)}) — "
                     f"sorties NON vérifiées ce run, garde un œil dessus.")
    new_holdings = keep + buys
    return {"sells": sells, "buys": buys, "message": "\n".join(lines),
            "new_holdings": new_holdings, "portfolio": p}


def run(send=False):
    try:
        r = weekly_signals()
    except SystemExit:
        raise
    except Exception as e:
        # jamais d'échec silencieux dans swing_book.log un lundi 14h : Sam doit
        # savoir que les règles de sortie n'ont PAS tourné.
        try:
            notify.send(f"🛑 SWING : run hebdo en ÉCHEC ({type(e).__name__}: {e}) — "
                        f"aucune règle de sortie évaluée, relancer python swing_book.py send.",
                        silent=False)
        except Exception:
            pass
        raise
    print(r["message"])
    if send:
        # On ne commite le book modèle QUE si Sam a reçu le message : sinon un
        # VENDS serait retiré de l'état sans jamais avoir été signalé (position
        # réelle orpheline) et le run suivant ne le re-signalerait pas.
        ok = notify.send(r["message"], silent=False)
        if ok:
            p = r["portfolio"]
            p["holdings"] = r["new_holdings"]
            p.setdefault("inception", "2026-06-30")
            # grand livre des lignes closes : nécessaire au tracker book-vs-benchmarks
            p.setdefault("closed", []).extend(
                {"ticker": s["ticker"], "entry_px": s["entry_px"], "exit_px": s["px"],
                 "pnl_pct": s["pnl_pct"], "reason": s["reason"],
                 "exit_date": dt.date.today().isoformat()} for s in r["sells"])
            _save(p)
            print(f"\n[envoyé + portefeuille mis à jour : {len(r['new_holdings'])} lignes]")
        else:
            print("\n[ECHEC envoi Telegram -> book NON modifié, signaux re-émis au prochain run]")
    return r


if __name__ == "__main__":
    import sys
    run(send=(len(sys.argv) > 1 and sys.argv[1] == "send"))
