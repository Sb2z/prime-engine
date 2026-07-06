#!/usr/bin/env python3
"""Experience CHERCHEUR NOCTURNE du 2026-06-28 (~23h30, nuit dimanche -> lundi).

=== LE BACKLOG #5 ("re-tester twist_1d quand le lake 1d s'epaissit") EST
    INACTIONNABLE PAR LE HARNESS TEL QUEL, demonstration empirique ===

CONSTAT D'INGESTION (re-verifie ce run, pas recopie) :
  - Pas de research/PAUSE. Budget respecte. J'ecris UNIQUEMENT dans research/.
  - Lake : 13 parquet, mtime 2026-06-28 07:00 (refresh dominical effectif).
    FRONTIERE REELLE (verifiee, ts epoch -> UTC) :
      GC_F_1d / ES_F_1d : dernier bar = 2026-06-26 (VENDREDI), OHLC REELLE
        (GC dernier 1d : O4044 / H4111 / L3998 / C4096 ; semaine volatile,
         low 3963 le 24/06 puis close 4096) -> le lake porte la SEMAINE
         COMPLETE de trading, il n'est PAS fige sur du Friday-19 perime.
      GC_F_1h / ES_F_1h : dernier bar = 2026-06-26 20:00 UTC (vendredi soir).
    TOUJOURS AUCUN 15m. Week-end -> 0 bar neuf jusqu'a lundi 29/06 07:00.
    NB : la barre 1d "plate" O=H=L=C=4078.70 vue par les analystes est le feed
    PRODUCTION TradingView CFD (fige week-end), PAS le lake yfinance (distinct,
    voulu : le backtest lake != prod, la phase PAPER revalide sur la prod).
  - lab_counters() AVANT run = {testees 45, tuees 44, papier 0, promues 0}.
    Deflation Bonferroni GLOBALE (harness.py:84-92) : test n+1 -> z_req ~3.07.
  - resim Gate-1 USER inchange (WR 56.7% n=180 exp +0.002% ; IA 12 decisifs<15,
    equity x20 1348.81 EUR == 4 slots analyste du jour, 0 derive).
  - feature_store : 4779/500, 0 ERROR, 1 MIXED exclu, 731 setups, 7j order-flow.
  - journal.json : 264 signaux (USER 180 / AI 66 / None 18), 0 fill du 28/06.
  - Aucune injection : news_cache.json (4028 ch.) + calendar_cache.json
    (49217 ch.) scannes (ignore|disregard|system prompt|rm -rf|sudo|override|
    delete|commit|exec|token) = 0 hit. Donnees externes traitees en DONNEE seule.

LE FAIT NEUF DE LA NUIT (structurel, code-verifie) :
  hypothesis_key = sha256(family, params, sorted(assets), timeframe)[:16]
  (harness.py:66-70). DEUX consequences que le backlog n'avait pas tracees :
   (1) exit_rule N'EST PAS dans la cle -> changer stop/tp/horizon ne cree PAS
       une hypothese neuve (c'est meme un re-knob deguise s'il est tente).
   (2) un doublon de cle retourne {"verdict":"DUPLICATE"} et RETOURNE AVANT
       tout _registry_append (harness.py:228-231) -> le harness NE RE-EVALUE
       JAMAIS une cellule deja jugee, MEME si le lake a gagne des barres.
  COROLLAIRE OPERATIONNEL : le backlog #5 ("re-tester twist_1d / les signaux 1d
  quand le lake 1d s'epaissit") est INACTIONNABLE tel quel. IL_pool_ichimoku_
  twist_1d a ete juge le 22/06 (KILLED, n_eff=30 PILE au seuil, exp +0.56%, IC
  [-0.007, 1.178] borne basse<0, t=1.79 << z_req=3.06). Le lake 1d a depuis
  gagne ~4 barres/actif (frontiere 22/06 -> 26/06), exactement la condition du
  backlog #5 -- mais re-soumettre la MEME cle = DUPLICATE, pas de nouveau verdict.

CE QUE FAIT CE SCRIPT (et ce qu'il NE fait PAS) :
  - Il NE soumet AUCUNE hypothese neuve (0/3). Sur cette surface (matrice fermee,
    2 leviers riches derriere des fichiers proteges/token-Sam, dedup bloquant),
    toute soumission serait un DUPLICATE, un re-knob, ou un sign-flip. 0 = le
    verdict discipline ("mortalite >90% = sante" ; ne pas bruler un cran de
    deflation pour un doublon).
  - Il DEMONTRE empiriquement le fait neuf : il re-soumet la cellule deja jugee
    IL_pool_ichimoku_twist_1d (params/assets/tf identiques au verdict 22/06) et
    montre que le harness rend DUPLICATE sans re-evaluer ni toucher le registry.
    Le chemin DUPLICATE retourne AVANT _registry_append -> 0 effet de bord, 0
    deflation brulee, lab_counters inchange (verifie avant/apres).

PROPOSITION POUR SAM (token Sam, fichier protege harness.py, je ne touche pas) :
  pour rendre le backlog #5 actionnable sans ouvrir la porte au re-knob, ajouter
  une EMPREINTE DE DONNEES a la cle OU un chemin de re-evaluation explicite, p.ex.
  inclure dans hypothesis_key un fingerprint du lake (nb de barres + ts du dernier
  bar par actif/tf). Une re-soumission a lake INCHANGE resterait DUPLICATE (bon),
  une re-soumission apres N barres neuves deviendrait une cellule distincte
  (re-test honnete sur donnee fraiche, pas un re-knob puisque family/params/exit
  sont identiques). Spec only : decision et edition = Sam.

Sources HOMOGENES (GOLD<->GC=F, US500<->ES=F, yfinance ; jamais melangees).
"""

