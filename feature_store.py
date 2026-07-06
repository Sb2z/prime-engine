#!/usr/bin/env python3
"""FEATURE STORE, chaque cycle du watcher devient une ligne requêtable.

Les poids de forecast.py (0.55/0.30/0.15) sont inventés à la main. Tant que
les snapshots ne sont pas persistés AVEC leur outcome réalisé, impossible
d'apprendre quoi que ce soit. Ici :

  features  : une ligne par cycle x actif (prix, forecast tf, régime, radar,
              calendrier macro, décision Prime, + colonnes réservées order
              flow/COT remplies par les phases A2/A4)
  outcomes  : rendement réalisé à +15m / +1h / +4h, backfillé via les
              bougies 1m du datafeed

Gate 3 (mission V2) : AUCUN apprentissage avant 500 lignes exploitables
(features avec outcome complet). `stats()` affiche le compteur.

DuckDB mono-writer : le watcher est le SEUL processus écrivain ; toute
lecture externe doit ouvrir en read_only (cf. connect(read_only=True)).
"""

import datetime as dt
import json
import os

import duckdb

DB_FILE = "/Users/sam/trading/prime.duckdb"
EXPORT_DIR = "/Users/sam/trading/feature_exports"
MIN_ROWS_FOR_LEARNING = 500
MIN_ORDERFLOW_DAYS = 15   # jours-semaine DISTINCTS d'order-flow avant tout 1er modèle
#                           appris (les lignes du gate sont autocorrélées ; ce sont les
#                           JOURS indépendants qui comptent contre l'overfit, analyse 06-19)

HORIZONS = {"ret_15m": 15 * 60, "ret_1h": 3600, "ret_4h": 4 * 3600}
TOLERANCE_S = 180  # bougie acceptée à ±3 min de l'horizon
CANDLE_1M_BARS = 330                    # profondeur du fetch 1m (~5.5h connue)
CANDLE_WINDOW_S = CANDLE_1M_BARS * 60   # un ret_Xh n'est calculable que si
#                                         ts+Xh tombe dans cette fenêtre vivante

