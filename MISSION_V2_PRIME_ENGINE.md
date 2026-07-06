# MISSION V2, PRIME ENGINE : data fiable, feature store, event engine

Prérequis : MISSION_FIX_MESURE.md est terminée (mesure honnête, dédup, coûts,
fills 1m, IC affichés). Cette mission V2 construit l'infrastructure qui permettra
de PROUVER un edge, pas d'en décréter un. Règle inchangée : signal-only, aucun
ordre automatique, et aucun assouplissement des garde-fous statistiques.

Principe directeur : le facteur limitant n'est pas la sophistication du modèle,
c'est (1) la qualité/fiabilité des données, (2) la taille d'échantillon,
(3) les coûts d'exécution. V2 attaque ces trois points dans cet ordre.

---

## PHASE A, Couche données fiable (remplace les sources fragiles)

### A1. Prix et bougies : redondance + officialisation
Problème actuel : tout repose sur le websocket TradingView non officiel (tv_live,
tv_candles). Il peut casser sans préavis et il n'a PAS de volume réel pour les CFD.

- Créer `datafeed.py` : interface unique `get_price(asset)`, `get_candles(asset, tf, n)`
  avec chaîne de fallback : source primaire → TradingView WS → yfinance (GC=F, ES=F,
  ^GSPC) → dernière valeur cache avec flag `stale: true`.
- Chaque réponse porte `source` et `latency_ms`. Le watcher logge la source utilisée.
- Mapping des sous-jacents RÉELS : GOLD ↔ futures COMEX GC, US500 ↔ futures CME ES.
  C'est sur les futures qu'existent le volume réel, le carnet et l'order flow.

### A2. Order flow réel (le vrai upgrade quant)
Le CFD Revolut n'a ni volume ni carnet. Le carnet réel de l'or et du S&P, c'est
CME Globex. Deux options, à choisir selon budget (NE PAS implémenter les deux) :

- Option éco (~12-30 $/mois) : compte Interactive Brokers (paper account suffit)
  + souscription market data CME non-pro. API via ib_insync : ticks temps réel,
  volume réel, profondeur L2 (DOM) sur GC et ES. Module `ibkr_feed.py`.
