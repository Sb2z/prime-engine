#!/usr/bin/env python3
"""Experience CHERCHEUR NOCTURNE du 2026-06-30 (nuit mardi -> mercredi).

=== FAIT NEUF DE LA NUIT (suite du 29/06, code+donnee-verifie) :
    (1) La FRONTIERE GOLD 1d s'est AUTO-REPAREE. La barre 26/06 plate (O=H=L=C=
        4078.70) est toujours plate MAIS elle est desormais INTERIEURE : le lake
        a gagne deux VRAIES barres OHLC (29/06 range 66.8, 30/06 range 81.3), la
        frontiere courante (30/06) n'est PAS plate. -> reponse a la question
        ouverte (a) du 29/06 : la barre forming s'est completee en VRAIE OHLC.
    (2) La DISTRIBUTION des 55 barres plates REFUTE ma theorie du 29/06. J'avais
        ecrit que la valeur plate venait du "settle figee du feed week-end qui a
        fui dans le lake". FAUX : les 55 plates sont concentrees MI-SEMAINE
        (Mardi 14 / Mercredi 17, pas le week-end) et reparties sur TOUTES les
        annees (2021->2026). C'est un quirk yfinance GC=F de JOURS MANQUANTS
        backfilles par un settle unique, PAS une fuite week-end. Le defaut reste
        SYSTEMATIQUE (~4.4%) et SPECIFIQUE a l'or (ES_F_1d = 0 plate).

CONSTAT D'INGESTION (re-verifie ce run, pas recopie) :
  - Pas de research/PAUSE. Budget respecte. J'ecris UNIQUEMENT dans research/.
  - Lake : 13 parquet, REFRESH mardi, FRONTIERE 2026-06-30 04:00 UTC (verifiee,
    ts epoch -> UTC). GC_F_1d/ES_F_1d frontiere = 2026-06-30 (VRAIE OHLC, non
    plate). TOUJOURS AUCUN 15m.
  - lab_counters() = {testees 45, tuees 44, papier 0, promues 0} (inchange).
    Deflation Bonferroni GLOBALE (harness.py) : test n+1 -> z_req ~3.07.
  - resim Gate-1 : equity x20 1241.11 EUR INCHANGEE depuis 09h (0 nouveau fill),
    n decisifs 14<15, exp +0.215% IC bootstrap (-0.043, 0.448) CONTIENT 0 ->
    edge non prouve. USER WR 56.7% n=180 exp +0.002% inchange.
  - feature_store : 5700/500, 0 ERROR, 1 MIXED exclu, 769 setups, 9j order-flow
    (modele_appris_autorise=false, attendu <~20j).
  - journal.json : 269 signaux (USER 180 / AI 71 / None 18), SEULS fills 30/06 =
    3 GOLD SHORT (3 LOSS -0.407/-0.406/-0.406%) + 2 EXPIRED NOFILL (= les pertes
    du matin, last_updated 06:35). 0 nouveau fill depuis. Pipeline honnete.
  - Aucune injection : news_cache.json + calendar_cache.json scannes
    (ignore|disregard|system prompt|rm -rf|sudo|override|delete|commit|exec|token)
    = 0 token imperatif. Donnees externes traitees STRICTEMENT en DONNEE.

CE QUE FAIT CE SCRIPT (et ce qu'il NE fait PAS) :
  - 0 hypothese neuve soumise (0/3). Matrice fermee (44 KILLED) ; les 2 leviers
    riches (porte order-flow value_gate ; detecteur transition range->tendance
    precoce) = famille NOUVELLE = strategy_families.py protege = token Sam, ET
    order-flow 9j seulement = walk-forward sous-puissant. Toute soumission
    momentum/regime serait DUPLICATE/re-knob/sign-flip. 0 = verdict discipline.
  - DEMONTRE empiriquement (a) l'auto-reparation de la frontiere + la
    distribution mi-semaine des plates (refute ma theorie week-end), et (b)
    l'invariant dedup (cellule deja jugee re-soumise -> DUPLICATE, 0 effet de
    bord, lab inchange) -> backlog #5 toujours bloque cote dedup.

PROPOSITION POUR SAM (token Sam, fichiers proteges, je ne touche pas) :
  1. Fingerprint-cle (propose 28/06) pour lever le BLOCAGE dedup du re-test 1d.
  2. Filtre d'integrite a l'ingestion : rejeter/interpoler les 55 barres GC_F_1d
     plates (O=H=L=C) avant tout backtest 1d. NB : la frontiere COURANTE est
     desormais propre (auto-reparee), mais l'INTERIEUR reste pollue a ~4.4% sur
     toute la fenetre -> un re-test 1d long historique reste contamine.
  Spec only : decision et edition = Sam.

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
    "id": "DEMO_dedup_twist_1d_2026_06_30",
    "hypothesis_text": "DEMONSTRATION (pas une hypothese neuve) : re-soumission de "
                       "la cellule deja jugee IL_pool_ichimoku_twist_1d sur le lake "
                       "rafraichi mardi. Attendu : DUPLICATE, 0 effet de bord.",
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
              f"({100*flat.mean():.1f}%) | FRONTIERE {front_t:%Y-%m-%d} "
              f"range={front_rng:.2f}{'  <-- PLATE' if front_rng == 0 else '  (VRAIE OHLC)'}")
        if flat.sum():
            ft = t[flat]
            wd = ft.dt.dayofweek.value_counts().sort_index()
            yr = ft.dt.year.value_counts().sort_index()
            print("      par jour-semaine :",
                  {_WD[k]: int(v) for k, v in wd.items()})
            print("      par annee        :", {int(k): int(v) for k, v in yr.items()})
            # gap entre derniere plate et la frontiere
            idx_flat = df.index[flat]
            gap = (len(df) - 1) - list(idx_flat)[-1]
            last_flat_t = ft.iloc[-1]
            print(f"      derniere plate   : {last_flat_t:%Y-%m-%d} "
                  f"(a {gap} barre(s) de la frontiere -> "
                  f"{'INTERIEURE' if gap > 0 else 'EN FRONTIERE'})")


def main():
    _flat_audit()
    print("\n  LECTURE : la frontiere GOLD s'est AUTO-REPAREE (forming 29/06 -> "
          "VRAIE OHLC, +30/06 VRAIE OHLC) ; la 26/06 plate est passee INTERIEURE."
          "\n  La distribution MI-SEMAINE (Tue/Wed) + multi-annees REFUTE ma "
          "theorie 'fuite settle week-end' du 29/06 : ce sont des JOURS MANQUANTS "
          "backfilles, pas un artefact week-end. Defaut reste systematique ~4.4%.")

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
    print("CONCLUSION : frontiere GOLD-1d auto-reparee (interieur encore pollue "
          "~4.4%), dedup toujours bloquant -> 0 hypothese neuve soumise (honnete).")


if __name__ == "__main__":
    main()
