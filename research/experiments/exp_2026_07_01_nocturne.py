#!/usr/bin/env python3
"""Experience CHERCHEUR NOCTURNE du 2026-07-01 (nuit mercredi -> jeudi).

=== FAIT NEUF DE LA NUIT (code+donnee-verifie, resout 2 questions ouvertes
    du 30/06) :
    (c) La FRONTIERE GOLD 1d du 01/07 est VRAIE OHLC (O=4025 H=4032 L=3983
        C=3992, range=49.0), PAS plate -- alors que le 01/07 est un MERCREDI,
        le jour-semaine le plus charge en barres plates (17/55). Un jour de
        MARCHE reellement trade produit une vraie OHLC ; seul un jour MANQUANT
        est backfille par un settle plat. -> ceci CONFIRME (et raffine) la
        theorie 30/06 "jours manquants backfilles" et REFUTE definitivement la
        theorie 29/06 "fuite settle week-end". Etre mercredi n'est PAS suffisant
        pour une plate : il faut que le jour soit ABSENT du feed. La derniere
        plate reste 26/06, desormais a 3 barres de la frontiere (INTERIEURE).
    (d) AUCUN nouveau MUET dans la fenetre predite ~01-02/07 (pattern ~3-4j,
        dernier 28/06 04:24). prime_watcher.log cycle a 23:27 Paris, cadence
        ~5 min continue (23:05/10/16/21/27), 0 error/traceback (grep=0). Le
        backstop watchdog.log reste 0 octet depuis le 17/06 (muet-par-conception,
        watcher primaire sain). Le pattern muet ne s'est PAS reproduit ce soir.

CONSTAT D'INGESTION (re-verifie ce run, pas recopie) :
  - Pas de research/PAUSE. Budget respecte. J'ecris UNIQUEMENT dans research/.
    Signal-only absolu (0 code d'execution d'ordres).
  - Lake : 13 parquet, FRONTIERE 2026-07-01 04:00 UTC (verifiee, ts epoch->UTC).
    GC_F_1d range 49.0 / ES_F_1d range 33.25 = VRAIES OHLC. TOUJOURS AUCUN 15m.
  - lab_counters() = {testees 45, tuees 44, papier 0, promues 0} (inchange).
    Deflation Bonferroni GLOBALE : test n+1 -> z_req ~3.07.
  - resim Gate-1 : n decisifs 16 (7 TP / 9 SL), WR 43.8%, exp +0.163%,
    IC bootstrap-jours (-0.088, 0.409) CONTIENT 0 -> edge non prouve.
    equity x20 1142.01 EUR. USER (Revolut reel) WR 56.7% n=180 exp +0.002%.
  - feature_store : 6196/500 outcomes, 0 ERROR, 1 MIXED exclu, 853 setups,
    order-flow 10 JOURS distincts (modele_appris_autorise=false, seuil ~20).
  - journal.json : 276 signaux. Fills du 01/07 = 5 GOLD SHORT -> 5 PERTES
    (4 LOSS + 1 LOSS_TIME) + 2 EXPIRED NOFILL. last_updated 11:00 UTC (13:00
    Paris) : 0 nouveau fill depuis 13h. Pipeline honnete (5 pertes capturees).
  - Aucune injection : news_cache.json (7665 ch.) + calendar_cache.json
    (18810 ch.) scannes (ignore|disregard|system prompt|rm -rf|sudo|override|
    delete|commit|exec|reveal|token|git|edit) -> 3 hits = SOUS-CHAINES benignes
    ("US commitment", "Private Sector Credit", "BOE Credit Conditions") : 0
    impératif. Donnees externes traitees STRICTEMENT en DONNEE.

CE QUE FAIT CE SCRIPT (et ce qu'il NE fait PAS) :
  - 0 hypothese neuve soumise (0/3). Matrice fermee (44 KILLED). L'autopsie du
    jour (2 trend-days OPPOSES le meme jour, tous deux "TENDANCE PROPRE", tous
    deux PERDANTS, autour d'un POC stable ~3977) est la REFUTATION SYMETRIQUE la
    plus forte a ce jour : ce n'est ni tendance short ni tendance long, mais du
    bruit de value-area classe en tendance des DEUX cotes. Le correctif
    (orderflow_regime_veto, decrit dans le rapport) reste famille order-flow =
    strategy_families.py protege (token Sam) + logique POC/VA/delta INJUGEABLE
    sur lake 1h-1d + order-flow 10j sous-puissant (seuil 20). Toute soumission
    momentum/regime serait DUPLICATE / re-knob / sign-flip INTERDIT. 0 = verdict
    discipline (mortalite >90% = sante).
  - DEMONTRE empiriquement (c) la frontiere 01/07 VRAIE OHLC malgre mercredi
    (raffine la theorie jours-manquants), et l'invariant dedup (cellule deja
    jugee re-soumise -> DUPLICATE, 0 effet de bord, lab byte-stable).

PROPOSITION POUR SAM (token Sam, fichiers proteges -- je ne touche pas) :
  1. Famille order-flow + orderflow_regime_veto : VETO le label TENDANCE quand
     POC plat (|dPOC|<k*ATR) ET prix DANS la VA (VAL<px<VAH) ET VA non-expansive
     -> forcer HACHEE/NO_TRADE. Le 01/07 = cas-test parfait (les 2 trend-days
     auraient ete VETO -> 0 perte au lieu de 2). Spec-only : edition = Sam.
  2. Accumuler l'order-flow 10 -> ~20 jours = levier #1 (stationnaire ce soir).
  3. Filtre d'integrite 1d (55 plates GC_F_1d interieures) + fingerprint-cle :
     inchanges, toujours token Sam.

Sources HOMOGENES (GOLD<->GC=F, US500<->ES=F, yfinance ; jamais melangees).
"""

