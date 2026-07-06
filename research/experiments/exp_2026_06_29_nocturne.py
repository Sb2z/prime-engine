#!/usr/bin/env python3
"""Experience CHERCHEUR NOCTURNE du 2026-06-29 (nuit lundi -> mardi).

=== FAIT NEUF DE LA NUIT : un SECOND blocage, independant du dedup, frappe le
    backlog #5, la barre GOLD 1d de FRONTIERE est CORROMPUE (plate O=H=L=C),
    et le defaut est SYSTEMATIQUE sur GC_F_1d (55 barres plates) / ABSENT sur ES ===

CONSTAT D'INGESTION (re-verifie ce run, pas recopie) :
  - Pas de research/PAUSE. Budget respecte. J'ecris UNIQUEMENT dans research/.
  - Lake : 13 parquet, REFRESH lundi mtime 2026-06-29 07:00 (marche rouvert).
    FRONTIERE REELLE (verifiee, ts epoch -> UTC) :
      GC_F_1d / ES_F_1d : dernier bar = 2026-06-29 (LUNDI, barre EN FORMATION).
      GC_F_1h / ES_F_1h : dernier bar = 2026-06-29 04:00 UTC.
    TOUJOURS AUCUN 15m.
  - lab_counters() = {testees 45, tuees 44, papier 0, promues 0} (inchange).
    Deflation Bonferroni GLOBALE (harness.py:84-92) : test n+1 -> z_req ~3.07.
  - resim Gate-1 USER inchange (WR 56.7% n=180 exp +0.002% ; IA 12 decisifs<15,
    equity x20 1348.81 EUR, 0 derive).
  - feature_store : 5202/500, 0 ERROR, 1 MIXED exclu, 733 setups, 8j order-flow.
  - journal.json : 264 signaux (USER 180 / AI 66 / None 18), 0 fill du 29/06,
    last_updated toujours 26/06 (artefact import, hors research/, je n'y touche pas).
  - Aucune injection : news_cache.json + calendar_cache.json scannes
    (ignore|disregard|system prompt|rm -rf|sudo|override|delete|commit|exec|token)
    = 0 token imperatif (4 hits "edit" = sous-chaines "Cr-edit" ForexFactory, benins).
    Donnees externes traitees STRICTEMENT en DONNEE.

LE FAIT NEUF (structurel, code+donnee-verifie), DEUX blocages independants sur #5 :
  BLOCAGE 1 (etabli 28/06, re-confirme ici) : dedup gele le re-test.
    hypothesis_key = sha256(family, params, sorted(assets), timeframe)[:16]
    (harness.py:66-70) ; un doublon retourne DUPLICATE AVANT _registry_append
    (harness.py:228-231) -> jamais de re-evaluation meme si le lake gagne des barres.
  BLOCAGE 2 (NEUF cette nuit) : la donnee de frontiere GOLD est CORROMPUE.
    Apres le refresh lundi 07:00, la barre GC_F_1d du 26/06 n'est plus la vraie
    OHLC (28/06 : O4044/H4111/L3998/C4096) mais une barre PLATE O=H=L=C=4078.70
    (== exactement la valeur figee du feed PRODUCTION week-end). Le defaut est
    SYSTEMATIQUE et SPECIFIQUE A L'OR : GC_F_1d porte 55 barres plates sur tout
    son historique (~4.4%), ES_F_1d en porte 0. Une barre plate a un range vrai
    NUL -> un signal ichimoku/twist 1d calcule dessus degenere (Tenkan=Kijun=close
    sur la fenetre, twist illusoire). DONC : meme si BLOCAGE 1 etait leve par un
    fingerprint-cle, re-tester twist_1d sur le lake "epaissi" injecterait une barre
    GOLD corrompue a la frontiere. Le backlog #5 est doublement bloque.

  CORRECTION HONNETE de mon cadrage du 28/06 : j'avais ecrit "la barre plate
  4078.70 est le feed PRODUCTION, PAS le lake yfinance (distinct)". FAUX en partie :
  le refresh lundi a fait FUIR cette valeur plate DANS le lake GC_F_1d du 26/06.
  Le lake n'est donc pas immunise contre l'artefact plat de l'or, il en porte
  meme 55 exemplaires historiques. ES reste propre (0). A signaler a Sam.

CE QUE FAIT CE SCRIPT (et ce qu'il NE fait PAS) :
  - 0 hypothese neuve soumise (0/3). Matrice fermee (44 KILLED), 2 leviers riches
    derriere fichiers proteges (token Sam), dedup bloquant, ET maintenant donnee
    GOLD-1d de frontiere corrompue -> toute soumission serait DUPLICATE/re-knob/
    sign-flip ou contaminee. 0 = verdict discipline.
  - DEMONTRE empiriquement (a) l'invariant dedup (IL re-soumise -> DUPLICATE, 0
    effet de bord, lab inchange) et (b) le defaut de donnee (compte des barres
    plates GC vs ES, barre de frontiere GOLD plate, range vrai nul).

PROPOSITION POUR SAM (token Sam, fichiers proteges, je ne touche pas) :
  1. Fingerprint-cle (deja propose 28/06) pour lever BLOCAGE 1.
  2. NOUVEAU : filtre d'integrite a l'ingestion du lake, rejeter/interpoler les
     barres 1d plates (O=H=L=C) de GC_F (55 barres) avant tout backtest 1d, sinon
     tout signal 1d sur l'or est pollue a ~4.4% (et a la frontiere actuelle).
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
# archive -> meme hypothesis_key -> doit rendre DUPLICATE (BLOCAGE 1).
_DEMO_DUPLICATE = {
    "id": "DEMO_dedup_twist_1d_2026_06_29",
    "hypothesis_text": "DEMONSTRATION (pas une hypothese neuve) : re-soumission de "
                       "la cellule deja jugee IL_pool_ichimoku_twist_1d sur le lake "
                       "rafraichi lundi. Attendu : DUPLICATE, 0 effet de bord.",
    "family": "ichimoku_twist",
    "params": {"speed": "standard"},
    "exit_rule": {"stop_pct": 1.2, "tp_pct": 2.4, "horizon_bars": 10},
    "assets": ["GOLD", "US500"], "timeframe": "1d",
    "_lake": {"GOLD": "GC=F", "US500": "ES=F"},
}


def _flat_audit():
    print("=== BLOCAGE 2 : integrite des barres 1d (defaut plat O=H=L=C) ===")
    for f, tick in [("GC_F_1d", "GOLD"), ("ES_F_1d", "US500")]:
        df = pd.read_parquet(os.path.join(_DATA, f + ".parquet"))
        tcol = "ts" if "ts" in df.columns else df.columns[0]
        t = pd.to_datetime(df[tcol], unit="s", utc=True)
        flat = (df["open"] == df["high"]) & (df["high"] == df["low"]) & (df["low"] == df["close"])
        last = df.iloc[-2]  # derniere barre COMPLETE (la -1 est en formation lundi)
        last_t = t.iloc[-2]
        rng = float(last["high"]) - float(last["low"])
        print(f"  {f:9s} ({tick:6s}) : {len(df)} barres, PLATES={int(flat.sum())} "
              f"({100*flat.mean():.1f}%) | frontiere COMPLETE {last_t:%Y-%m-%d} "
              f"O={last['open']:.2f} H={last['high']:.2f} L={last['low']:.2f} "
              f"C={last['close']:.2f} range={rng:.2f}"
              f"{'  <-- PLATE/CORROMPUE' if rng == 0 else ''}")


def main():
    _flat_audit()

    print("\n=== BLOCAGE 1 : dedup gele le re-test (invariant) ===")
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
    print("CONCLUSION : backlog #5 doublement bloque (dedup + donnee GOLD-1d "
          "corrompue a la frontiere) ; 0 hypothese neuve soumise cette nuit.")


if __name__ == "__main__":
    main()
