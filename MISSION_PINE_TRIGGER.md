# MISSION — Intégration Pine "Prime Trend Day Trigger" via claudeverstradingview

Contexte : le MCP claudeverstradingview est installé (TradingView Desktop piloté
en CDP localhost:9222). Le fichier pine/prime_trend_day.pine réplique
trend_day_trigger.py. Objectif : le déployer sur les charts GOLD et US500,
PROUVER la parité avec le Python, et créer les alertes TradingView miroir.

Règles inchangées : signal-only (aucun outil UI sur un quelconque panel de
trading), watcher totalement découplé du MCP (si TradingView Desktop est fermé,
rien dans le système autonome ne doit échouer), Gate 1 intact.

## Étape 0 — Rangement
- Créer le dossier pine/ dans /Users/sam/trading, y mettre prime_trend_day.pine.
- L'ajouter au repo git (c'est du code, pas du runtime).

## Étape 1 — Compilation et déploiement
- tv_health_check d'abord. Si KO, demander à Sam de lancer le script
  launch_tv_debug_mac.sh et s'arrêter là.
- Compiler le script via l'outil pine du MCP (pine_smart_compile / check).
  Corriger les erreurs de syntaxe v6 éventuelles SANS toucher aux formules
  (ER n=39, ADX 14 Wilder, EMA50, MACD 12/26/9, seuils 30/0.45) ni aux textes.
- Sauvegarder l'indicateur dans le compte TradingView de Sam et l'ajouter
  sur le chart 15m GOLD (CFD, le même symbole que SYMBOL_MAP de tv_candles)
  puis US500. Screenshot de chaque chart en preuve.

## Étape 2 — Test de parité Pine vs Python (le cœur de la mission)
Créer scripts/compare_pine_parity.py :
- Côté Python : datafeed.get_candles(asset, "15m", 60) et ("1h", 100), puis
  calculer ADX, ER, dir15, dir1h, armed avec les fonctions EXISTANTES
  (tv_candles compute_ta + regime.efficiency_ratio + trend_day_trigger).
  Ne pas réimplémenter — importer.
- Côté Pine : lire les valeurs affichées par l'indicateur sur le chart via le
  MCP (stream values / lecture du status line ou de la table).
- Comparer avec tolérances : |ΔADX| <= 1.5 pts, |ΔER| <= 0.02, directions
  identiques, état armed identique. (Les deux lisent le même feed TradingView,
  l'écart vient seulement de la fenêtre de bougies et du seeding Wilder.)
- Sortie : tableau PASS/FAIL par actif. Si FAIL sur ER ou direction, c'est un
  bug de formule → corriger le Pine, jamais le Python (le Python est la
  référence, c'est lui qui a l'historique du forward-test).
- Lancer le test à deux moments espacés d'au moins 1h, coller les deux
  sorties dans LESSONS.md section "Parité Pine".

## Étape 3 — Alertes TradingView miroir
- Via alert_create du MCP : une alerte par actif sur les conditions
  "Prime ARMÉ LONG", "Prime ARMÉ SHORT" et "Prime DÉSARMÉ" de l'indicateur
  (option "Une fois par clôture de bougie" si confirmOnly=true, sinon
  "Une fois par minute" max pour éviter le spam).
- Résultat : deux canaux indépendants — Telegram (watcher Python) et push
  TradingView (Pine). Si l'un se tait pendant que l'autre parle, c'est un
  signal de panne d'un des deux systèmes : noter cette règle dans LESSONS.md.
- NE PAS supprimer ni modifier les alertes existantes de Sam (alert_list
  d'abord, toucher uniquement aux alertes créées par cette mission).

## Étape 4 — Désynchronisation surveillée
- Ajouter au résumé quotidien Telegram du watcher une ligne "Pine parité :
  dernier check OK/KO/inconnu" : le watcher lit un petit fichier
  pine_parity_status.json que compare_pine_parity.py écrit à chaque run.
  Le watcher ne lance JAMAIS le check lui-même (découplage : pas de
  dépendance CDP dans la boucle autonome) — il ne fait que lire le fichier
  s'il existe et afficher son âge.
- Proposer à Sam un alias shell `parite` qui lance le script quand
  TradingView Desktop est ouvert.

## Critères d'acceptation
1. Indicateur compilé, visible sur les charts GOLD et US500 15m (screenshots).
2. compare_pine_parity.py : PASS sur les deux actifs, deux runs espacés.
3. Alertes TV créées et listées, alertes préexistantes intactes.
4. Watcher : aucun nouvel import lié au MCP/CDP, résumé quotidien enrichi
   de la ligne parité, py_compile OK partout.
5. Un commit par étape.

## Pièges connus (à vérifier explicitement)
- request.security et le symbole : l'indicateur doit tourner sur le MÊME
  symbole CFD que le watcher (SYMBOL_MAP), pas sur GC=F/ES=F, sinon le test
  de parité compare deux instruments différents (basis).
- ta.dmi de Pine et ADXIndicator de la lib ta : même Wilder mais seeding
  différent sur les premières barres → c'est pour ça que la tolérance ADX
  est 1.5 pts avec 60 bougies. Si l'écart dépasse, augmenter n_bars côté
  Python à 150 et re-tester avant de conclure à un bug.
- confirmOnly=false par défaut = parité avec le watcher (évaluation live),
  donc l'état ARMÉ peut clignoter intrabar exactement comme le Python peut
  s'armer puis se dégrader (cas de la nuit du 10/06). C'est voulu : les deux
  systèmes doivent dire la même chose au même moment, y compris se tromper
  pareil.