SCHEMA = """
CREATE TABLE IF NOT EXISTS features (
    ts TIMESTAMPTZ,
    asset VARCHAR,
    session VARCHAR,
    price DOUBLE,
    grade VARCHAR,
    conf DOUBLE,
    direction VARCHAR,
    rr DOUBLE,
    entry DOUBLE,
    stop DOUBLE,
    tp DOUBLE,
    strategy VARCHAR,
    regime VARCHAR,
    vetoes VARCHAR,
    forecast_dir VARCHAR,
    tf_15m DOUBLE,
    tf_1h DOUBLE,
    tf_4h DOUBLE,
    radar_alert VARCHAR,
    gold_bias INTEGER,
    spx_bias INTEGER,
    fear_greed INTEGER,
    macro_cal_mode VARCHAR,
    surprise_z DOUBLE,
    edge_label VARCHAR,
    -- réservées aux phases A2 (order flow) et A4 (COT) :
    of_delta DOUBLE,
    of_imbalance DOUBLE,
    of_poc_dist DOUBLE,
    cot_pctile DOUBLE,
    raw JSON,
    price_source VARCHAR,
    PRIMARY KEY (ts, asset)
);
CREATE TABLE IF NOT EXISTS outcomes (
    ts TIMESTAMPTZ,
    asset VARCHAR,
    ret_15m DOUBLE,
    ret_1h DOUBLE,
    ret_4h DOUBLE,
    filled_at TIMESTAMPTZ,
    outcome_source VARCHAR,
    outcome_quality VARCHAR,
    PRIMARY KEY (ts, asset)
);
ALTER TABLE features ADD COLUMN IF NOT EXISTS price_source VARCHAR;
ALTER TABLE outcomes ADD COLUMN IF NOT EXISTS outcome_source VARCHAR;
ALTER TABLE outcomes ADD COLUMN IF NOT EXISTS outcome_quality VARCHAR;
ALTER TABLE features ADD COLUMN IF NOT EXISTS btc_imbalance DOUBLE;
ALTER TABLE features ADD COLUMN IF NOT EXISTS btc_delta_5m DOUBLE;
ALTER TABLE features ADD COLUMN IF NOT EXISTS crypto_risk VARCHAR;
-- Ichimoku (11/06/2026) : enregistrement sans décision, cf. ichimoku.py.
-- Valeurs connues à t (Senkou décalé), anti-lookahead prouvé par test_ichimoku.py.
ALTER TABLE features ADD COLUMN IF NOT EXISTS ichi15_pos INTEGER;
ALTER TABLE features ADD COLUMN IF NOT EXISTS ichi15_d_tenkan DOUBLE;
ALTER TABLE features ADD COLUMN IF NOT EXISTS ichi15_d_kijun DOUBLE;
ALTER TABLE features ADD COLUMN IF NOT EXISTS ichi15_d_cloud DOUBLE;
ALTER TABLE features ADD COLUMN IF NOT EXISTS ichi15_kumo_atr DOUBLE;
ALTER TABLE features ADD COLUMN IF NOT EXISTS ichi15_tk_atr DOUBLE;
ALTER TABLE features ADD COLUMN IF NOT EXISTS ichi15_twist_age INTEGER;
ALTER TABLE features ADD COLUMN IF NOT EXISTS ichi15_chikou INTEGER;
ALTER TABLE features ADD COLUMN IF NOT EXISTS ichi1h_pos INTEGER;
ALTER TABLE features ADD COLUMN IF NOT EXISTS ichi1h_d_tenkan DOUBLE;
ALTER TABLE features ADD COLUMN IF NOT EXISTS ichi1h_d_kijun DOUBLE;
ALTER TABLE features ADD COLUMN IF NOT EXISTS ichi1h_d_cloud DOUBLE;
ALTER TABLE features ADD COLUMN IF NOT EXISTS ichi1h_kumo_atr DOUBLE;
ALTER TABLE features ADD COLUMN IF NOT EXISTS ichi1h_tk_atr DOUBLE;
ALTER TABLE features ADD COLUMN IF NOT EXISTS ichi1h_twist_age INTEGER;
ALTER TABLE features ADD COLUMN IF NOT EXISTS ichi1h_chikou INTEGER;
"""

# Au-delà de cet âge, un outcome encore vide est rempli avec la source
# disponible même différente (marqué MIXED) plutôt que perdu : la fenêtre
# des bougies 1m (330 barres ≈ 5h30) est sur le point d'être dépassée.
MIXED_DEADLINE_S = 5 * 3600

_conn_cache = None


def connect(read_only=False):
    global _conn_cache
    if _conn_cache is not None:
        # Ce process est déjà writer : DuckDB refuse une 2e config sur le même
        # fichier, on réutilise la connexion existante (lecture incluse).
        return _conn_cache
    if read_only:
        return duckdb.connect(DB_FILE, read_only=True)
    _conn_cache = duckdb.connect(DB_FILE)
    _conn_cache.execute(SCHEMA)
    return _conn_cache


def _release(con):
    """Ferme une connexion seulement si elle n'est pas la writer du process."""
    if con is not _conn_cache:
        con.close()


def _orderflow_features(of, price):
    """3 features order-flow persistables, dérivées du payload compact threadé dans
    la décision (prime_strategy._of_compact : poc/vah/val/recent_delta), foundation
    A2 câblée 2026-06-18. None si données absentes :
      • of_delta    : delta cumulé récent (pression acheteur/vendeur, proxy bougies).
                      Échelle brute (dépend du volume / mode TIME|VOLUME) -> le modèle
                      standardisera par feature ; normalisation à affiner plus tard.
      • of_imbalance: position dans la Value Area (price-VAL)/(VAH-VAL), <0 sous la
                      valeur (vendeur), >1 au-dessus (acheteur). Déséquilibre VP, normalisé.
      • of_poc_dist : distance signée au POC (aimant volume), en fraction du prix."""
    if not of or not price:
        return None, None, None
    of_delta = of.get("recent_delta")
    poc = of.get("poc")
    of_poc_dist = round((price - poc) / price, 5) if poc else None
    val, vah = of.get("val"), of.get("vah")
    of_imbalance = (round((price - val) / (vah - val), 4)
                    if (val is not None and vah is not None and vah > val) else None)
    return of_delta, of_imbalance, of_poc_dist


