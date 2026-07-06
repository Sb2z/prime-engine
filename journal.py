#!/usr/bin/env python3
"""
JOURNAL AUTO-APPRENANT, Forward-testing engine
══════════════════════════════════════════════════════════════════
Chaque scan :
  1. enregistre le signal courant de chaque actif (prix, score, niveaux, indicateurs, macro)
  2. évalue les signaux OUVERTS contre le prix réel actuel (TP touché / Stop touché / en cours)
  3. met à jour MFE/MAE (excursions max favorable/adverse)
  4. calcule la performance réelle par tranche de score, session, ADX, actif

C'est un VRAI forward test : l'IA apprend de ses propres signaux sans intervention manuelle.
"""

import json, os, datetime, time, math

import clusters
import costs
import tz

JOURNAL_FILE = "/Users/sam/trading/journal.json"

# Horizon d'évaluation : un signal non résolu après X heures est clôturé "au marché"
HORIZON_HOURS = 8.0

# Bandes stop/TP par actif (en % du prix) si non fournies, basées sur volatilité typique
ASSET_BANDS = {
    # GOLD : stop élargi 0.35→0.60%, le journal du 29/05 a montré que des stops
    # serrés se font balayer sur les mèches (4 longs directionnellement bons mais stoppés).
    "GOLD":   {"stop_pct": 0.60, "tp1_pct": 1.00, "tp2_pct": 1.60, "leverage": 20},
    "OIL":    {"stop_pct": 1.20, "tp1_pct": 2.20, "tp2_pct": 3.50, "leverage": 10},
    "BTC":    {"stop_pct": 1.50, "tp1_pct": 3.00, "tp2_pct": 5.00, "leverage": 2},
    "ETH":    {"stop_pct": 1.80, "tp1_pct": 3.50, "tp2_pct": 6.00, "leverage": 2},
    "US500":  {"stop_pct": 0.40, "tp1_pct": 0.80, "tp2_pct": 1.30, "leverage": 10},
    "NAS100": {"stop_pct": 0.55, "tp1_pct": 1.00, "tp2_pct": 1.70, "leverage": 10},
}


def paris_now():
    return tz.paris_now()


def load_journal() -> dict:
    try:
        with open(JOURNAL_FILE) as f:
            return json.load(f)
    except Exception:
        return {"signals": [], "stats": {}, "last_updated": ""}


def save_journal(j: dict):
    # Écriture ATOMIQUE (temp + os.replace) : un crash en plein write ne doit jamais
    # laisser journal.json tronqué, load_journal avalerait le fichier corrompu et
    # repartirait d'un journal VIDE (perte silencieuse de TOUT l'historique de mesure).
    tmp = JOURNAL_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(j, f, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, JOURNAL_FILE)


def _base_source(s):
    """Fournisseur de base d'une source de prix (ignore le suffixe '+cache')."""
    return (s or "").split("+")[0].strip().lower()


