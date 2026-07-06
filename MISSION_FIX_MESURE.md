# MISSION — Fiabiliser la mesure du protocole Prime avant toute optimisation

Contexte : projet /Users/sam/trading. Le journal (journal.json) montre IA 79.2% WR n=24
et OTE_RETRACEMENT 100% n=9, mais ces stats sont gonflées par quatre biais identifiés :

1. Pseudo-réplication : le watcher re-signale le même trade toutes les heures.
   Preuve : 7 des 9 trades OTE sont des shorts US500 du 7 juin entre 15h30 et 23h21,
   pnl_pct identique 1.583 répété. Échantillon effectif réel : 2-3 trades, pas 9.
2. Zéro coût de transaction : journal.evaluate_open() clôture à exit_price = tp1 exact.
   Aucun spread, slippage, ni swap. Les trades USER sont des fills réels Revolut.
3. Fills échantillonnés aux scans : hi_since/lo_since ne sont mis à jour qu'au moment
   des runs (5 min au mieux). Les mèches entre deux scans sont invisibles, ce qui rate
   des touches de stop et biaise vers WIN.
4. WIN_TIME compté comme win plein dans toutes les stats.

Plus un cinquième problème : adaptive_edge.build_candidates() génère ~300 candidats
(72 fenêtres horaires x 3 largeurs, x actif, x direction) testés sur ~24 trades
autocorrélés avec MIN_TEST_N=3. C'est du data mining garanti.

Objectif de cette mission : corriger la MESURE. On n'optimise rien tant que les stats
ne sont pas honnêtes. Travailler dans l'ordre ci-dessous, un commit par étape,
py_compile + un petit test après chaque étape.

---

## Étape 1 — Déduplication par position (nouveau module `clusters.py`)