def record_cycle(data):
    """Persiste une ligne par actif depuis la sortie de prime_strategy.evaluate()."""
    con = connect()
    ts = dt.datetime.now(dt.timezone.utc)
    radar = data.get("radar") or {}
    fg = (radar.get("fear_greed") or {}).get("score")
    cal = radar.get("macro_calendar") or {}
    edge = (data.get("adaptive_edge_policy") or {}).get("label")
    # Capteurs contextuels (cache interne : COT 24h, crypto 60s, pas de
    # martèlement réseau dans la boucle)
    try:
        import crypto_pulse
        crypto = crypto_pulse.snapshot() or {}
    except Exception:
        crypto = {}

    n = 0
    for d in data.get("decisions") or []:
        setup = d.get("setup") or {}
        tf = d.get("forecast_tf") or {}
        try:
            import cot_feed
            cot = cot_feed.snapshot(d.get("asset")) or {}
        except Exception:
            cot = {}
        try:
            import adaptive_edge
            session = adaptive_edge.current_session(d.get("asset"))
        except Exception:
            session = None
        # MARCHÉ FERMÉ (week-end) : prix figé → ligne polluante (le gap de
        # réouverture serait compté comme un move 15m/1h/4h, ~10x l'amplitude
        # normale). On NE l'enregistre PAS (audit 2026-06-17). Robuste : session
        # WEEKEND ou, à défaut, samedi/dimanche UTC.
        if session == "WEEKEND" or (session is None and ts.weekday() >= 5):
            continue
        # Ichimoku : enregistrement pur (échec → colonnes NULL, cycle intact)
        try:
            import ichimoku
            ichi = ichimoku.snapshot(d.get("asset")) or {}
        except Exception:
            ichi = {}
        # Les prix des décisions viennent des moteurs aurum/sentinel500,
        # branchés TradingView uniquement. La basis futures/CFD (~0.24% sur
        # ES=F vs CFD) est plus grosse qu'un move 15m : le backfill des
        # outcomes DOIT utiliser la même source (sinon outcome_quality=MIXED,
        # exclu du gate des 500 lignes).
        price_source = d.get("price_source") or "tradingview"
        of_delta, of_imbalance, of_poc_dist = _orderflow_features(
            d.get("orderflow"), d.get("price"))
        con.execute(
            "INSERT OR REPLACE INTO features "
            "(ts, asset, session, price, grade, conf, direction, rr, entry, stop, tp, "
            " strategy, regime, vetoes, forecast_dir, tf_15m, tf_1h, tf_4h, radar_alert, "
            " gold_bias, spx_bias, fear_greed, macro_cal_mode, surprise_z, edge_label, "
            " of_delta, of_imbalance, of_poc_dist, cot_pctile, raw, price_source, "
            " btc_imbalance, btc_delta_5m, crypto_risk, "
            " ichi15_pos, ichi15_d_tenkan, ichi15_d_kijun, ichi15_d_cloud, "
            " ichi15_kumo_atr, ichi15_tk_atr, ichi15_twist_age, ichi15_chikou, "
            " ichi1h_pos, ichi1h_d_tenkan, ichi1h_d_kijun, ichi1h_d_cloud, "
            " ichi1h_kumo_atr, ichi1h_tk_atr, ichi1h_twist_age, ichi1h_chikou) VALUES "
            "(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,"
            "?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            [
                ts, d.get("asset"), session, d.get("price"),
                d.get("grade"), setup.get("conf"), setup.get("direction"),
                setup.get("rr"), setup.get("entry"), setup.get("stop"),
                setup.get("tp"), setup.get("strategy"),
                d.get("regime"), json.dumps(d.get("vetoes") or [], ensure_ascii=False),
                d.get("forecast_direction"),
                tf.get("15m"), tf.get("1h"), tf.get("4h"),
                radar.get("alert"), radar.get("gold_bias"), radar.get("spx_bias"),
                fg, cal.get("mode"), cal.get("surprise_z"),
                edge,
                of_delta, of_imbalance, of_poc_dist,  # order-flow (foundation A2, câblé 06-18)
                cot.get("pctile_3y"),
                json.dumps({"radar_msg": radar.get("message"),
                            "vetoes": d.get("vetoes"),
                            "adaptive_edge": d.get("adaptive_edge"),
                            "cal_detail": cal.get("detail"),
                            "cot": cot or None}, ensure_ascii=False),
                price_source,
                crypto.get("btc_imbalance"), crypto.get("btc_delta_5m"),
                crypto.get("crypto_risk"),
                ichi.get("ichi15_pos"), ichi.get("ichi15_d_tenkan"),
                ichi.get("ichi15_d_kijun"), ichi.get("ichi15_d_cloud"),
                ichi.get("ichi15_kumo_atr"), ichi.get("ichi15_tk_atr"),
                ichi.get("ichi15_twist_age"), ichi.get("ichi15_chikou"),
                ichi.get("ichi1h_pos"), ichi.get("ichi1h_d_tenkan"),
                ichi.get("ichi1h_d_kijun"), ichi.get("ichi1h_d_cloud"),
                ichi.get("ichi1h_kumo_atr"), ichi.get("ichi1h_tk_atr"),
                ichi.get("ichi1h_twist_age"), ichi.get("ichi1h_chikou"),
            ],
        )
        n += 1
    return n