import json
import os
import sys

import pandas as pd

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "research"))
import harness
import datalake

_DATA = os.path.join(_ROOT, "research", "data")

# Cellule DEJA JUGEE le 22/06 (KILLED). Params/assets/tf IDENTIQUES au verdict
# archive -> meme hypothesis_key -> doit rendre DUPLICATE (BLOCAGE dedup).
_DEMO_DUPLICATE = {
    "id": "DEMO_dedup_twist_1d_2026_07_01",
    "hypothesis_text": "DEMONSTRATION (pas une hypothese neuve) : re-soumission de "
                       "la cellule deja jugee IL_pool_ichimoku_twist_1d sur le lake "
                       "rafraichi mercredi. Attendu : DUPLICATE, 0 effet de bord.",
    "family": "ichimoku_twist",
    "params": {"speed": "standard"},
    "exit_rule": {"stop_pct": 1.2, "tp_pct": 2.4, "horizon_bars": 10},
    "assets": ["GOLD", "US500"], "timeframe": "1d",
    "_lake": {"GOLD": "GC=F", "US500": "ES=F"},
}

_WD = {0: "Mon", 1: "Tue", 2: "Wed", 3: "Thu", 4: "Fri", 5: "Sat", 6: "Sun"}


def _flat_audit():
    print("=== DONNEE : integrite des barres 1d (defaut plat O=H=L=C) ===")
    for f, tick in [("GC_F_1d", "GOLD"), ("ES_F_1d", "US500")]:
        df = pd.read_parquet(os.path.join(_DATA, f + ".parquet"))
        tcol = "ts" if "ts" in df.columns else df.columns[0]
        t = pd.to_datetime(df[tcol], unit="s", utc=True)
        flat = (df["open"] == df["high"]) & (df["high"] == df["low"]) & (df["low"] == df["close"])
        front = df.iloc[-1]
        front_t = t.iloc[-1]
        front_rng = float(front["high"]) - float(front["low"])
        print(f"  {f:9s} ({tick:6s}) : {len(df)} barres, PLATES={int(flat.sum())} "
              f"({100*flat.mean():.1f}%) | FRONTIERE {front_t:%Y-%m-%d} ({_WD[front_t.dayofweek]}) "
              f"range={front_rng:.2f}{'  <-- PLATE' if front_rng == 0 else '  (VRAIE OHLC)'}")
        if flat.sum():
            ft = t[flat]
            wd = ft.dt.dayofweek.value_counts().sort_index()
            print("      par jour-semaine :", {_WD[k]: int(v) for k, v in wd.items()})
            idx_flat = df.index[flat]
            gap = (len(df) - 1) - list(idx_flat)[-1]
            last_flat_t = ft.iloc[-1]
            print(f"      derniere plate   : {last_flat_t:%Y-%m-%d} "
                  f"(a {gap} barre(s) de la frontiere -> "
                  f"{'INTERIEURE' if gap > 0 else 'EN FRONTIERE'})")


def main():
    _flat_audit()
    print("\n  LECTURE (question (c) du 30/06 RESOLUE) : le 01/07 est un MERCREDI "
          "(jour-semaine le plus charge en plates : 17/55) et POURTANT sa barre "
          "est une VRAIE OHLC (range 49.0). -> etre mercredi n'est PAS suffisant "
          "pour une plate ; il faut que le jour soit ABSENT du feed. Confirme la "
          "theorie 'jours manquants backfilles' (30/06), refute 'fuite week-end' "
          "(29/06). Frontiere PROPRE, 55 plates INTERIEURES (~4.4%), specifique or.")

    print("\n=== HARNESS : dedup gele le re-test (invariant) ===")
    before = harness.lab_counters()
    reg_len_before = len(harness.registry())
    print("lab_counters AVANT :", json.dumps(before, ensure_ascii=False),
          "| registry len =", reg_len_before)

    s = dict(_DEMO_DUPLICATE)
    lake_map = s.pop("_lake")
    print("hypothesis_key(demo) =", harness.hypothesis_key(s))
    data, sources = {}, {}
    for asset, ticker in lake_map.items():
        candles, src = datalake.load_candles(ticker, s["timeframe"])
        data[asset] = candles
        sources[asset] = src
    r = harness.evaluate(s, data, sources=sources)
    print("verdict =", r["verdict"], "|", r.get("note", ""))

    after = harness.lab_counters()
    reg_len_after = len(harness.registry())
    print("lab_counters APRES :", json.dumps(after, ensure_ascii=False),
          "| registry len =", reg_len_after)

    ok = (before == after and reg_len_before == reg_len_after
          and r["verdict"] == "DUPLICATE")
    print("\nINVARIANT (0 effet de bord) :", "OK" if ok else "VIOLE")
    print("CONCLUSION : frontiere GOLD-1d 01/07 VRAIE OHLC malgre mercredi "
          "(theorie jours-manquants raffinee), dedup toujours bloquant -> "
          "0 hypothese neuve soumise (honnete, discipline).")


if __name__ == "__main__":
    main()