- Option pro (~179 $/mois) : Databento GLBX.MDP3 plan Standard, full order book
  MBP-10 sur GC/ES, API Python propre, historique tick au même endroit.
  Module `databento_feed.py`. (Le live usage-based n'existe plus depuis 2025,
  c'est abonnement.)

À construire au-dessus (module `orderflow2.py`, remplace progressivement orderflow.py) :
- Volume profile RÉEL par session (POC/VAH/VAL sur vrai volume, plus l'approximation actuelle)
- Delta cumulé (agressions achat vs vente par bougie 1m)
- Imbalance du carnet top-5 niveaux + détection d'absorption près des niveaux SMC
- CVD divergence prix/delta comme feature de confirmation des setups Prime

### A3. Calendrier macro structuré (consensus vs actual = la donnée du jour NFP)
Le jour de surperformance de Sam (+30%) était un jour NFP à surprise. Le système
doit connaître consensus, actual et la surprise normalisée, pas juste "NFP à 14:30".

- `calendar_feed.py` : source primaire le JSON hebdo public ForexFactory
  (ff_calendar_thisweek.json), cache local, refresh 1h, parsing en
  {event, currency, impact, time_utc, forecast, previous, actual}.
- Fallback : calendrier MQL5 ou API JBlanked (limitée à 1 req/jour en free → cache).
- À la sortie d'un chiffre high-impact US : calculer surprise_z =
  (actual - forecast) / écart-type historique des surprises de CET événement
  (constituer l'historique au fil de l'eau dans le feature store).
- Brancher dans news_radar : fenêtre pré-event (veto nouveaux trades T-30min),
  fenêtre post-event (mode "event day" si |surprise_z| > 1).

### A4. Positionnement et options
- `cot_feed.py` : rapport COT CFTC hebdomadaire (CSV public gratuit) pour GC et ES.
  Features : net specs, variation 4 semaines, percentile 3 ans. Mise à jour vendredi soir.
- Options : garder la source actuelle de options.py pour SPX ; pour l'or, les options
  COMEX ne sont accessibles proprement que via Databento (si option pro choisie).
  Sinon, marquer le pilier options GOLD comme `quality: LOW` dans la confluence
  au lieu de faire semblant.

### A5. Crypto (déjà connecté, coût zéro)
Le MCP Revolut X donne carnet L2, trades publics et bougies BTC/ETH en live.
- `crypto_pulse.py` : imbalance carnet BTC + delta trades publics 5min, utilisé
  comme capteur risk-on/risk-off intrajournalier (corrélation BTC/ES en régime
  risk-off) et, si Sam trade BTC/ETH, comme order flow natif pour ces actifs.

## PHASE B, Feature store (la condition de tout apprentissage futur)

Problème : les poids de forecast.py (0.55/0.30/0.15...) sont inventés à la main et
invérifiables, car les snapshots ne sont pas stockés de façon requêtable.

- `feature_store.py` : DuckDB (fichier unique prime.duckdb) + export Parquet.
- À CHAQUE cycle du watcher, persister une ligne par actif :
  ts, prix, TA des 4 timeframes, régime (ER/ADX), score macro, biais news,
  surprise_z active, order flow (delta, imbalance, POC dist), SMC (structure,
  distance OB/FVG), COT percentile, VIX, DXY, session, et la décision Prime
  (grade, conf, vetos).
- Et une table `outcomes` : pour chaque ts, le rendement réalisé à +15m, +1h, +4h
  (rempli par un job de backfill qui tourne avec les bougies 1m).
- C'est CE dataset qui permettra, dans 4-8 semaines, de remplacer les poids
  manuels par des poids appris en walk-forward. Interdit avant : < 500 lignes
  exploitables = pas d'apprentissage.

## PHASE C, Event engine et mode "jour de tendance"

L'edge documenté de Sam (LESSONS.md, validé sur ses 57 trades réels) :
shorts en downtrend fort + scalp micro-rebond les jours ADX>30 propres (ER élevé).

- `trend_day_trigger.py` : détecteur temps réel du régime TENDANCE PROPRE
  (réutilise regime.py) + conditions d'armement : ADX 15m > 30, ER > 0.45,
  alignement 1h/4h, et idéalement surprise macro le jour même.
  Quand armé → alerte explicite "MODE SCALP TENDANCE : conditions du 5 juin réunies"
  avec direction, zones de rebond (VWAP, EMA20 15m, OB), et rappel des règles
  (sens de la tendance uniquement, sortie rapide, stop ATR).
- C'est l'inverse de Prime (qui cherche des swings RR>=2) : deux modes distincts,
  jamais actifs en même temps, le régime décide.
- Alerting : `notify.py` via bot Telegram (token en .env) : A_SETUP, trend-day armé,
  pré-event T-30, et résumé quotidien (stats effectives + IC).

## PHASE D, Validation et apprentissage (gates stricts)

- Gate 1 (immédiat) : 4 semaines de forward-test avec la mesure V1 corrigée.
  Aucun changement de seuils pendant la fenêtre. resim_report.py hebdomadaire.
- Gate 2 (si Gate 1 montre espérance nette > 0 avec borne basse IC > 0 sur les
  trades effectifs) : autoriser l'augmentation du sizing quart-Kelly au-delà du
  plancher 1%.
- Gate 3 (>= 500 lignes feature store avec outcomes) : entraîner une régression
  logistique L2 (pas plus complexe) prédisant P(TP avant SL) en walk-forward
  purgé (purge 1 jour entre train et test pour l'autocorrélation). La proba
  remplace/complète le score de confluence SEULEMENT si l'AUC test > 0.58 sur
  3 fenêtres consécutives. Sinon on garde la confluence actuelle.
- Métriques toujours nettes de coûts, toujours sur trades effectifs (dédup),
  toujours avec IC. Tout résultat sans IC est invalide par convention.

## Ordre d'exécution et budget

1. A1 datafeed + fallback (0 €), fiabilité d'abord.
2. A3 calendrier consensus/actual (0 €) + B feature store (0 €).
3. C trend_day_trigger + Telegram (0 €), exploite l'edge déjà documenté de Sam.
4. A4 COT (0 €), A5 crypto pulse (0 €).
5. A2 order flow réel, SEUL poste payant. Recommandation : commencer par
   l'option IBKR éco ; passer Databento seulement si l'order flow démontre,
   dans le feature store, un pouvoir prédictif (corrélation outcome) qui le justifie.
6. D : les gates, dans l'ordre, sans exception.

## Contraintes inchangées

- Signal-only. Aucun ordre automatique, sur aucun connecteur, jamais.
- Aucun secret en clair dans le repo (.env ignoré, déjà fait).
- Un commit par module, py_compile + smoke test à chaque étape.
- Les seuils statistiques de la mission V1 (n>=15 effectifs, IC Wilson, walk-forward)
  ne sont JAMAIS assouplis pour faire passer un résultat.