def _price_at(candles, target_epoch):
    """Close de la bougie 1m la plus proche de target_epoch (±TOLERANCE_S)."""
    best, best_gap = None, TOLERANCE_S + 1
    for b in candles:
        gap = abs(b[0] - target_epoch)
        if gap < best_gap:
            best, best_gap = b, gap
    return float(best[4]) if best else None


def backfill_outcomes(max_rows=400):
    """Remplit ret_15m/1h/4h pour les features dont l'horizon est atteint.

    Règle de cohérence : un outcome n'est calculé qu'avec des bougies de la
    MÊME source que la ligne d'origine (la basis futures/CFD fausserait le
    rendement). Si la source ne matche pas, on réessaie au cycle suivant ;
    passé MIXED_DEADLINE_S (la fenêtre 1m va se refermer), on remplit avec
    la source disponible mais outcome_quality=MIXED → exclu du gate des 500.

    SÉLECTION BORNÉE À LA FENÊTRE VIVANTE (corrige le bug ret_4h du 10-13/06) :
    une ligne ne peut recevoir son ret_4h que tant que ts+4h tombe dans les
    CANDLE_1M_BARS dernières barres, soit ts ≥ now-(4h+fenêtre) ≈ now-9.5h.
    L'ancien ORDER BY ts DESC LIMIT N prenait les N lignes les plus JEUNES
    (toutes < 4h, donc sans ret_4h possible) et n'atteignait JAMAIS la tranche
    4h-9.5h : le ret_4h était affamé en permanence. On borne donc à la fenêtre
    vivante et on trie du plus ANCIEN au plus jeune (les plus proches de sortir
    de la fenêtre traités d'abord). max_rows couvre tout le backlog en fenêtre
    (~200 lignes/jour), donc chaque cycle tente chaque ligne encore calculable.
    """
    import datafeed
    con = connect()
    now = dt.datetime.now(dt.timezone.utc)
    oldest_fillable = now - dt.timedelta(
        seconds=HORIZONS["ret_4h"] + CANDLE_WINDOW_S)
    rows = con.execute(
        """
        SELECT f.ts, f.asset, f.price, f.price_source
        FROM features f LEFT JOIN outcomes o USING (ts, asset)
        WHERE f.price IS NOT NULL
          AND (o.ts IS NULL OR o.ret_4h IS NULL)
          AND f.ts <= ?
          AND f.ts >= ?
        ORDER BY f.ts ASC
        LIMIT ?
        """,
        [now - dt.timedelta(seconds=HORIZONS["ret_15m"]),
         oldest_fillable, max_rows],
    ).fetchall()
    if not rows:
        return 0

    feeds = {}  # asset → {"candles": [...], "source": ...}
    for asset in {r[1] for r in rows}:
        c = datafeed.get_candles(asset, "1m", CANDLE_1M_BARS)
        if c and not c.get("stale"):
            feeds[asset] = c

    filled = 0
    for ts, asset, price, price_source in rows:
        feed = feeds.get(asset)
        if not feed or not price:
            continue
        same_source = feed["source"] == (price_source or "tradingview")
        past_deadline = (now - ts).total_seconds() > MIXED_DEADLINE_S
        if not same_source and not past_deadline:
            continue  # on retente au prochain cycle avec la bonne source
        quality = "OK" if same_source else "MIXED"

        base_epoch = ts.timestamp()
        vals = {}
        for col, horizon_s in HORIZONS.items():
            if (now - ts).total_seconds() < horizon_s:
                vals[col] = None
                continue
            px = _price_at(feed["candles"], base_epoch + horizon_s)
            vals[col] = round((px - price) / price * 100, 4) if px else None
        if all(v is None for v in vals.values()):
            continue

        # Fusion avec l'existant en python (la qualité retient le pire)
        old = con.execute(
            "SELECT ret_15m, ret_1h, ret_4h, outcome_quality FROM outcomes "
            "WHERE ts=? AND asset=?", [ts, asset]
        ).fetchone()
        if old:
            for i, col in enumerate(("ret_15m", "ret_1h", "ret_4h")):
                if vals[col] is None:
                    vals[col] = old[i]
            if old[3] == "MIXED":
                quality = "MIXED"
        con.execute(
            "INSERT OR REPLACE INTO outcomes VALUES (?,?,?,?,?,?,?,?)",
            [ts, asset, vals["ret_15m"], vals["ret_1h"], vals["ret_4h"],
             now, feed["source"], quality],
        )
        filled += 1
    return filled


