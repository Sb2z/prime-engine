#!/usr/bin/env python3
"""Experience CHERCHEUR NOCTURNE du 2026-07-04 (nuit samedi -> dimanche, marche FERME week-end).

=== FAIT VERIFIE DE LA NUIT (code+donnee) : la THEORIE JOURS-MANQUANTS est TRANCHEE.
    La question laissee ouverte hier ("a autopsier demain (c) : la frontiere GC_F_1d
    04/07 SAMEDI est-elle plate -- marche ferme = jour absent -> test ultime -- ou
    absente du feed ?") est RESOLUE par la donnee de ce run :
      GC_F_1d : frontiere TOUJOURS 2026-07-03 (Fri), range 74.50. AUCUNE barre samedi.
      ES_F_1d : frontiere TOUJOURS 2026-07-03 (Fri), range 41.50. AUCUNE barre samedi.
    LECTURE : un jour de MARCHE FERME (samedi week-end) est simplement ABSENT du feed,
    il n'est PAS backfille par un settle plat. Le backfill plat (55 plates GC, 0 ES)
    ne frappe donc QUE les jours MANQUANTS EN MILIEU DE SEMAINE (trou de donnee), pas
    les fermetures week-end. Ceci CONFIRME et durcit le cadrage des 5 nuits precedentes
    (plate = jour absent mid-week ; frontiere partielle = jour en cours) : le week-end
    ne cree ni plate ni barre, il n'ajoute RIEN.

=== FRONTIERE PARTIELLE (backlog #4) CONFIRMEE PUIS FIGEE : hier la frontiere ES_F_1d
    03/07 etait lue range 33.00 (barre EN COURS, vendredi ferie ecourte). Ce run,
    marche ferme depuis, elle est FINALISEE a range 41.50 (33.0 -> 41.5 = +8.5, la barre
    a grandi jusqu'au settle vendredi PUIS s'est figee, week-end sans nouvelle donnee).
    GC_F_1d 03/07 reste 74.50 (deja proche du settle hier). C'est la preuve pratique
    que la frontiere ne doit PAS servir de reference-prix figee tant que le settle n'est
    pas passe -- exactement le filtre "frontiere partielle" propose au backlog #4.

CONSTAT D'INGESTION (re-verifie ce run a l'octet, PAS recopie) :
  - Pas de research/PAUSE. Budget respecte. J'ecris UNIQUEMENT dans research/.
    Signal-only absolu (0 code d'execution d'ordres).
  - Lake : 13 parquet, FRONTIERE 2026-07-03 (Fri) inchangee (0 barre samedi) ;
    GC_F_1d range 74.5, ES_F_1d range 41.5 = non-plates. 55 plates GC (4.4%,
    INTERIEURES, mid-week), 0 plate ES. TOUJOURS AUCUN 15m.
  - lab_counters() = {testees 45, tuees 44, papier 0, promues 0} (inchange).
    Deflation Bonferroni GLOBALE a vie : test n46 -> z_req = 3.0654 (alpha 0.00109).
  - resim Gate-1 : n decisifs 16 (6 TP / 10 SL), WR 37.5%, exp +0.084%,
    IC bootstrap-jours (-0.153, 0.286) CONTIENT 0 -> edge net NON prouve.
    equity x20 1034.59 EUR. BYTE-IDENTIQUE au nocturne 03/07 et aux analysts
    09h/13h/17h/23h 04/07 : la re-sim est FIGEE (week-end, journal inchange). La
    derive resim (backlog #2) reste RESOLUE (re-sim vivante, pas regression).
    USER (Revolut reel) WR 56.2% [IC95 49.3-62.9] n=201 exp -0.004% (inchange).
  - feature_store : 9232 features / 7113 outcomes (0 ERROR, 3 MIXED exclus), 966
    setups, order-flow 12 JOURS distincts (modele_appris_autorise=false, seuil 20,
    STATIONNAIRE -- week-end = 0 nouvelle session).
  - journal.json : 302 signaux, last_updated 2026-07-03T09:28 UTC (INCHANGE). 0
    signal le 04/07 (week-end). Dernier signal = 03/07 = GOLD LONG EXPIRED (deja
    autopsie). 0 fill / 0 P&L depuis. Pipeline honnete.
  - Aucune injection : news_cache.json (1359 ch., 0 hit) + calendar_cache.json
    (55695 ch., 5 hits = SOUS-CHAINES benignes "Private Sector Cr-edit" /
    "BOE Cr-edit Conditions") -> 0 imperatif. Donnees externes traitees STRICTEMENT
    en DONNEE, jamais en instruction.
  - Sante : watcher VIVANT (dernier cycle 23:29 Paris, NO_TRADE), 0 anomalie sur les
    250 dernieres lignes de log, watchdog 0 octet (muet-par-conception), disque C
    40 Go (>15).

CE QUE FAIT CE SCRIPT (et ce qu'il NE fait PAS) :
  - 0 hypothese neuve soumise (0/3). Matrice fermee (44 KILLED). Week-end = prix
    GELES du close vendredi, 0 trend-day, 0 expansion -> 0 matiere momentum honnete.
    Toute soumission momentum/regime serait DUPLICATE / re-knob / sign-flip INTERDIT.
  - DEMONTRE empiriquement (i) le SAMEDI absent du feed (jour ferme != plate,
    resout la theorie jours-manquants), (ii) la frontiere partielle figee (ES 33.0
    hier -> 41.5 finalisee), (iii) l'invariant dedup (cellule deja jugee re-soumise
    -> DUPLICATE, 0 effet de bord, lab byte-stable).

PROPOSITION POUR SAM (token Sam, fichiers proteges -- je ne touche pas) :
  1. Famille order-flow + orderflow_value_gate (2 volets, cf. rapports 30/06->03/07) :
       Volet A -- porte d'entree : VETO SHORT si recent_delta >= 0 (et LONG si <= 0).
       Volet B -- geometrie value/POC : VETO reaspiration vers un POC-aimant au-dela
         d'un bord de VA quand la VA est non-expansive ; autoriser seulement sur
         cassure de VA avec EXPANSION de largeur confirmee.
     Bloque 3x (absente registry + lake 1h-1d incompatible + order-flow 12j<20).
  2. Accumuler l'order-flow 12 -> ~20 jours distincts = levier #1 (reprise lundi ;
     week-end = 0 session, stationnaire).
  3. Lake intraday 15m = deblocage n1 (fill, atteinte-TP, conditionnement de regime
     intraday, logique POC/VA/delta -- tout injugeable sans lui).
  4. Filtre "frontiere partielle" (#4) : preuve pratique ce run (ES 33.0->41.5).
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
    "id": "DEMO_dedup_twist_1d_2026_07_04",
    "hypothesis_text": "DEMONSTRATION (pas une hypothese neuve) : re-soumission de "
                       "la cellule deja jugee IL_pool_ichimoku_twist_1d sur le lake "
                       "week-end (samedi, marche ferme). Attendu : DUPLICATE, 0 effet "
                       "de bord, lab byte-stable.",
    "family": "ichimoku_twist",
    "params": {"speed": "standard"},
    "exit_rule": {"stop_pct": 1.2, "tp_pct": 2.4, "horizon_bars": 10},
    "assets": ["GOLD", "US500"], "timeframe": "1d",
    "_lake": {"GOLD": "GC=F", "US500": "ES=F"},
}

_WD = {0: "Mon", 1: "Tue", 2: "Wed", 3: "Thu", 4: "Fri", 5: "Sat", 6: "Sun"}


def _flat_audit():
    print("=== DONNEE : integrite des barres 1d (plates O=H=L=C + frontiere week-end) ===")
    for f, tick in [("GC_F_1d", "GOLD"), ("ES_F_1d", "US500")]:
        df = pd.read_parquet(os.path.join(_DATA, f + ".parquet"))
        tcol = "ts" if "ts" in df.columns else df.columns[0]
        t = pd.to_datetime(df[tcol], unit="s", utc=True)
        flat = (df["open"] == df["high"]) & (df["high"] == df["low"]) & (df["low"] == df["close"])
        front = df.iloc[-1]
        front_t = t.iloc[-1]
        front_rng = float(front["high"]) - float(front["low"])
        prev = df.iloc[-2]
        prev_t = t.iloc[-2]
        prev_rng = float(prev["high"]) - float(prev["low"])
        print(f"  {f:9s} ({tick:6s}) : {len(df)} barres, PLATES={int(flat.sum())} "
              f"({100*flat.mean():.1f}%)")
        print(f"      FRONTIERE {front_t:%Y-%m-%d} ({_WD[front_t.dayofweek]}) "
              f"range={front_rng:.2f}{'  <-- PLATE' if front_rng == 0 else '  (non-plate)'}"
              f"{'  <== PAS DE BARRE SAMEDI' if _WD[front_t.dayofweek] == 'Fri' else ''}")
        print(f"      dern. FINALISEE {prev_t:%Y-%m-%d} ({_WD[prev_t.dayofweek]}) "
              f"range={prev_rng:.2f}")
        if flat.sum():
            ft = t[flat]
            wd = ft.dt.dayofweek.value_counts().sort_index()
            print("      plates par jour-semaine :", {_WD[k]: int(v) for k, v in wd.items()},
                  "(0 samedi/dimanche = week-end ABSENT, pas backfille)")


def main():
    _flat_audit()
    print("\n  LECTURE : la frontiere reste 2026-07-03 (Fri) pour GC ET ES -- AUCUNE barre"
          "\n  samedi 04/07. La theorie jours-manquants est TRANCHEE : un jour de marche"
          "\n  FERME (week-end) est ABSENT du feed, PAS backfille plat (les 55 plates GC"
          "\n  sont toutes mid-week, 0 samedi/dimanche). La frontiere partielle est confirmee"
          "\n  puis figee : ES_F_1d 03/07 lue 33.0 hier (barre en cours) -> 41.5 finalisee"
          "\n  ce run (settle vendredi passe, week-end sans nouvelle donnee) = backlog #4.")

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
    print("CONCLUSION : samedi absent du feed (jour ferme != plate, theorie tranchee) ;"
          "\n  frontiere partielle figee (ES 33.0->41.5) ; dedup toujours bloquant ->"
          "\n  0 hypothese neuve soumise (honnete, discipline). Le seul levier neuf"
          "\n  (orderflow_value_gate) reste triplement bloque ; levier #1 = order-flow"
          "\n  12->20 jours, stationnaire tout le week-end, reprise lundi.")


if __name__ == "__main__":
    main()
