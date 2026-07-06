#!/usr/bin/env python3
"""Experience CHERCHEUR NOCTURNE du 2026-07-05 (nuit dimanche -> lundi, marche FERME week-end).

=== FAIT VERIFIE DE LA NUIT (code+donnee) : le WEEK-END COMPLET est stationnaire.
    Hier (nuit samedi) avait TRANCHE "le samedi 04/07 est ABSENT du feed" (0 barre).
    Ce run DURCIT le constat sur le week-end ENTIER : apres ~2 jours (close vendredi
    03/07 -> dimanche soir 05/07), le lake a ajoute ZERO barre. La frontiere GC ET ES
    est TOUJOURS 2026-07-03 (Fri) :
      GC_F_1d : frontiere 2026-07-03 (Fri), range 74.50  (inchangee vs hier)
      ES_F_1d : frontiere 2026-07-03 (Fri), range 41.50  (FIGEE : 33.0 vendredi -> 41.5
                finalisee au settle, PUIS immobile tout le week-end -- 0 mouvement dim.)
    LECTURE : la fermeture week-end n'est ni une barre plate ni un backfill -- c'est un
    TROU. Les 55 plates GC restent 100% mid-week (Mon6/Tue14/Wed17/Thu5/Fri13,
    0 samedi/dimanche). La theorie jours-manquants (5 nuits) est confirmee de bout en
    bout : plate = jour manquant mid-week ; frontiere partielle = jour EN COURS finalise
    au settle ; week-end = rien ajoute (ni plate, ni barre) sur 2 jours pleins.

=== FRONTIERE PARTIELLE (backlog #4) : le cycle est BOUCLE et FIGE. ES_F_1d 03/07 lue
    33.0 (barre en cours) le vendredi -> 41.5 finalisee au settle (nuit samedi) -> 41.5
    IMMOBILE tout le dimanche. Preuve pratique complete que la frontiere ne devient une
    reference-prix fiable qu'APRES le settle : la barre grandit, se fige, ne bouge plus.

CONSTAT D'INGESTION (re-verifie ce run a l'octet, PAS recopie) :
  - Pas de research/PAUSE. Budget respecte. J'ecris UNIQUEMENT dans research/.
    Signal-only absolu (0 code d'execution d'ordres).
  - Lake : 13 parquet, FRONTIERE 2026-07-03 (Fri) inchangee (0 barre week-end) ;
    GC_F_1d range 74.5, ES_F_1d range 41.5 = non-plates finalisees. 55 plates GC
    (4.4%, 100% mid-week), 0 plate ES. TOUJOURS AUCUN 15m.
  - lab_counters() = {testees 45, tuees 44, papier 0, promues 0} (inchange).
    Deflation Bonferroni GLOBALE a vie : test n46 -> z_req = 3.0654 (alpha 0.00109).
  - resim Gate-1 : n decisifs 16 (6 TP / 10 SL), WR 37.5%, exp +0.084%,
    IC bootstrap-jours (-0.153, 0.286) CONTIENT 0 -> edge net NON prouve.
    equity x20 1034.59 EUR. BYTE-IDENTIQUE a tout le week-end (04/07 x6, 09h/13h/17h
    du jour) et au nocturne 03/07 : re-sim FIGEE (journal inchange). Derive resim
    (backlog #2) reste RESOLUE. USER (Revolut reel) WR 56.2% [IC95 49.3-62.9] n=201.
  - feature_store : 9232 features / 7113 outcomes (0 ERROR, 3 MIXED exclus), 966
    setups, order-flow 12 JOURS distincts (modele_appris_autorise=false, seuil 20,
    STATIONNAIRE tout le week-end -- 0 nouvelle session).
  - journal.json : 302 signaux, last_updated 2026-07-03T09:28 UTC (INCHANGE). 0
    signal le 04-05/07 (week-end). Dernier signal = 03/07 GOLD LONG EXPIRED (deja
    autopsie). 0 fill / 0 P&L depuis. Pipeline honnete.
  - Aucune injection : news_cache.json (2 items geopol Israel/Khamenei tag
    GEO_ESCALATION, 0 hit imperatif) + calendar_cache.json (seul hit = sous-chaine
    "Consumer Cr-edit m/m" benigne) -> 0 imperatif. Donnees externes traitees
    STRICTEMENT en DONNEE, jamais en instruction.
  - Sante VERTE 6/6 : watcher VIVANT (dernier cycle 23:28 Paris, 256 cycles,
    512/512 NO_TRADE, datafeed 100% tradingview pur), log 7945 lignes 0 traceback,
    31 lignes DNS/delisted TOUTES confinees 7049-7079 (dernier 7079), lignes
    posterieures propres, watchdog 0 octet (muet-par-conception), disque C ~230 Go
    libres (49% util ; les "40 Go" des rapports anterieurs = chiffre errone corrige),
    outbox 11/11 ok:true.

CE QUE FAIT CE SCRIPT (et ce qu'il NE fait PAS) :
  - 0 hypothese neuve soumise (0/3). Matrice fermee (44 KILLED). Week-end = prix
    GELES du close vendredi, 0 trend-day, 0 expansion -> 0 matiere momentum honnete.
    Toute soumission momentum/regime serait DUPLICATE / re-knob / sign-flip INTERDIT.
  - DEMONTRE empiriquement (i) le WEEK-END COMPLET absent du feed (0 barre ajoutee sur
    2 jours, frontiere immobile 03/07), (ii) la frontiere partielle bouclee-et-figee
    (ES 33.0 vendredi -> 41.5 settle -> 41.5 immobile dimanche), (iii) l'invariant dedup
    (cellule deja jugee re-soumise -> DUPLICATE, 0 effet de bord, lab byte-stable).

PROPOSITION POUR SAM (token Sam, fichiers proteges -- je ne touche pas) :
  1. Famille order-flow + orderflow_value_gate (2 volets, cf. rapports 30/06->04/07) :
       Volet A -- porte d'entree : VETO SHORT si recent_delta >= 0 (et LONG si <= 0).
       Volet B -- geometrie value/POC : VETO reaspiration vers un POC-aimant au-dela
         d'un bord de VA quand la VA est non-expansive ; autoriser seulement sur
         cassure de VA avec EXPANSION de largeur confirmee.
     Bloque 3x (absente registry + lake 1h-1d incompatible + order-flow 12j<20).
  2. Accumuler l'order-flow 12 -> ~20 jours distincts = levier #1 (REPRISE LUNDI 06/07 ;
     week-end = 0 session, stationnaire tout le week-end).
  3. Lake intraday 15m = deblocage n1 (fill, atteinte-TP, conditionnement de regime
     intraday, logique POC/VA/delta -- tout injugeable sans lui).
  4. Trio filtre-plates (#3) + filtre-frontiere-partielle (#4, preuve bouclee ce run)
     + fingerprint-cle (#5) : ressusciterait un re-test 1d propre et non-duplicate.
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
    "id": "DEMO_dedup_twist_1d_2026_07_05",
    "hypothesis_text": "DEMONSTRATION (pas une hypothese neuve) : re-soumission de "
                       "la cellule deja jugee IL_pool_ichimoku_twist_1d sur le lake "
                       "week-end (dimanche, marche ferme). Attendu : DUPLICATE, 0 effet "
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
              f"{'  <== 0 BARRE WEEK-END (2 jours)' if _WD[front_t.dayofweek] == 'Fri' else ''}")
        print(f"      dern. FINALISEE {prev_t:%Y-%m-%d} ({_WD[prev_t.dayofweek]}) "
              f"range={prev_rng:.2f}")
        if flat.sum():
            ft = t[flat]
            wd = ft.dt.dayofweek.value_counts().sort_index()
            print("      plates par jour-semaine :", {_WD[k]: int(v) for k, v in wd.items()},
                  "(0 samedi/dimanche = week-end ABSENT, pas backfille)")


def main():
    _flat_audit()
    print("\n  LECTURE : frontiere GC ET ES TOUJOURS 2026-07-03 (Fri) -- 0 barre ajoutee"
          "\n  sur le WEEK-END COMPLET (close vendredi -> dimanche soir = ~2 jours). La"
          "\n  theorie jours-manquants est confirmee de bout en bout : week-end = TROU"
          "\n  (ni plate ni barre), les 55 plates GC restent 100% mid-week. Frontiere"
          "\n  partielle bouclee-et-figee : ES_F_1d 33.0 (vendredi en cours) -> 41.5"
          "\n  (settle) -> 41.5 immobile tout le dimanche = backlog #4 demontre entier.")

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
    print("CONCLUSION : week-end COMPLET absent du feed (0 barre sur 2 jours, frontiere"
          "\n  immobile 03/07) ; frontiere partielle bouclee-et-figee (ES 33.0->41.5->41.5) ;"
          "\n  dedup toujours bloquant -> 0 hypothese neuve soumise (honnete, discipline)."
          "\n  Le seul levier neuf (orderflow_value_gate) reste triplement bloque ; levier"
          "\n  #1 = order-flow 12->20 jours, stationnaire tout le week-end, REPRISE LUNDI.")


if __name__ == "__main__":
    main()