_weekend_purged = False


def _purge_weekend_rows(con):
    """Purge ONE-SHOT (par process) des lignes de marché FERMÉ (audit 03-07) :
    1 028 lignes du week-end 13-14/06 (prix 100% figé, antérieures à la garde
    du 17/06) + la queue du vendredi 12/06 23h (déjà figée). Elles créaient un
    faux saut de +1,87% « en 5,7 min » à la réouverture et 2 faux jours
    distincts. La garde de record_cycle empêche toute nouvelle ligne week-end."""
    global _weekend_purged
    if _weekend_purged:
        return
    for t in ("features", "outcomes"):
        con.execute(f"DELETE FROM {t} WHERE strftime(ts, '%w') IN ('0', '6')")
        con.execute(f"DELETE FROM {t} WHERE CAST(ts AS DATE) = DATE '2026-06-12' "
                    f"AND EXTRACT(hour FROM ts) = 23")
    con.execute("DELETE FROM features WHERE session = 'WEEKEND'")
    _weekend_purged = True


def export_parquet():
    os.makedirs(EXPORT_DIR, exist_ok=True)
    con = connect()
    try:
        _purge_weekend_rows(con)
    except Exception:
        pass  # la purge ne doit jamais bloquer l'export
    for table in ("features", "outcomes"):
        path = os.path.join(EXPORT_DIR, f"{table}.parquet")
        # export ATOMIQUE (audit 07-02) : COPY écrivait EN PLACE -> les lecteurs
        # concurrents (edge_zone, capture Telegram, analyste) pouvaient lire un
        # fichier tronqué et faire échouer une capture de trade.
        tmp = path + ".tmp_export"
        con.execute(f"COPY {table} TO '{tmp}' (FORMAT PARQUET)")
        os.replace(tmp, path)
    _release(con)
    return EXPORT_DIR


