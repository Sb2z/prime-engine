# MISSION V3 — PRIME RESEARCH LAB : recherche autonome, promotion sous contrôle

Objectif : donner au système la capacité de chercher, tester et améliorer des
stratégies DE LUI-MÊME, sans jamais lui donner la capacité de se mentir.
Le danger n°1 d'un système auto-améliorant n'est pas qu'il ne trouve rien,
c'est qu'il "améliore" ses propres garde-fous jusqu'à valider du bruit
(reward hacking). Toute l'architecture V3 découle de ça.

## Principe constitutionnel : séparation des pouvoirs

1. LE CHERCHEUR (autonome, libre) — propose des hypothèses, fouille les
   données, lit internet, code des expériences dans research/. Il peut tout
   essayer, il ne peut rien promouvoir.
2. LE JUGE (harness.py, gelé) — valide ou tue chaque expérience selon des
   règles immuables. Le chercheur ne peut pas modifier le juge.
3. LE PROMOTEUR (Sam, humain) — seul habilité à faire passer une stratégie
   du papier aux alertes réelles, sur dossier présenté par le chercheur
   et tamponné par le juge.

Application technique de la séparation :
- Nouveau dossier research/ : seul espace d'écriture du chercheur autonome.
- harness.py, prime core (prime_strategy, journal, clusters, costs,
  feature_store, regime, trend_day_trigger), et ce brief : protégés par un
  pre-commit hook git qui REFUSE tout commit les modifiant si le fichier
  research/HUMAN_APPROVAL ne contient pas un token frais écrit par Sam.
  Le hook lui-même est dans .githooks/ versionné, installé via
  git config core.hooksPath.
- Le watcher de production ne lit JAMAIS rien dans research/ sauf la
  liste paper_strategies.json validée par le juge (voir pipeline).

## Le juge : harness.py (à écrire UNE fois, puis gelé)

Entrée : une stratégie au format standard
  strategy = {id, hypothesis_text, family, params,
              signal_fn(features_row) -> LONG/SHORT/None,
              exit_rule, assets, timeframe}
Validation imposée à toutes les expériences, sans exception :
- Données : feature store + bougies historiques du data lake. Split
  walk-forward purgé (purge 1 jour), minimum 3 fenêtres, jamais de test
  sur des données vues.
- Coûts systématiques via costs.py (spread session/off, slippage, swap).
- Dédup : signaux clusterisés comme en production (clusters.py).
- Correction de comparaisons multiples GLOBALE : le harness tient un
  compteur à vie de toutes les expériences jamais testées
  (hypothesis_registry.json, append-only). Le seuil de significativité se
  déflate avec ce compteur (Bonferroni-style sur la famille, déflated
  Sharpe ratio en métrique). Tester 1000 idées rend automatiquement le
  seuil 1000 fois plus dur. C'est LA défense contre le data mining infini.
- Verdicts possibles : KILLED (défaut attendu ~95% des cas), PAPER
  (espérance nette > 0, borne basse IC > 0 sur >= 2 fenêtres sur 3,
  n effectif >= 30 sur le backtest).
- Sortie : rapport JSON signé (hash du code de la stratégie + hash du
  harness) dans research/verdicts/. Un verdict sans les deux hashes
  est invalide par convention.

## Le chercheur : boucle autonome nocturne

Mécanique : cron à 23h30 Paris qui lance une session Claude Code headless
(claude -p) avec research/RESEARCH_PROTOCOL.md comme instruction, budget
plafonné (tokens + durée max 45 min + kill switch fichier research/PAUSE).
La session a accès à internet (lecture), au data lake, à research/.

RESEARCH_PROTOCOL.md (à écrire dans cette mission) impose le cycle :
1. INGESTION — lire le rapport du jour : resim_report, nouvelles lignes
   feature store, trades réels de Sam du jour, événements macro.
2. AUTOPSIE — chaque signal de la veille (Prime, trend-day, paper
   strategies) : prévu vs réalisé. Mettre à jour research/autopsy.md.