import json
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, _ROOT)
sys.path.insert(0, os.path.join(_ROOT, "research"))
import harness
import datalake

# Cellule DEJA JUGEE le 22/06 (KILLED). Params/assets/tf IDENTIQUES au verdict
# archive -> meme hypothesis_key -> doit rendre DUPLICATE. exit_rule est hors-cle
# (harness.py:66-70) : je remets l'exit d'origine par exactitude documentaire.
_DEMO_DUPLICATE = {
    "id": "DEMO_dedup_twist_1d_2026_06_28",
    "hypothesis_text": "DEMONSTRATION (pas une hypothese neuve) : re-soumission de "
                       "la cellule deja jugee IL_pool_ichimoku_twist_1d sur un lake "
                       "1d epaissi (frontiere 22/06 -> 26/06). Attendu : DUPLICATE, "
                       "0 re-evaluation, 0 effet sur le registry/la deflation.",
    "family": "ichimoku_twist",
    "params": {"speed": "standard"},
    "exit_rule": {"stop_pct": 1.2, "tp_pct": 2.4, "horizon_bars": 10},
    "assets": ["GOLD", "US500"], "timeframe": "1d",
    "_lake": {"GOLD": "GC=F", "US500": "ES=F"},
}


def main():
    print("=== lab_counters AVANT ===")
    before = harness.lab_counters()
    reg_len_before = len(harness.registry())
    print(json.dumps(before, ensure_ascii=False), "| registry len =", reg_len_before)

    s = dict(_DEMO_DUPLICATE)
    lake_map = s.pop("_lake")
    print("\nhypothesis_key(demo) =", harness.hypothesis_key(s))
    data, sources = {}, {}
    for asset, ticker in lake_map.items():
        candles, src = datalake.load_candles(ticker, s["timeframe"])
        data[asset] = candles
        sources[asset] = src
    r = harness.evaluate(s, data, sources=sources)
    print("verdict =", r["verdict"], "|", r.get("note", ""))

    print("\n=== lab_counters APRES ===")
    after = harness.lab_counters()
    reg_len_after = len(harness.registry())
    print(json.dumps(after, ensure_ascii=False), "| registry len =", reg_len_after)
    print("\nINVARIANT (0 effet de bord) :",
          "OK" if (before == after and reg_len_before == reg_len_after
                   and r["verdict"] == "DUPLICATE") else "VIOLE")
    print("CONCLUSION : backlog #5 (re-test sur lake epaissi) inactionnable par "
          "le harness tel quel ; 0 hypothese neuve soumise cette nuit.")


if __name__ == "__main__":
    main()