def stats():
    source = "duckdb"
    try:
        con = connect(read_only=True)
        feat_rel, out_rel = "features", "outcomes"
    except duckdb.IOException:
        # Le watcher (writer unique) tient le verrou : on lit l'export Parquet
        # qu'il régénère à chaque cycle.
        fp = os.path.join(EXPORT_DIR, "features.parquet")
        op = os.path.join(EXPORT_DIR, "outcomes.parquet")
        if not (os.path.exists(fp) and os.path.exists(op)):
            return {"error": "base verrouillée par le watcher et pas encore d'export parquet"}
        con = duckdb.connect()
        feat_rel, out_rel = f"read_parquet('{fp}')", f"read_parquet('{op}')"
        source = "parquet_export"
    n_feat = con.execute(f"SELECT count(*) FROM {feat_rel}").fetchone()[0]
    # Gate des 500 : les TROIS horizons remplis (le 15m est celui du scalp,
    # une ligne sans lui n'apprend rien d'utile) ET même source que l'origine
    # Exclut les lignes week-end (marché fermé, gap = faux move) du compteur
    # d'apprentissage (audit 2026-06-17).
    n_out = con.execute(
        f"SELECT count(*) FROM {out_rel} o JOIN {feat_rel} f USING (ts, asset) "
        f"WHERE o.ret_15m IS NOT NULL AND o.ret_1h IS NOT NULL "
        f"AND o.ret_4h IS NOT NULL AND o.outcome_quality = 'OK' "
        f"AND (f.session IS NULL OR f.session <> 'WEEKEND')"
    ).fetchone()[0]
    # Compteur HONNÊTE distinct : décisions A_SETUP/WATCH avec outcome (le n qui
    # compte pour apprendre une politique d'entrée, bien < lignes de marché).
    n_setups = con.execute(
        f"SELECT count(*) FROM {out_rel} o JOIN {feat_rel} f USING (ts, asset) "
        f"WHERE o.ret_4h IS NOT NULL AND o.outcome_quality = 'OK' "
        f"AND f.grade IN ('A_SETUP', 'WATCH') "
        f"AND (f.session IS NULL OR f.session <> 'WEEKEND')"
    ).fetchone()[0]
    # Jours-semaine DISTINCTS avec order-flow peuplé : les jours INDÉPENDANTS (pas les
    # lignes autocorrélées du gate) -> seuil anti-overfit du 1er modèle appris (06-19).
    n_of_days = con.execute(
        f"SELECT count(DISTINCT CAST(ts AS DATE)) FROM {feat_rel} "
        f"WHERE of_delta IS NOT NULL AND (session IS NULL OR session <> 'WEEKEND')"
    ).fetchone()[0]
    n_mixed = con.execute(
        f"SELECT count(*) FROM {out_rel} WHERE outcome_quality = 'MIXED'"
    ).fetchone()[0]
    by_grade = dict(con.execute(
        f"SELECT grade, count(*) FROM {feat_rel} GROUP BY grade ORDER BY 2 DESC"
    ).fetchall())
    _release(con)
    return {
        "source": source,
        "features": n_feat,
        "outcomes_complets": n_out,
        "outcomes_mixed_exclus": n_mixed,
        "lignes_exploitables": n_out,
        "setups_avec_outcome": n_setups,
        "gate_apprentissage": f"{n_out}/{MIN_ROWS_FOR_LEARNING}",
        "apprentissage_autorise": n_out >= MIN_ROWS_FOR_LEARNING,
        "jours_order_flow_distincts": n_of_days,
        "modele_appris_autorise": n_of_days >= MIN_ORDERFLOW_DAYS,
        "par_grade": by_grade,
    }


if __name__ == "__main__":
    print(json.dumps(stats(), indent=2, ensure_ascii=False, default=str))