3. HYPOTHÈSES — proposer max 3 hypothèses NOUVELLES (le registry refuse
   les doublons, similarité sur hypothesis_text + family + params).
   Sources d'inspiration autorisées : familles d'effets documentés
   (momentum intraday, mean reversion post-excès, dérive post-événement
   macro, saisonnalité horaire/session, extrêmes COT, transitions de
   régime vol, gaps week-end), littérature publique (SSRN, papers),
   et SURTOUT le mining des données propres : les 80+ trades réels de Sam
   et le feature store (ex. "le WR de Sam chute après 2 pertes
   consécutives ?", "les A_SETUP en EVENT_DAY surperforment ?").
4. EXPÉRIENCES — coder chaque hypothèse au format standard, soumettre au
   harness, archiver le verdict. Interdit de re-soumettre une variante
   mineure d'une idée KILLED sans la déclarer comme variante (le registry
   compte les familles).
5. RAPPORT — research/reports/YYYY-MM-DD.md : ce qui a été testé, tué,
   passé en papier, + le backlog priorisé pour demain. Résumé en 5 lignes
   envoyé sur Telegram dans le résumé quotidien.

## Pipeline de promotion (aucun raccourci possible)

IDEA → BACKTEST (harness) → PAPER → CANDIDATE → LIVE-ALERTES
- PAPER : la stratégie entre dans research/paper_strategies.json. Le
  watcher l'évalue en shadow : signaux journalisés (trader=PAPER_<id>)
  avec coûts, dédup, AUCUNE alerte Telegram. Durée minimum 4 semaines OU
  20 trades effectifs, au premier atteint.
- CANDIDATE : si le forward papier confirme (espérance nette > 0, borne
  basse IC > 0), le chercheur monte un dossier (backtest + forward + code
  + limites connues) et notifie Sam. RIEN ne change tant que Sam n'écrit
  pas le token dans HUMAN_APPROVAL.
- LIVE-ALERTES : alertes Telegram actives, sizing plancher 1% pendant
  encore 15 trades effectifs (la règle V1 s'applique aux nouvelles
  stratégies comme aux anciennes).
- Rétrogradation automatique : toute stratégie LIVE ou PAPER dont la borne
  haute IC de l'espérance passe sous 0 sur fenêtre glissante de 30 trades
  retourne en KILLED. Le juge rétrograde sans demander.

## Data lake (research/data/)

- Bougies historiques : backfill yfinance quotidien+horaire 5 ans
  (GC=F, ES=F, ^GSPC, DXY, ^VIX, ZN=F), stocké en Parquet. Pour l'intraday
  fin : Dukascopy tick gratuit pour XAUUSD (downloader public), sinon le
  feature store qui s'accumule reste la source 1m de référence.
- Historique COT 5 ans via la même API Socrata (une requête, cache).
- Historique calendrier : calendar_history.json s'enrichit chaque jour ;
  backfill des grands événements passés (NFP/CPI/FOMC 3 ans) depuis les
  archives publiques si disponible, sinon au fil de l'eau.
- AUCUNE donnée à symbole différent mélangée dans un même test (le harness
  vérifie l'homogénéité de source, garde anti-basis héritée de V2).

## Garde-fous spécifiques à l'autonomie

- Signal-only absolu : rien dans research/ ne peut importer un module
  d'exécution d'ordres (il n'en existe pas, et le hook bloque l'ajout de
  dépendances broker dans le projet).
- Budget : la session nocturne s'arrête à 45 min ou au plafond de tokens.
  Pas de session si research/PAUSE existe.
- Le chercheur ne touche pas aux seuils de production : Gate 1/2/3 de la
  V2 restent gérés à la main.
- Transparence : tout est committé (recherche incluse), Telegram quotidien
  résume, et l'historique des verdicts est append-only.
- Réalisme affiché : le rapport quotidien commence par le compteur
  "hypothèses testées / tuées / en papier / promues" — le taux de mortalité
  attendu est >90% et c'est un signe de SANTÉ du système, pas d'échec.

## Ordre d'exécution

1. Hooks git + structure research/ + hypothesis_registry (la séparation
   des pouvoirs AVANT toute intelligence).
2. harness.py + 2 stratégies-test bidons (une qui doit passer sur données
   synthétiques, une qui doit être tuée) pour valider le juge lui-même.
3. Data lake backfill (yfinance 5 ans, COT 5 ans, Dukascopy XAUUSD si simple).
4. Mode shadow PAPER dans le watcher (lecture de paper_strategies.json).
5. RESEARCH_PROTOCOL.md + premier run MANUEL supervisé de la boucle
   chercheur (pas de cron tant que Sam n'a pas relu un rapport complet).
6. Cron nocturne + kill switch + budget. Activation sur accord de Sam.
