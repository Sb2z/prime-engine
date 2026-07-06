#!/usr/bin/env python3
"""Experience CHERCHEUR NOCTURNE du 2026-06-19 (~23h45).

=== 0 SOUMISSION AU JUGE CE SOIR, par EPUISEMENT du lake, pas par paresse ===

Ce fichier ne soumet RIEN a harness.evaluate. Il documente (a) la verification
qui conduit a 0 hypothese lake-jugeable nouvelle, et (b) un MINING DESCRIPTIF
report-only des 291 setups production (hors-lake) qui motive les specs portees
a Sam dans le rapport. Aucun verdict n'en sort : le score composite production
n'est PAS dans le lake, donc ces mesures ne sont pas harness-jugeables et
restent au rapport (regle reconduite des nuits precedentes).

POURQUOI 0 (chaine de verification, pas un a-priori) :
  1. Les 11 familles de strategy_families.py ont TOUTES ete soumises au juge et
     TOUTES tuees : momentum, mean_reversion, session_hour, cot_extreme,
     momentum_regime, momentum_breakout, et les 5 ichimoku. Registry = 38/37.
  2. cot_extreme est la seule famille a n'avoir que 2 instances (HD gold, HE es).
     Or le lake ne contient de COT que pour GOLD et US500 (cot_5y.parquet :
     assets = {GOLD, US500}), les deux sont DEJA tues (contrarian 10/90,
     negatif des deux cotes). Le ressusciter exigerait :
       - changer l'EXIT (ce qu'aurait fait IF_gold_cot_extreme_1d, prepare au
         slot 17h mais NON soumis) => sweep d'exit pour sauver un signal mort.
       - passer mode="follow" => sign-flip apres avoir vu contrarian tue.
     Les deux sont explicitement interdits par le protocole. cot_extreme est
     donc EPUISE sur le lake.
  3. Les frontieres encore vivantes (momentum localise par session infra-horaire ;
     mean_reversion conditionnee a un regime RANGE ; vol-extreme via VIX ;
     momentum x COT-non-foule composee ; politique exit/lock §81a) exigent TOUTES
     soit une NOUVELLE famille (hook protege strategy_families.py => token Sam),
     soit des donnees absentes du lake (barres < 1h ; MFE/MAE marche-vs-fill de
     production). Aucune n'est jugeable cette nuit.
  4. Forcer un 39e test serait churner la deflation Bonferroni GLOBALE pour zero
     information neuve, exactement l'anti-pattern que le protocole existe pour
     empecher. "0 test force" (cf. rapport nocturne 18/06) est de la SANTE.

Le mining ci-dessous est OBSERVATIONNEL (pas d'IC, comparaisons multiples, proxy
ret_4h a horizon fixe sans stops ni couts). Il NE conclut RIEN, il signale deux
anomalies a investiguer et chiffre la conditionnalite regime/session qui motive
les specs (famille composee + vol_extreme) portees a Sam.
"""

import os
import sys

import pandas as pd

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def mine_setups():
    """Mining descriptif report-only des setups A_SETUP/WATCH avec outcome OK."""
    f = pd.read_parquet(os.path.join(_ROOT, "feature_exports", "features.parquet"))
    o = pd.read_parquet(os.path.join(_ROOT, "feature_exports", "outcomes.parquet"))
    m = f.merge(o, on=["ts", "asset"], how="inner")
    m = m[(m["ret_4h"].notna()) & (m["outcome_quality"] == "OK")]
    m = m[m["session"].fillna("") != "WEEKEND"]
    setups = m[m["grade"].isin(["A_SETUP", "WATCH"])].copy()

    def signed(row):
        d = str(row["direction"]).upper()
        r = row["ret_4h"]
        if "SHORT" in d or d == "SELL":
            return -r
        if "LONG" in d or d == "BUY":
            return r
        return None

    setups["dir_ret4h"] = setups.apply(signed, axis=1)
    s = setups[setups["dir_ret4h"].notna()]
    print(f"setups directionnels avec outcome OK : {len(s)}")
    print("\n=== ret_4h SIGNE (%) par GRADE ===")
    print(s.groupby("grade")["dir_ret4h"].agg(["count", "mean"]).round(4))
    print("\n=== par SESSION ===")
    print(s.groupby("session")["dir_ret4h"].agg(["count", "mean"]).round(4))
    print("\n=== par REGIME ===")
    print(s.groupby("regime")["dir_ret4h"].agg(["count", "mean"]).round(4))
    print("\n=== SESSION x REGIME (n>=10) ===")
    g = s.groupby(["session", "regime"])["dir_ret4h"].agg(["count", "mean"]).round(4)
    print(g[g["count"] >= 10])
    print("\nRAPPEL : report-only. Pas d'IC, comparaisons multiples, proxy 4h sans "
          "stops/couts. AUCUNE conclusion, motive des specs, pas un verdict.")


if __name__ == "__main__":
    mine_setups()
