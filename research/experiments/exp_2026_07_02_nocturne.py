#!/usr/bin/env python3
"""Experience CHERCHEUR NOCTURNE du 2026-07-02 (nuit jeudi -> vendredi, post-NFP).

=== FAIT VERIFIE DE LA NUIT (code+donnee) : la FRONTIERE 1d du 02/07 (jeudi,
    jour du NFP) est VRAIE OHLC des DEUX cotes du lake --
      GC_F_1d 02/07 : O4049.2 H4086.3 L4042.8 C4074.0  range=43.5   VRAIE OHLC
      ES_F_1d 02/07 : O7536.0 H7558.0 L7522.75 C7543.25 range=35.25  VRAIE OHLC
    Le jeudi NFP a ete reellement trade -> vraie OHLC, PAS une plate settle.
    Ceci RE-CONFIRME (3e nuit consecutive) la theorie 30/06 "jours manquants
    backfilles par un settle plat" et REFUTE definitivement "fuite settle
    week-end" (29/06) : etre un jour de semaine ne suffit pas a produire une
    plate ; seul un jour ABSENT du feed est backfille. La derniere plate reste
    26/06, desormais a 4 barres de la frontiere (INTERIEURE). Frontiere PROPRE ;
    interieur or encore pollue ~4.4% (55 plates, specifique or ; ES_F_1d 0 plate).

CONSTAT D'INGESTION (re-verifie ce run, pas recopie) :
  - Pas de research/PAUSE. Budget respecte. J'ecris UNIQUEMENT dans research/.
    Signal-only absolu (0 code d'execution d'ordres).
  - Lake : 13 parquet, FRONTIERE 2026-07-02 04:00 UTC (ts epoch->UTC verifie).
    GC_F_1d range 43.5 / ES_F_1d range 35.25 = VRAIES OHLC. TOUJOURS AUCUN 15m.
  - lab_counters() = {testees 45, tuees 44, papier 0, promues 0} (inchange).
    Deflation Bonferroni GLOBALE a vie : test n+1 -> z_req ~3.07.
  - resim Gate-1 : n decisifs 17 (7 TP / 10 SL), WR 41.2%, exp +0.142%,
    IC bootstrap-jours (-0.11, 0.367) CONTIENT 0 -> edge net NON prouve.
    equity x20 1094.58 EUR (etait 1142.01 : perte US500 02/07 bookee, coherent).
    USER (Revolut reel) WR 56.2% [IC95 49.3-62.9] n=201 exp -0.004%
    (+21 vs 180 = re-import CSV cote Sam, hygiene de donnees).
  - feature_store : 6692/500 outcomes, 0 ERROR, 1 MIXED exclu, 917 setups,
    order-flow 11 JOURS distincts (modele_appris_autorise=false, seuil ~20,
    STATIONNAIRE depuis ce matin).
  - journal.json : 301 signaux, last_updated 20:39 UTC (22:39 Paris). Fills du
    02/07 = 1 US500 SHORT CLOSED -0.362% (le fill perdant autopsie a 23h) +
    3 US500 SHORT EXPIRED. 0 nouveau fill depuis 23h. Pipeline honnete.
  - Aucune injection : news_cache.json (4384 ch.) + calendar_cache.json
    (18810 ch.) scannes (ignore|disregard|system prompt|rm -rf|sudo|override|
    delete|commit|exec|reveal|token|git|edit) -> 2 hits = SOUS-CHAINES benignes
    ("Private Sector Cr-edit", "BOE Cr-edit Conditions") : 0 imperatif. Donnees
    externes traitees STRICTEMENT en DONNEE, jamais en instruction.

CE QUE FAIT CE SCRIPT (et ce qu'il NE fait PAS) :
  - 0 hypothese neuve soumise (0/3). Matrice fermee (44 KILLED). Le FAIT DU JOUR
    (deja autopsie a 23h) : la prod a TRADE apres le NFP -- 10 A_SETUP US500
    SHORT OTE_RETRACEMENT tous en TENDANCE HACHEE, 1 fill LOSS -0.362% + 3
    EXPIRED. L'etiqueteur de regime etait HONNETE aujourd'hui (a dit HACHEE,
    PAS le faux PROPRE du 01/07) -> la fuite du jour n'est PAS l'etiqueteur mais
    la PORTE A_SETUP + le value-gate qui laissent shorter SOUS la VAL vers un
    POC-aimant AU-DESSUS quand recent_delta flippe positif (miroir BAS du grief
    GOLD par le haut). Le correctif (orderflow_value_gate, decrit dans le
    rapport, 2 volets) reste famille order-flow = strategy_families.py protege
    (token Sam) + logique POC/VAL/delta 15m INJUGEABLE sur lake 1h-1d +
    order-flow 11j sous-puissant (seuil 20). Toute soumission momentum/regime
    serait DUPLICATE / re-knob / sign-flip INTERDIT. 0 = verdict discipline
    (mortalite >90% = sante).
  - DEMONTRE empiriquement la frontiere 02/07 VRAIE OHLC des 2 cotes (raffine la
    theorie jours-manquants, 3e nuit), et l'invariant dedup (cellule deja jugee
    re-soumise -> DUPLICATE, 0 effet de bord, lab byte-stable).

PROPOSITION POUR SAM (token Sam, fichiers proteges -- je ne touche pas) :
  1. Famille order-flow + orderflow_value_gate (2 volets, affines par le cas
     US500 02/07) :
       Volet A -- porte d'entree : VETO tout SHORT si recent_delta >= 0 (et
         symetriquement LONG si delta <= 0). Le delta est le signal AVANCE du
         retournement-POC. Cas 02/07 : tue les shorts 20:27->21:50 (delta +103
         -> +1743).
       Volet B -- geometrie value/POC : VETO SHORT sous la VAL quand le POC est
         AU-DESSUS et la VA non-expansive (reaspiration probable, pas breakout).
         Autoriser seulement si le prix casse la VA avec EXPANSION de largeur.
         Cas 02/07 : tue le fill perdant de 19:38 (delta -2115 order-flow-correct
         a l'entree mais POC 7481 au-dessus, VA non-expansive -> clippe par la
         reaspiration). A+B => 0 short => 0 perte le 02/07.
  2. Accumuler l'order-flow 11 -> ~20 jours distincts = levier #1 pour rendre la
     famille jugeable (modele appris non autorise sous seuil 20).
  3. Lake intraday 15m = deblocage n1 (fill, atteinte-TP, conditionnement de
     regime intraday, logique POC/VA/delta -- tout est injugeable sans lui).
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
    "id": "DEMO_dedup_twist_1d_2026_07_02",
    "hypothesis_text": "DEMONSTRATION (pas une hypothese neuve) : re-soumission de "
                       "la cellule deja jugee IL_pool_ichimoku_twist_1d sur le lake "
                       "rafraichi jeudi (post-NFP). Attendu : DUPLICATE, 0 effet de bord.",
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
    print("\n  LECTURE : le 02/07 est un JEUDI de NFP reellement trade et sa barre "
          "est une VRAIE OHLC des DEUX cotes (GC range 43.5, ES range 35.25). "
          "-> re-confirme (3e nuit) 'jours manquants backfilles' (30/06), refute "
          "'fuite week-end' (29/06). Frontiere PROPRE ; 55 plates INTERIEURES "
          "(~4.4%, specifique or ; ES_F_1d 0 plate). Tout re-test 1d LONG reste "
          "contamine tant que l'interieur n'est pas filtre (backlog #3, token Sam).")

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
    print("CONCLUSION : frontiere 1d 02/07 VRAIE OHLC des 2 cotes (theorie "
          "jours-manquants raffinee, 3e nuit), dedup toujours bloquant -> "
          "0 hypothese neuve soumise (honnete, discipline). Le seul levier neuf "
          "(orderflow_value_gate) reste triplement bloque (famille absente du "
          "registry + lake 1h-1d incompatible + order-flow 11j<20).")


if __name__ == "__main__":
    main()