Règle : tant qu'une position virtuelle (asset + direction) est OPEN dans le journal,
tout nouveau signal IA identique (même asset, même direction, entrée à moins de
0.35 x ATR15m de l'entrée du signal ouvert, OU émis moins de 4h après) est marqué
`"duplicate_of": <id du signal parent>` au moment du log, et exclu de toutes les stats.

Implémentation :
- Dans `journal.log_signal()` : avant d'appender, chercher un signal OPEN trader=AI
  même asset+direction satisfaisant le critère ci-dessus. Si trouvé, logger quand même
  (traçabilité) mais avec `duplicate_of` renseigné et `status: "DUPLICATE"`.
- Créer `clusters.py` avec `effective_trades(journal_dict)` qui retourne les trades
  clôturés décisifs SANS les duplicates, et qui regroupe rétroactivement les anciens
  signaux du journal avec la même règle (passe de nettoyage rétroactive : marquer les
  duplicates existants dans journal.json via un script one-shot `migrate_dedup.py`,
  avec backup de journal.json avant écriture).
- Remplacer la source de données de `prime_strategy._stats_for`, `edge_lab.load_closed`,
  `adaptive_edge.load_trades`, `position_policy._closed_ai` par `clusters.effective_trades`.

Critère d'acceptation : après migration, `python3 prime_strategy.py` affiche un n IA et
un n OTE nettement réduits (attendu : OTE passe de 9 à ~2-3). Imprimer avant/après.

## Étape 2 — Coûts de transaction (nouveau module `costs.py`)

Constantes par actif, en points, configurables en tête de module :

```python
COSTS = {
  "GOLD":  {"spread_session": 0.50, "spread_off": 1.20, "slippage_stop": 0.30, "swap_pct_per_night": 0.012},
  "US500": {"spread_session": 1.50, "spread_off": 4.00, "slippage_stop": 1.00, "swap_pct_per_night": 0.010},
}
```

(valeurs de départ prudentes côté CFD retail, à ajuster sur les fills réels Revolut
de Sam plus tard — prévoir une fonction `calibrate_from_user_trades()` en stub.)

Application :
- `journal.evaluate_open()` : sortie TP → exit_price = tp1 - sign*spread ;
  sortie SL → exit_price = stop - sign*slippage_stop (le sign tel que ça DÉGRADE
  toujours le pnl). Spread off-hours si session du signal est CLOSED/WEEKEND/OVERNIGHT.
- pnl_pct final : retrancher swap_pct_per_night x nombre de nuits tenues.
- `adaptive_edge._account_return_pct` et `simulate()` : appliquer les mêmes coûts.
- Marquer chaque trade clôturé avec `"costs_applied": true` pour distinguer
  l'ancien historique du nouveau. Les stats affichent les deux populations séparément
  tant que l'historique n'est pas re-simulé.

## Étape 3 — Fills intrabar via bougies 1m

Dans le cycle du watcher (prime_watcher.py et track.py) :
- Pour chaque signal OPEN, fetch les bougies 1m de l'actif depuis le dernier check
  (tv_candles.TVCandleClient, timeframe 1m, n_bars suffisant pour couvrir l'intervalle).
- Mettre à jour hi_since/lo_since avec les high/low des bougies 1m, pas seulement lp.
- Ordre de touche dans une même bougie 1m : si TP et SL touchés dans la même bougie,
  hypothèse conservatrice SL d'abord (déjà la convention du code, la conserver).
- Si l'historique 1m ne couvre pas tout l'intervalle (week-end, trou), logger un
  warning dans le signal (`"fill_quality": "PARTIAL"`).

## Étape 4 — WIN_TIME hors de la catégorie WIN

- Partout où on calcule un WR (journal._recompute_stats, prime_strategy._stats_for,
  edge_lab.stats, position_policy._stats) : le WR principal = WIN / (WIN+LOSS) décisifs
  par touche TP/SL uniquement. WIN_TIME/LOSS_TIME comptés dans l'espérance (pnl réel)
  mais affichés à part : `WR_tp_sl` et `time_exits: {n, exp}`.

## Étape 5 — Incertitude affichée (modifier `prime_summary.py` et `prime_strategy._print`)

- Intervalle de Wilson 95% sur chaque WR affiché. Format : `WR 79% [IC95 59-91] n=24`.
- Bootstrap par blocs JOURNALIERS (regrouper les trades effectifs par date Paris,
  rééchantillonner les jours, 2000 itérations) pour l'IC de l'espérance.
- Règle d'affichage : si n effectif < 15, préfixer la stat de `ÉCHANTILLON INSUFFISANT`.
- `should_replace_user_strategy()` : passer MIN_OTE_SAMPLE de 6 à 15 trades EFFECTIFS
  (post-dédup) et exiger que la borne BASSE de l'IC Wilson de l'IA dépasse le WR user.

## Étape 6 — Durcir adaptive_edge

- Réduire l'espace de candidats : supprimer les fenêtres horaires glissantes
  (72 x 3 largeurs). Garder uniquement : asset, direction, asset+direction, strategy,
  sessions NOMMÉES (celles de current_session), score_band. Soit ~25 candidats max.
- MIN_ACTIVE_N: 8 → 15 (trades effectifs), MIN_TEST_N: 3 → 6.
- Remplacer le split unique 60/40 par un walk-forward à 3 fenêtres roulantes :
  un candidat n'est éligible que si l'espérance test est positive sur au moins
  2 fenêtres sur 3.
- Correction de comparaisons multiples simple : MIN_IMPROVEMENT_PCT exigé =
  3.0 x sqrt(nombre de candidats testés / 25), planché à 3.0.

## Étape 7 — Garde-fous d'exécution

- `scanner.quality_setup()` : stop minimum = max(stop SMC, 0.6 x ATR15m de l'actif).
  Si le stop SMC est plus serré que le plancher, élargir le stop ET recalculer le RR ;
  si RR retombe sous 2, rejeter le setup. (Le A_SETUP du 9 juin avait un stop de
  8 points sur US500, c'est dans le bruit du spread.)
- `prime_strategy._major_veto()` : veto si session courante (adaptive_edge.current_session)
  est CLOSED/WEEKEND/OVERNIGHT pour l'actif.
- `position_policy` : remplacer l'affichage `size<=100% de marge` par un sizing
  quart-de-Kelly : f = 0.25 x (WR_effectif - (1-WR_effectif)/RR), borné à [0, cap 4%/SL_x20].
  Si n effectif < 15, forcer le sizing minimum (1% de risque compte).

## Étape 8 — Re-simulation et rapport

- Script `resim_report.py` : recalcule tout le journal IA avec dédup + coûts +
  WIN_TIME séparé, et imprime un tableau avant/après :
  n brut vs n effectif, WR brut vs WR net de coûts avec IC, espérance, equity x20
  simulée baseline vs corrigée.
- C'est CE rapport qui dira si le protocole Prime garde un edge. Aucune conclusion
  de "remplacement de stratégie" avant un mois de forward-test avec cette mesure.

---

## Contraintes

- Ne jamais passer d'ordre. Le système reste signal-only.
- Backup de journal.json avant toute migration (copie horodatée).
- Un commit par étape, message clair. py_compile sur chaque fichier touché.
- Ne pas toucher aux trades USER importés (HISTORIQUE_IMPORT) : ce sont des fills
  réels, ils servent de référence de calibration des coûts.
- Conserver la convention existante "SL d'abord si TP et SL touchés ensemble".