# ── Enregistrement d'un signal ──────────────────────────────────────────────
def log_signal(asset, price, direction, score, ta, session, vix=None, dxy=None,
               stop=None, tp1=None, tp2=None, note=""):
    """
    Enregistre un signal de trading. Calcule stop/TP par défaut si non fournis.
    Ne logge PAS deux fois le même actif+direction s'il y a déjà un signal OPEN
    avec un prix < 0.15% différent (évite les doublons entre scans rapprochés).
    """
    j = load_journal()
    bands = ASSET_BANDS.get(asset, {"stop_pct": 0.5, "tp1_pct": 1.0, "tp2_pct": 1.6, "leverage": 1})
    sign = 1 if direction == "LONG" else -1

    if stop is None:
        stop = round(price * (1 - sign * bands["stop_pct"] / 100), 2)
    if tp1 is None:
        tp1 = round(price * (1 + sign * bands["tp1_pct"] / 100), 2)
    if tp2 is None:
        tp2 = round(price * (1 + sign * bands["tp2_pct"] / 100), 2)

    # Anti-doublon : signal OPEN même actif/direction à prix très proche
    for s in j["signals"]:
        if (s["asset"] == asset and s["direction"] == direction
                and s["status"] == "OPEN"
                and abs(s["entry"] - price) / price < 0.0015):
            return None  # déjà tracké

    # Déduplication par position : si une racine IA même actif/direction est
    # encore OPEN et que le nouveau signal est la même position (cf. clusters),
    # on logge quand même (traçabilité) mais marqué DUPLICATE, exclu des stats.
    duplicate_of = None
    probe = {"asset": asset, "direction": direction, "entry": round(price, 2),
             "ts": datetime.datetime.now(datetime.timezone.utc).isoformat()}
    for s in j["signals"]:
        if (s.get("status") == "OPEN" and clusters.is_ai(s)
                and clusters.is_duplicate_of(probe, s)):
            duplicate_of = s["id"]
            break

    sig = {
        "id":        f"{asset}_{int(time.time())}",
        "ts":        datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "paris":     paris_now().strftime("%Y-%m-%d %H:%M"),
        "asset":     asset,
        "direction": direction,
        "score":     round(score, 1),
        "entry":     round(price, 2),
        "stop":      stop,
        "tp1":       tp1,
        "tp2":       tp2,
        "rsi":       ta.get("rsi"),
        "adx":       ta.get("adx"),
        "stoch_k":   ta.get("stoch_k"),
        "session":   session,
        "vix":       vix,
        "dxy":       dxy,
        "status":    "OPEN",
        "result":    None,
        "exit_price": None,
        "pnl_pct":   None,
        "mfe_pct":   0.0,   # max favorable excursion
        "mae_pct":   0.0,   # max adverse excursion
        "note":      note,
    }
    if duplicate_of:
        sig["status"] = "DUPLICATE"
        sig["duplicate_of"] = duplicate_of
    j["signals"].append(sig)
    j["last_updated"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    save_journal(j)
    return sig["id"]


# ── Évaluation des signaux ouverts ──────────────────────────────────────────
def evaluate_open(current_prices: dict, candles_1m=None, candle_sources=None):
    """
    current_prices : {asset: {"lp": price, "high_price": h, "low_price": l}}
    candles_1m     : {asset: [[ts, o, h, l, c, v], ...]} optionnel, fills
                     intrabar : les mèches entre deux scans sont vues, et
                     l'ordre de touche TP/SL est résolu bougie par bougie.
    Met à jour chaque signal OPEN : MFE/MAE, et clôture si TP1 ou Stop touché,
    ou si horizon dépassé.
    Retourne la liste des signaux clôturés ce cycle.
    """
    j = load_journal()
    closed_now = []
    now = datetime.datetime.now(datetime.timezone.utc)

    # ── A_SETUP EN ATTENTE : remplissage à l'entrée annoncée ou expiration ──
    # (audit 2026-06-17, fill-tracking honnête) : un trigger devient OPEN
    # SEULEMENT si le prix touche l'entrée OTE dans sa fenêtre de validité ;
    # sinon EXPIRED (NOFILL). On mesure enfin le VRAI trade, le taux de
    # remplissage de l'entrée annoncée AVANT le PnL.
    for s in j["signals"]:
        if s["status"] != "PENDING":
            continue
        entry = s["entry"]
        sign = 1 if s["direction"] == "LONG" else -1
        bars = (candles_1m or {}).get(s["asset"]) or []
        try:
            trig = datetime.datetime.fromisoformat(s.get("trigger_ts") or s["ts"]).timestamp()
            deadline = datetime.datetime.fromisoformat(s["entry_deadline"]).timestamp()
        except Exception:
            continue
        fill_ts = None
        # Anti CROSS-SOURCE (basis) : ne JAMAIS détecter un fill sur des bougies d'une
        # autre référence de prix que celle de l'entrée (TV/CFD vs yfinance futures
        # GC=F/ES=F en contango → faux fills/NOFILL). On attend que la source revienne.
        cs = (candle_sources or {}).get(s["asset"])
        if cs and s.get("price_source") and _base_source(cs) != _base_source(s["price_source"]):
            s["fill_quality"] = "CROSS_SOURCE"
        else:
            # la source est (re)devenue conforme : un flag CROSS_SOURCE posé à un
            # cycle précédent ne doit pas exclure ce signal À VIE du fill-rate
            # (audit 07-02 : biais de sous-compte des NOFILL).
            if s.get("fill_quality") == "CROSS_SOURCE":
                s["fill_quality"] = None
            for b in bars:
                if b[0] < trig or b[0] > deadline:
                    continue
                s["window_observed"] = True   # ≥1 bougie conforme vue dans la fenêtre
                if (sign > 0 and float(b[3]) <= entry) or (sign < 0 and float(b[2]) >= entry):
                    fill_ts = b[0]
                    break
        if fill_ts is not None:
            s["status"] = "OPEN"
            s["filled_ts"] = datetime.datetime.fromtimestamp(
                fill_ts, datetime.timezone.utc).isoformat()
            s["ts"] = s["filled_ts"]        # horizon + fills comptent dès le REMPLISSAGE
            s["hi_since"] = s["lo_since"] = entry
            # La bougie de remplissage elle-même doit être évaluée pour le SL/TP
            # intrabar : sinon un stop-run sur la mèche de la bougie d'OTE-fill est
            # silencieusement PERDU (new_bars utilise `> last_seen` strict + hi/lo
            # seedés à l'entrée) → biais WR/espérance à la HAUSSE (audit 2026-06-18).
            # On recule last_intrabar_ts d'1s pour inclure la bougie de fill.
            s["last_intrabar_ts"] = fill_ts - 1
        elif now.timestamp() > deadline:
            s["status"] = "EXPIRED"
            s["result"] = "NOFILL"
            # absence de DONNÉE ≠ absence de fill : si AUCUNE bougie conforme n'a
            # couvert la fenêtre (datafeed stale, watcher arrêté), on marque
            # NO_DATA et on exclut du dénominateur du fill-rate (audit 07-02).
            if not s.get("window_observed"):
                s["fill_quality"] = "NO_DATA"
            s["closed_ts"] = now.isoformat()

    for s in j["signals"]:
        if s["status"] != "OPEN":
            continue
        # Anti CROSS-SOURCE : ne pas évaluer TP/SL/MFE sur une autre référence (basis).
        cs = (candle_sources or {}).get(s["asset"])
        if cs and s.get("price_source") and _base_source(cs) != _base_source(s["price_source"]):
            s["fill_quality"] = "CROSS_SOURCE"
            continue
        px = current_prices.get(s["asset"], {})
        lp = px.get("lp")
        if lp is None:
            continue

        entry = s["entry"]
        sign  = 1 if s["direction"] == "LONG" else -1

        # Suivi des extrêmes DEPUIS L'ENTRÉE (running, pas le range journalier).
        # Init au prix d'entrée pour ne jamais compter une mèche antérieure au signal.
        if "hi_since" not in s:
            s["hi_since"] = entry
        if "lo_since" not in s:
            s["lo_since"] = entry

        # ── Fills intrabar : bougies 1m depuis le dernier point connu ──
        bar_exit = None  # (result, kind, niveau) du premier TP/SL touché
        bars = (candles_1m or {}).get(s["asset"]) or []
        if bars:
            try:
                opened_epoch = datetime.datetime.fromisoformat(s["ts"]).timestamp()
            except Exception:
                opened_epoch = 0
            last_seen = s.get("last_intrabar_ts") or opened_epoch
            new_bars = sorted(b for b in bars if b[0] > last_seen)
            # Trou de couverture (> 3 min) : week-end, déconnexion, watcher arrêté
            if new_bars and new_bars[0][0] - last_seen > 180:
                s["fill_quality"] = "PARTIAL"
            for b in new_bars:
                b_h, b_l = float(b[2]), float(b[3])
                s["hi_since"] = round(max(s["hi_since"], b_h), 2)
                s["lo_since"] = round(min(s["lo_since"], b_l), 2)
                s["last_intrabar_ts"] = b[0]
                bar_sl = (b_l <= s["stop"]) if sign > 0 else (b_h >= s["stop"])
                bar_tp = (b_h >= s["tp1"]) if sign > 0 else (b_l <= s["tp1"])
                # Même bougie 1m : conservateur, le SL d'abord
                if bar_sl:
                    bar_exit = ("LOSS", "sl", s["stop"])
                    break
                if bar_tp:
                    bar_exit = ("WIN", "tp", s["tp1"])
                    break

        s["hi_since"] = round(max(s["hi_since"], lp), 2)
        s["lo_since"] = round(min(s["lo_since"], lp), 2)

        # MFE / MAE calculés sur les extrêmes observés depuis l'entrée
        if sign > 0:
            s["mfe_pct"] = round((s["hi_since"] - entry) / entry * 100, 2)
            s["mae_pct"] = round((s["lo_since"] - entry) / entry * 100, 2)
        else:
            s["mfe_pct"] = round((entry - s["lo_since"]) / entry * 100, 2)
            s["mae_pct"] = round((entry - s["hi_since"]) / entry * 100, 2)

        # TP / Stop : ordre résolu intrabar si bougies dispo, sinon détection
        # sur extrêmes observés depuis l'entrée (jamais le range journalier).
        hit_tp = (s["hi_since"] >= s["tp1"]) if sign > 0 else (s["lo_since"] <= s["tp1"])
        hit_sl = (s["lo_since"] <= s["stop"]) if sign > 0 else (s["hi_since"] >= s["stop"])

        # Si les deux touchés dans la même fenêtre, on est conservateur : Stop d'abord
        if bar_exit:
            result, kind, level = bar_exit
            s["status"], s["result"] = "CLOSED", result
            s["exit_price"] = round(costs.adjust_exit(s["asset"], level, s["direction"],
                                                      s.get("session"), kind), 2)
        elif hit_sl:
            s["status"], s["result"] = "CLOSED", "LOSS"
            s["exit_price"] = round(costs.adjust_exit(s["asset"], s["stop"], s["direction"],
                                                      s.get("session"), "sl"), 2)
        elif hit_tp:
            s["status"], s["result"] = "CLOSED", "WIN"
            s["exit_price"] = round(costs.adjust_exit(s["asset"], s["tp1"], s["direction"],
                                                      s.get("session"), "tp"), 2)
        else:
            # Horizon dépassé → clôture au prix courant (spread de sortie inclus)
            opened = datetime.datetime.fromisoformat(s["ts"])
            age_h = (now - opened).total_seconds() / 3600
            if age_h >= HORIZON_HOURS:
                s["status"] = "CLOSED"
                s["exit_price"] = round(costs.adjust_exit(s["asset"], lp, s["direction"],
                                                          s.get("session"), "market"), 2)
                pnl = sign * (s["exit_price"] - entry) / entry * 100
                s["result"] = "WIN_TIME" if pnl > 0.1 else ("LOSS_TIME" if pnl < -0.1 else "FLAT")

        if s["status"] == "CLOSED":
            s["closed_ts"] = now.isoformat()
            pnl = sign * (s["exit_price"] - entry) / entry * 100
            pnl -= costs.swap_pct(s["asset"], costs.nights_held(s["ts"], s["closed_ts"]))
            s["pnl_pct"] = round(pnl, 3)
            s["costs_applied"] = True
            closed_now.append(s)

    j["last_updated"] = now.isoformat()
    _recompute_stats(j)
    save_journal(j)
    return closed_now


def evaluate_open_live(prices=None):
    """Évalue les signaux OPEN avec fills intrabar 1m (fetch TradingView).

    prices : dict optionnel {asset: {"lp": ...}} déjà fetché par l'appelant ;
    sinon fetch live. Les bougies 1m (330 barres ≈ 5h30) couvrent l'intervalle
    entre deux scans et un éventuel arrêt du watcher.
    """
    j = load_journal()
    assets = sorted({s["asset"] for s in j["signals"]
                     if s["status"] in ("OPEN", "PENDING")})
    if not assets:
        return []

    # Datafeed avec fallback (TradingView → yfinance → cache stale).
    # Une bougie stale ou d'une source secondaire reste utilisable pour les
    # extrêmes, mais le référentiel peut différer (basis futures/CFD) : la
    # source est loggée par le watcher via datafeed.last_sources().
    import datafeed
    candles = {}
    cand_sources = {}
    for a in assets:
        c = datafeed.get_candles(a, "1m", 330)
        if c and not c.get("stale"):
            candles[a] = c["candles"]
            cand_sources[a] = c.get("source")

    if prices is None:
        prices = {}
        for a in assets:
            p = datafeed.get_price(a)
            if p and not p.get("stale"):
                prices[a] = p
    # Fallback : dernière bougie 1m si le live n'a rien donné
    for a in assets:
        if a not in prices and candles.get(a):
            prices[a] = {"lp": float(candles[a][-1][4])}

    return evaluate_open(prices, candles_1m=candles, candle_sources=cand_sources)


# ── Statistiques de performance ─────────────────────────────────────────────
def _recompute_stats(j: dict):
    # Doublons IA exclus ; WR principal = touches TP/SL uniquement,
    # les sorties à horizon (WIN_TIME/LOSS_TIME) comptent dans l'espérance
    # mais sont affichées à part.
    # (audit 2026-07-02/03) Les stats de PILOTAGE (win_rate, expectancy, by_*)
    # sont IA-SEULEMENT : les 200+ trades USER importés noyaient les agrégats
    # (poison dormant de confidence_modifier via by_adx/by_score_band), et les
    # « fills » de session WEEKEND (prix figés, 6 fantômes du 07/06 = 60% du
    # PnL IA) sont des artefacts de mesure, pas des trades. Un bloc `user`
    # séparé conserve la visibilité sur les trades réels de Sam.
    def _is_ai(s):
        return (s.get("trader") or ("USER" if s.get("source") == "REAL_TRADE" else "AI")) == "AI"
    closed_all = [s for s in clusters.non_duplicates(j) if s["status"] == "CLOSED"]
    closed = [s for s in closed_all if _is_ai(s) and s.get("session") != "WEEKEND"]
    weekend_ghosts = [s for s in closed_all if _is_ai(s) and s.get("session") == "WEEKEND"]
    user_closed = [s for s in closed_all if not _is_ai(s) and s.get("pnl_pct") is not None]
    wins = [s for s in closed if s["result"] == "WIN"]
    losses = [s for s in closed if s["result"] == "LOSS"]
    time_exits = [s for s in closed if s["result"] in ("WIN_TIME", "LOSS_TIME")]

    def wr(group):
        w = [s for s in group if s["result"] == "WIN"]
        l = [s for s in group if s["result"] == "LOSS"]
        c = w + l
        return (round(len(w) / len(c) * 100, 1), len(c)) if c else (None, 0)

    by_band = {}
    for lo, hi, label in [(8, 11, "8-10"), (7, 8, "7-8"), (6, 7, "6-7"), (0, 6, "<6")]:
        grp = [s for s in closed if s.get("score") is not None and lo <= s["score"] < hi]
        by_band[label] = wr(grp)

    by_session = {}
    for sess in set(s["session"] for s in closed):
        by_session[sess] = wr([s for s in closed if s["session"] == sess])

    by_asset = {}
    for a in set(s["asset"] for s in closed):
        by_asset[a] = wr([s for s in closed if s["asset"] == a])

    # adx None ≠ « ADX faible » : les trades sans mesure sont EXCLUS du bucket
    # (avant, tout import USER à adx=None tombait dans '<20' et masquait le malus).
    with_adx = [s for s in closed if s.get("adx") is not None]
    by_adx = {
        ">30": wr([s for s in with_adx if s["adx"] >= 30]),
        "20-30": wr([s for s in with_adx if 20 <= s["adx"] < 30]),
        "<20": wr([s for s in with_adx if s["adx"] < 20]),
    }

    decisive = [s for s in closed if s["result"] in ("WIN", "LOSS", "WIN_TIME", "LOSS_TIME")]
    avg_win = round(sum(s["pnl_pct"] for s in wins) / len(wins), 2) if wins else 0
    avg_loss = round(sum(s["pnl_pct"] for s in losses) / len(losses), 2) if losses else 0
    # Espérance sur le pnl réel de TOUTES les sorties décisives (time incluses)
    expectancy = round(sum(s.get("pnl_pct") or 0 for s in decisive) / len(decisive), 3) if decisive else None
    te_exp = round(sum(s.get("pnl_pct") or 0 for s in time_exits) / len(time_exits), 3) if time_exits else 0

    # Fill-tracking des A_SETUP virtuels (audit 2026-06-17) : combien d'entrées
    # annoncées sont réellement atteignables avant le PnL.
    ai_pending = [s for s in j["signals"] if s["status"] == "PENDING"]
    ai_expired = [s for s in j["signals"] if s["status"] == "EXPIRED"
                  and s.get("fill_quality") not in ("CROSS_SOURCE", "NO_DATA")]
    ai_filled = [s for s in j["signals"] if s.get("trader") == "AI" and s.get("filled_ts")]
    n_filldecided = len(ai_filled) + len(ai_expired)
    fill_rate = round(len(ai_filled) / n_filldecided * 100, 1) if n_filldecided else None

    j["stats"] = {
        "total_signals": len(j["signals"]),
        "open": len([s for s in j["signals"] if s["status"] == "OPEN"]),
        "duplicates": len([s for s in j["signals"] if s.get("duplicate_of") or s.get("status") == "DUPLICATE"]),
        "closed": len(closed),
        "wins": len(wins),
        "losses": len(losses),
        "win_rate": wr(closed)[0],
        "time_exits": {"n": len(time_exits), "exp": te_exp},
        "costs_applied_n": len([s for s in closed if s.get("costs_applied")]),
        "avg_win_pct": avg_win,
        "avg_loss_pct": avg_loss,
        "expectancy_pct": expectancy,
        "by_score_band": by_band,
        "by_session": by_session,
        "by_asset": by_asset,
        "by_adx": by_adx,
        "ai_pending": len(ai_pending),
        "ai_expired_nofill": len(ai_expired),
        "ai_fill_rate": fill_rate,
        "scope": "IA seulement, hors session WEEKEND (audit 07-03)",
        "weekend_ghosts_exclus": len(weekend_ghosts),
        "user": {
            "n": len(user_closed),
            "win_rate": (round(sum(1 for s in user_closed if (s["pnl_pct"] or 0) > 0)
                               / len(user_closed) * 100, 1) if user_closed else None),
            "expectancy_pct": (round(sum(s["pnl_pct"] or 0 for s in user_closed)
                                     / len(user_closed), 3) if user_closed else None),
        },
    }


def performance_report() -> str:
    j = load_journal()
    _recompute_stats(j)
    save_journal(j)
    st = j["stats"]
    if not st or st.get("closed", 0) == 0:
        n_open = st.get("open", 0) if st else 0
        return (f"  📓 JOURNAL : {n_open} signaux ouverts, 0 clôturé.\n"
                f"     (les stats apparaîtront dès que des signaux toucheront TP/Stop)")

    def fmt(t):
        return f"{t[0]}% ({t[1]})" if t and t[0] is not None else "-"

    out = []
    out.append(f"  📓 JOURNAL DE TRADING, Performance réelle (forward-test)")
    out.append(f"     Signaux: {st['total_signals']} | Ouverts: {st['open']} | Clôturés: {st['closed']}"
               f" | Doublons exclus: {st.get('duplicates', 0)}")
    out.append(f"     ✅ Win rate TP/SL : {st['win_rate']}%  ({st['wins']}W / {st['losses']}L)")
    te = st.get("time_exits") or {}
    if te.get("n"):
        out.append(f"     ⏱  Sorties horizon (hors WR): n={te['n']} exp {te['exp']:+.3f}%")
    if st.get("costs_applied_n") is not None:
        out.append(f"     💸 Coûts appliqués sur {st['costs_applied_n']}/{st['closed']} clôturés"
                   f" (l'historique sera re-simulé par resim_report)")
    out.append(f"     💰 Gain moy: {st['avg_win_pct']}%  |  Perte moy: {st['avg_loss_pct']}%  |  Espérance: {st['expectancy_pct']}%/trade")
    out.append(f"     Par score : " + "  ".join(f"{k}:{fmt(v)}" for k, v in st["by_score_band"].items()))
    out.append(f"     Par ADX   : " + "  ".join(f"{k}:{fmt(v)}" for k, v in st["by_adx"].items()))
    if st["by_session"]:
        out.append(f"     Par session: " + "  ".join(f"{k}:{fmt(v)}" for k, v in st["by_session"].items()))
    if st["by_asset"]:
        out.append(f"     Par actif : " + "  ".join(f"{k}:{fmt(v)}" for k, v in st["by_asset"].items()))
    return "\n".join(out)


def log_real_trade(asset, direction, entry, stop, tp1, tp2=None, note="",
                   trader="USER", comment="", valid_hours=None, invalidation=""):
    """
    Enregistre un trade. trader='USER' (exécution réelle) ou 'AI' (reco moteur).
    comment = contexte/remarques. valid_hours = durée de validité du setup.
    """
    j = load_journal()
    now = datetime.datetime.now(datetime.timezone.utc)
    valid_until = None
    if valid_hours:
        valid_until = (now + datetime.timedelta(hours=valid_hours)).isoformat()
    sig = {
        "id":        f"{trader}_{asset}_{int(time.time())}",
        "ts":        now.isoformat(),
        "paris":     paris_now().strftime("%Y-%m-%d %H:%M"),
        "asset":     asset, "direction": direction, "score": None,
        "entry":     round(entry, 2), "stop": round(stop, 2),
        "tp1":       round(tp1, 2), "tp2": round(tp2, 2) if tp2 else None,
        "rsi": None, "adx": None, "stoch_k": None,
        "session":   "REAL" if trader == "USER" else "AI", "vix": None, "dxy": None,
        "status":    "OPEN", "result": None, "exit_price": None, "pnl_pct": None,
        "hi_since":  round(entry, 2), "lo_since": round(entry, 2),
        "mfe_pct":   0.0, "mae_pct": 0.0,
        "source":    "REAL_TRADE" if trader == "USER" else "AI_SIGNAL",
        "trader":    trader,
        "comment":   comment or note,
        "valid_hours": valid_hours,
        "valid_until": valid_until,
        "invalidation": invalidation,
        "note": note,
    }
    j["signals"].append(sig)
    save_journal(j)
    return sig["id"]


def log_pending_setup(asset, direction, entry, stop, tp, score=None, strategy=None,
                      session=None, valid_minutes=45, adx=None, price_source=None, rr=None,
                      entry_mode=None):
    """Enregistre un A_SETUP émis par le watcher comme trade VIRTUEL EN ATTENTE
    de remplissage à l'entrée annoncée (audit 2026-06-17 : fermer le nerf de
    mesure). evaluate_open le passe à OPEN si le prix touche l'entrée dans
    valid_minutes (sinon EXPIRED). Anti-doublon : un PENDING/OPEN identique
    (asset/dir, entrée à 0.15%) bloque le re-log à chaque cycle."""
    j = load_journal()
    now = datetime.datetime.now(datetime.timezone.utc)
    for s in j["signals"]:
        if (s["asset"] == asset and s["direction"] == direction
                and s["status"] in ("PENDING", "OPEN") and s.get("trader") == "AI"
                and entry and s.get("entry") and abs(s["entry"] - entry) / entry < 0.0015):
            return None  # déjà suivi
    sig = {
        "id":        f"AI_{asset}_{int(time.time())}",
        "ts":        now.isoformat(),
        "trigger_ts": now.isoformat(),
        "paris":     paris_now().strftime("%Y-%m-%d %H:%M"),
        "asset":     asset, "direction": direction, "score": score,
        "entry":     round(entry, 2), "stop": round(stop, 2),
        "tp1":       round(tp, 2), "tp2": None, "rr": rr,   # rr journalisé (observabilité capture)
        "rsi": None, "adx": adx, "stoch_k": None,
        "session":   session or "AI", "vix": None, "dxy": None,
        "status":    "PENDING", "result": None, "exit_price": None, "pnl_pct": None,
        "hi_since":  round(entry, 2), "lo_since": round(entry, 2),
        "mfe_pct":   0.0, "mae_pct": 0.0,
        "source":    "AI_SIGNAL", "trader": "AI", "strategy": strategy,
        "price_source": price_source,   # réf de prix de l'entrée -> anti cross-source au fill
        "entry_mode": entry_mode,   # MARKET_TREND / OTE_CAPPED / OTE (audit 07-02 :
        #                             sans ce champ, le fill n'est pas attribuable au fix 22/06)
        "entry_deadline": (now + datetime.timedelta(minutes=valid_minutes)).isoformat(),
        "comment": "", "note": "",
    }
    j["signals"].append(sig)
    save_journal(j)
    return sig["id"]


def confidence_modifier(asset, score, session, adx) -> tuple:
    """
    Retourne (modificateur, raison) basé sur la performance historique réelle.
    Utilisé pour ajuster la confiance d'un nouveau signal.
    """
    j = load_journal()
    st = j.get("stats", {})
    if not st or st.get("closed", 0) < 8:
        return (0.0, "données insuffisantes (<8 trades)")

    mods, reasons = 0.0, []
    # Score band
    band = "8-10" if score >= 8 else "7-8" if score >= 7 else "6-7" if score >= 6 else "<6"
    bwr = st.get("by_score_band", {}).get(band)
    if bwr and bwr[1] >= 4 and bwr[0] is not None:
        if bwr[0] >= 65:
            mods += 0.4; reasons.append(f"score {band} historiquement {bwr[0]}%")
        elif bwr[0] <= 40:
            mods -= 0.4; reasons.append(f"score {band} faible {bwr[0]}%")
    # ADX
    adx_band = ">30" if (adx or 0) >= 30 else "20-30" if (adx or 0) >= 20 else "<20"
    awr = st.get("by_adx", {}).get(adx_band)
    if awr and awr[1] >= 4 and awr[0] is not None:
        if awr[0] >= 65:
            mods += 0.3; reasons.append(f"ADX {adx_band} historiquement {awr[0]}%")
        elif awr[0] <= 40:
            mods -= 0.3; reasons.append(f"ADX {adx_band} faible {awr[0]}%")
    return (round(mods, 2), "; ".join(reasons) if reasons else "neutre")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "report":
        print(performance_report())
    else:
        j = load_journal()
        print(json.dumps(j.get("stats", {}), indent=2))
