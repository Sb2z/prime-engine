#!/usr/bin/env python3
"""Experience CHERCHEUR NOCTURNE du 2026-07-03 (nuit vendredi -> samedi, jour ferie US).

=== FAIT VERIFIE DE LA NUIT (code+donnee) : la barre-FRONTIERE 1d est PARTIELLE
    (vivante) et grandit jusqu'au settle. Preuve directe par la meme cellule a 24h
    d'ecart --
      GC_F_1d 02/07 : range 43.50 en FRONTIERE (rapport d'hier) -> 78.10 une fois
                      FINALISEE (barre interieure aujourd'hui).
      GC_F_1d 03/07 : range 74.50 en FRONTIERE (vendredi ferie, partielle a ce run).
      ES_F_1d 03/07 : range 33.00 en FRONTIERE (VRAIE OHLC).
    LECTURE : "frontiere vraie OHLC" (dit 3 nuits de suite) etait vrai mais
    INCOMPLET -- la frontiere n'est pas une plate settle (bon), mais c'est une
    barre EN COURS, pas une OHLC arretee. Elle ne doit PAS servir de reference-prix
    figee ; tout re-test 1d doit s'arreter a la derniere barre FINALISEE (frontiere
    exclue), en plus du filtre plates (backlog #3). Ceci RAFFINE, sans le contredire,
    le cadrage "jours manquants backfilles par un settle plat" (30/06) : une plate
    = jour ABSENT du feed ; la frontiere partielle = jour EN COURS. Le 26/06 (Fri)
    reste la derniere plate, desormais a 5 barres de la frontiere (INTERIEURE).

=== QUESTION (c) DU BACKLOG 02/07 -> RESOLUE : "la frontiere GC_F_1d 03/07 (vendredi,
    2e jour le plus charge en plates 13/55) reste-t-elle vraie OHLC ?" OUI --
    range 74.50 (non-plate), coherent avec la volatilite journaliere GC recente
    (66.8 / 87.2 / 137.0 / 78.1 les 4 jours precedents). 4e nuit consecutive qui
    confirme "seul un jour ABSENT est backfille plat". CAVEAT : le vendredi 03/07 est
    un jour ferie US observe (July 4) -> COMEX ecourte cote CFD prod, mais le futur
    GC=F du lake a bien une vraie barre journaliere. Pas d'anomalie de range (ma
    comparaison au range CFD ~18pts serait fausse : instruments/sessions differents).

CONSTAT D'INGESTION (re-verifie ce run a l'octet, PAS recopie) :
  - Pas de research/PAUSE. Budget respecte. J'ecris UNIQUEMENT dans research/.
    Signal-only absolu (0 code d'execution d'ordres).
  - Lake : 13 parquet, FRONTIERE 2026-07-03 (Fri) ; GC_F_1d range 74.5, ES_F_1d
    range 33.0 = non-plates. 55 plates GC (4.4%, INTERIEURES), 0 plate ES.
    TOUJOURS AUCUN 15m.
  - lab_counters() = {testees 45, tuees 44, papier 0, promues 0} (inchange).
    Deflation Bonferroni GLOBALE a vie : test n46 -> z_req = 3.0654 (alpha 0.00109).
  - resim Gate-1 : n decisifs 16 (6 TP / 10 SL), WR 37.5%, exp +0.084%,
    IC bootstrap-jours (-0.153, 0.286) CONTIENT 0 -> edge net NON prouve.
    equity x20 1034.59 EUR. STABLE vs analyst 23h (identique) -> la derive
    17->16 dec signalee a 23h s'est ARRETEE : c'etait une re-simulation vivante
    (1 position TP -> sortie-horizon quand les chandelles intraday se sont mises a
    jour), PAS une regression progressive du pipeline. Backlog #2 RECONFIRME.
    USER (Revolut reel) WR 56.2% [IC95 49.3-62.9] n=201 exp -0.004% (inchange).
  - feature_store : 7113/500 outcomes, 0 ERROR, 3 MIXED exclus, 966 setups,
    order-flow 12 JOURS distincts (modele_appris_autorise=false, seuil 20,
    STATIONNAIRE vs 23h).
  - journal.json : 302 signaux, last_updated 09:28 UTC (11:28 Paris). 1 seul
    signal today = GOLD LONG EXPIRED (10:39 Paris, OTE_RETRACEMENT, conf 8.0) =
    0 fill / 0 P&L (deja autopsie 13h+23h). 0 nouveau fill depuis. Pipeline honnete.
  - Aucune injection : news_cache.json (5031 ch., 0 hit) + calendar_cache.json
    (52131 ch., 5 hits = SOUS-CHAINES benignes "Private Sector Cr-edit" /
    "BOE Cr-edit Conditions") -> 0 imperatif. Donnees externes traitees STRICTEMENT
    en DONNEE, jamais en instruction.

CE QUE FAIT CE SCRIPT (et ce qu'il NE fait PAS) :
  - 0 hypothese neuve soumise (0/3). Matrice fermee (44 KILLED). Jour ferie =
    range/consolidation sans trend-day -> 0 matiere momentum. La seule decision-prod
    (GOLD LONG EXPIRED) est deja autopsiee et NON decisive (0 fill). Toute soumission
    momentum/regime serait DUPLICATE / re-knob / sign-flip INTERDIT.
  - DEMONTRE empiriquement (i) la frontiere partielle qui grandit (02/07 43.5->78.1),
    (ii) la question (c) resolue (03/07 vendredi non-plate), (iii) l'invariant dedup
    (cellule deja jugee re-soumise -> DUPLICATE, 0 effet de bord, lab byte-stable).

PROPOSITION POUR SAM (token Sam, fichiers proteges -- je ne touche pas) :
  1. Famille order-flow + orderflow_value_gate (2 volets, cf. rapports 30/06->03/07) :
       Volet A -- porte d'entree : VETO SHORT si recent_delta >= 0 (et LONG si <= 0).
       Volet B -- geometrie value/POC : VETO reaspiration vers un POC-aimant au-dela
         d'un bord de VA quand la VA est non-expansive ; autoriser seulement sur
         cassure de VA avec EXPANSION de largeur confirmee.
     Contre-exemple POSITIF du 03/07 midi : le gate aurait LAISSE PASSER le GOLD LONG
     (delta +56k confirme + cassure VAH expansive) = il discrimine (pass les bons,
     veto les faux trends delta-contredisant 30/06->02/07).
  2. Accumuler l'order-flow 12 -> ~20 jours distincts = levier #1 (modele appris non
     autorise sous seuil 20).
  3. Lake intraday 15m = deblocage n1 (fill, atteinte-TP, conditionnement de regime
     intraday, logique POC/VA/delta -- tout injugeable sans lui).
  4. Filtre "frontiere partielle" : en plus du filtre plates (#3), tout re-test 1d
     doit exclure la derniere barre (EN COURS) pour ne pas lire un range tronque.
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
    "id": "DEMO_dedup_twist_1d_2026_07_03",
    "hypothesis_text": "DEMONSTRATION (pas une hypothese neuve) : re-soumission de "
                       "la cellule deja jugee IL_pool_ichimoku_twist_1d sur le lake "
                       "rafraichi vendredi (jour ferie US). Attendu : DUPLICATE, 0 "
                       "effet de bord.",
    "family": "ichimoku_twist",
    "params": {"speed": "standard"},
    "exit_rule": {"stop_pct": 1.2, "tp_pct": 2.4, "horizon_bars": 10},
    "assets": ["GOLD", "US500"], "timeframe": "1d",
    "_lake": {"GOLD": "GC=F", "US500": "ES=F"},
}

_WD = {0: "Mon", 1: "Tue", 2: "Wed", 3: "Thu", 4: "Fri", 5: "Sat", 6: "Sun"}


def _flat_audit():
    print("=== DONNEE : integrite des barres 1d (plates O=H=L=C + frontiere) ===")
    for f, tick in [("GC_F_1d", "GOLD"), ("ES_F_1d", "US500")]:
        df = pd.read_parquet(os.path.join(_DATA, f + ".parquet"))
        tcol = "ts" if "ts" in df.columns else df.columns[0]
        t = pd.to_datetime(df[tcol], unit="s", utc=True)
        flat = (df["open"] == df["high"]) & (df["high"] == df["low"]) & (df["low"] == df["close"])
        front = df.iloc[-1]
        front_t = t.iloc[-1]
        front_rng = float(front["high"]) - float(front["low"])
        # barre precedente = derniere FINALISEE (interieure)
        prev = df.iloc[-2]
        prev_t = t.iloc[-2]
        prev_rng = float(prev["high"]) - float(prev["low"])
        print(f"  {f:9s} ({tick:6s}) : {len(df)} barres, PLATES={int(flat.sum())} "
              f"({100*flat.mean():.1f}%)")
        print(f"      FRONTIERE (EN COURS) {front_t:%Y-%m-%d} ({_WD[front_t.dayofweek]}) "
              f"range={front_rng:.2f}{'  <-- PLATE' if front_rng == 0 else '  (non-plate)'}")
        print(f"      dern. FINALISEE      {prev_t:%Y-%m-%d} ({_WD[prev_t.dayofweek]}) "
              f"range={prev_rng:.2f}")
        if flat.sum():
            ft = t[flat]
            wd = ft.dt.dayofweek.value_counts().sort_index()
            print("      plates par jour-semaine :", {_WD[k]: int(v) for k, v in wd.items()})
            idx_flat = df.index[flat]
            gap = (len(df) - 1) - list(idx_flat)[-1]
            last_flat_t = ft.iloc[-1]
            print(f"      derniere plate       : {last_flat_t:%Y-%m-%d} "
                  f"(a {gap} barre(s) de la frontiere -> "
                  f"{'INTERIEURE' if gap > 0 else 'EN FRONTIERE'})")


def main():
    _flat_audit()
    print("\n  LECTURE : la barre-frontiere est PARTIELLE (en cours) -- le 02/07 lu a"
          "\n  range 43.5 en frontiere hier est aujourd'hui FINALISE a 78.1. La question"
          "\n  (c) du backlog est RESOLUE : la frontiere 03/07 (vendredi ferie) est"
          "\n  non-plate (GC 74.5 / ES 33.0) = 4e nuit qui confirme 'seul un jour ABSENT"
          "\n  est backfille plat'. Consequence pratique : tout re-test 1d doit exclure"
          "\n  la barre EN COURS (frontiere) EN PLUS du filtre plates (backlog #3/#4).")

    print("\n=== HARNESS : dedup gele le re-test (invariant) ===")
    before = harness.lab_counters()
    reg_len_before = len(harness.registry())
    z_req = harness.required_z(reg_len_before + 1)
    print("lab_counters AVANT :", json.dumps(before, ensure_ascii=False),
          "| registry len =", reg_len_before, "| z_req test n+1 =", round(z_req[0], 4))

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
    print("CONCLUSION : frontiere 1d = barre PARTIELLE (grandit jusqu'au settle) ;"
          "\n  question (c) resolue (03/07 non-plate) ; dedup toujours bloquant ->"
          "\n  0 hypothese neuve soumise (honnete, discipline). Le seul levier neuf"
          "\n  (orderflow_value_gate) reste triplement bloque (famille absente du"
          "\n  registry + lake 1h-1d incompatible + order-flow 12j<20).")


if __name__ == "__main__":
    main()
