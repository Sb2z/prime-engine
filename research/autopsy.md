# AUTOPSIE, prévu vs réalisé, jour par jour (append-only)

## 2026-06-10 (premier run, manuel)

- **Trend-day GOLD SHORT armé 01:20** (ADX 43.3, ER 0.455, prix 4233) :
  à 08h le régime était dégradé en TENDANCE HACHÉE (ER 0.40→0.25), aucun
  follow-through propre. Verdict : armement overnight sur liquidité fine,
  non confirmé en session. Question ouverte → backlog : "les armements
  overnight (22h-08h) sous-performent-ils ceux de session ?" (besoin de
  plus d'armements pour tester, compter d'abord).
- **Prime** : aucun A_SETUP depuis le 09/06 23:25 (veto session OVERNIGHT
  a tué les setups nocturnes US500, comportement voulu post-V1).
- **PAPER** : aucune stratégie active (les tests synthétiques du juge ont
  été retirés).
- **Contexte macro** : jour CPI (14:30 Paris). Veto PRÉ-EVENT attendu à
  14:00, première validation live de la chaîne calendrier (A3/V2).

## 2026-06-12 (run n°2, nocturne, 1re session qui DÉMARRE réellement)

- **Infrastructure** : les sessions des 10/06 23:30 et 11/06 23:30 n'ont PAS
  tourné (FileNotFoundError sur claude.exe, PATH des tâches planifiées sans
  npm). Corrigé dans les commits du 12/06 (chemins absolus, candidats
  multiples). Cette session est la PREMIÈRE à démarrer (06:57:41, exe résolu
  via %USERPROFILE%\.local\bin\claude.exe).
- **BLOCAGE DÉCOUVERT (le suivant dans la chaîne)** : la session tourne en
  headless `claude -p ... --permission-mode acceptEdits` (stdin fermé).
  acceptEdits auto-approuve les écritures de fichiers mais AUCUNE commande
  Bash (allowlist = `crontab -l`). Donc python est refusé → harness.evaluate,
  resim_report.py, feature_store.py, notify.send ET git commit sont tous
  injouables cette nuit. Conséquence : 0 hypothèse réellement TESTÉE (le juge
  n'a pas pu trancher) ; les 3 hypothèses du jour sont CODÉES et prêtes
  (exp_2026_06_12.py) mais en attente d'une approbation humaine. Registry
  volontairement intact : pas de verdict sans le juge.
- **Trading** : journal.json inchangé depuis le 09/06 21:43 UTC, aucun trade
  réel, aucun signal Prime, aucune stratégie PAPER (none active) sur la
  fenêtre 10→12/06. Rien à autopsier côté exécution.
- **Prime / trend-day** : aucun A_SETUP ni armement trend-day enregistré
  (cohérent : veto OVERNIGHT + absence d'activité watcher sur la fenêtre).
- **Contexte macro** : CPI US du 10/06 SOFT (Core CPI m/m 0.2 vs 0.3 attendu,
  surprise −0.1 ; CPI y/y 4.2 conforme). ECB Main Refinancing Rate du 11/06
  12:15 conforme (2.4, surprise 0). Aucune surprise exploitable en dérive
  post-event, le silence macro est lui-même l'information : pas de fenêtre
  événementielle à miner cette semaine.

## 2026-06-12 (run n°3, nocturne, CORRECTION du run n°2)

- **Rectification** : le run n°2 avait conclu « 0 hypothèse testée » (blocage
  permissions au moment de l'écriture du rapport). En réalité le blocage a été
  levé et le juge a tourné à 05:05 UTC : HA/HB/HC ont été JUGÉES et TUÉES
  (commit 9b11095, verdicts au registry). La nuit était donc 3 testées /
  3 tuées, pas stérile. Leçon : écrire le rapport APRÈS le juge.
- **Autopsie des 3 verdicts** :
  - HA (momentum conditionné régime ER>=0.45 ET ADX>=30) : exp +0.0017% ~ 0,
    t 0.019, IC à cheval sur 0. Le filtre de régime ne crée AUCUN edge sur
    l'or, il réduit n (71) sans déplacer l'espérance. Réponse négative.
  - HB (dérive overnight LONG, 23h-08h) : exp -0.114%, t -6.71, 0/3 fenêtres
    positives. L'anomalie overnight des métaux NE se reproduit PAS sur GC=F
    net de coûts. SIGN-FLIP INTERDIT noté : le short n'est PAS une conclusion
    gratuite, ce serait une hypothèse nouvelle déclarée.
  - HC (cassure nuage Ichimoku, speed standard, périmètre fermé) : exp
    -0.047%, t -0.673, 1/3 fenêtres+. Première épreuve d'Ichimoku : aucun edge
    de continuation de tendance sur la cassure de kumo.
- **Ingestion ré-exécutée** (python OK ce run) : resim USER WR 57.7% n=78
  exp -0.001% ; fenêtre récente n=8 décisifs (insuffisant, exp +0.361% IC
  (0.005,0.64) à confirmer en forward-test). feature_store gate 72/500,
  apprentissage gelé. journal inchangé depuis 09/06 21:43 UTC.
- **Macro** : CPI US 10/06 soft, ECB 11/06 conforme, aucune surprise
  exploitable, pas de dérive post-event à miner.

## 2026-06-13 (run n°4, nocturne)

- **Exécution** : RIEN à autopsier. journal.json inchangé (dernier trade USER
  daté 08/06 13:00, 0 trade neuf, 0 signal Prime, 0 PAPER actif sur 12→13/06).
  feature_store : 1916 features mais toujours **72 outcomes complets** → gate
  apprentissage **72/500**, gelé (l'export grossit mais les outcomes ne se
  bouclent pas, faute d'activité signalétique). resim USER inchangé : WR 57.7 %
  n=78 exp −0.001 % ; fenêtre récente n=8 décisifs (toujours insuffisant).
- **Macro 11→13/06** : un seul point notable, **US PPI m/m +1.1 vs +0.7
  attendu** (surprise +0.4, inflation chaude) le 11/06 12:30 UTC ; Core PPI au
  contraire un peu soft (0.4 vs 0.5). UoM Sentiment 12/06 au-dessus (48.9 vs
  46.1). Signal d'inflation MIXTE, pas de surprise propre exploitable en dérive
  post-event sans famille event-study dédiée → pas miné.
- **Autopsie des 3 verdicts de cette nuit** (tous KILLED) :
  - **HD (cot_extreme GOLD, contrarian, daily)** : 1er câblage réussi du
    ctx_fn cot_pctile (lag pub +4j, pctile 156 sem, anti-lookahead par bisect
    strict). Résultat : exp **−0.462 %**, t −1.146, n_eff **29** (< 30),
    fenêtre 3 SANS extrême (0 trade). Sur 2024-26 l'or est en marché HAUSSIER
    structurel : se mettre contrarian SHORT contre un positionnement spéculatif
    extrême-long a perdu, et l'échantillon est sous le plancher. Le COT contrarian
    inconditionnel ne tient pas sur l'or, résultat honnête, pas un bug de câblage.
  - **HE (cot_extreme US500/ES, contrarian, daily, 2e test famille z 1.96)** :
    exp **+0.027 % ≈ 0**, t 0.07, n_eff **21** (< 30), IC (−0.75, +0.83) à
    cheval sur 0. Aucun edge, échantillon insuffisant. La thèse COT contrarian
    ne se généralise pas non plus au S&P. Déflation Bonferroni correctement
    appliquée (z 1.645→1.96 car HD compte déjà dans la famille).
  - **HF (ichimoku_tk_cross GOLD, 1h, 1er test famille z 1.645)** : la plus
    "vivante" des trois, n_eff **161**, **2/3 fenêtres positives**, exp
    +0.066 %, mais **IC bas −0.094 < 0** et **t 0.78 ≪ 1.645**. Le croisement
    TK confirmé par le nuage n'est pas significatif net de coûts. 2e mécanisme
    Ichimoku réfuté après la cassure de nuage (HC) : ni cassure ni croisement
    canonique ne produisent d'edge mesurable sur l'or horaire.

## 2026-06-14 (run n°5, nocturne)

- **Exécution** : RIEN à autopsier côté trading. journal.json inchangé (dernier
  trade USER 08/06 13:00, 0 trade neuf, 0 signal Prime, 0 PAPER actif). resim
  USER inchangé (WR 57.7 % n=78 exp −0.001 % ; fenêtre récente n=8 décisifs,
  insuffisant). feature_store : **2430 features** (vs 1916) mais toujours **72
  outcomes** → gate **72/500 figé** (l'export grossit, les outcomes ne se
  bouclent pas). Macro 13→14/06 : rien de neuf depuis le PPI chaud du 11/06
  (signal d'inflation mixte déjà digéré), aucune surprise propre exploitable.
- **DEUX CORRECTIONS DE FOND découvertes ce run (autopsie méthodo) :**
  1. **HA était en 1h, PAS en daily.** Les rapports 12/06 et 13/06 et l'entrée
     autopsie du 12/06 décrivent HA comme un test « daily ». FAUX : `exp_2026_
     06_12.py` le définit `timeframe:"1h"`. Les **statistiques** de HA
     (+0.0017 %, t 0.019, n=71) étaient correctes, seul le **label de
     timeframe** était erroné, propagé sur 3 runs faute de relire la source.
     Conséquence directe ci-dessous (HH).
  2. **HH est un DOUBLON économique exact de HA.** Conçu ce soir sur la prémisse
     (fausse) « HA testait le daily, HH teste le TF natif 1h », HH a reproduit
     HA **trade pour trade** (n=71, exp +0.0017 %, t 0.019, mêmes 3 fenêtres).
     Il a échappé au garde anti-doublon du harness UNIQUEMENT parce que j'ai
     omis `er_n:39, adx_n:14` (égaux à leurs défauts) : `hypothesis_key` hashe
     le **dict params brut**, pas les params canoniques du signal → deux clés
     différentes pour une stratégie identique. **Faille du garde**, pas un edge.
     Le verdict (KILLED) reste juste ; l'entrée registry est redondante. Je ne
     touche PAS au registry du juge (append-only, séparation des pouvoirs) :
     signalé à Sam pour décision (purge éventuelle + canonicalisation du hash).
- **Autopsie des 3 verdicts de cette nuit (tous KILLED) :**
  - **HG (ichimoku_kijun_reject GOLD 1h, 1er test famille z 1.645)** : la
    réfutation la plus FORTE du lab à ce jour. n_eff **395**, exp **−0.282 %**,
    t **−5.97**, **0/3 fenêtres positives**, IC95 (−0.385, −0.167) entièrement
    < 0. Le pullback-rejet sur Kijun (acheter le repli en tendance) PERD
    robustement net de coûts : la bougie de rejet a déjà capturé le rebond, on
    entre en haut de la mèche, et le coût 1h fait le reste. **3e mécanisme
    Ichimoku réfuté** (après kumo_break HC et tk_cross HF), et le seul à edge
    nettement négatif, pas seulement nul.
  - **HH (momentum_regime GOLD 1h)** : doublon de HA (cf. ci-dessus). exp
    +0.0017 % ≈ 0, t 0.019, n=71. N'apporte aucune information nouvelle ; ne
    compte pas comme hypothèse distincte.
  - **HI (momentum_regime US500 1h, variant_of=HA, z 2.128)** : 1er test
    *réellement nouveau* de la famille sur l'indice. exp **−0.042 %**, t
    **−0.449**, n_eff **46**, 1/3 fenêtres positives, IC (−0.230, +0.130). Le
    filtre de régime ne crée pas davantage d'edge sur le S&P en 1h que sur l'or.
    KILLED au z déflaté 2.128 (durci par l'entrée HH), mais KILLED aussi à
    1.96 : t 0.449 ≪ les deux seuils, verdict insensible à la faille.
- **Bilan honnête** : 3 testées / 3 tuées, mais **2 réellement nouvelles**
  (HG, HI) + 1 doublon involontaire (HH). La vraie valeur du run est ailleurs :
  une erreur factuelle vieille de 3 rapports corrigée, et une faille du garde
  anti-doublon du juge mise au jour. Mortalité 100 % = santé.

## 2026-06-15 (run n°6, nocturne)

- **Exécution** : RIEN à autopsier côté trading. journal.json INCHANGÉ (dernier
  trade USER 08/06 13:00, 0 trade neuf, 0 signal Prime, 0 PAPER actif). resim
  USER inchangé (WR 57.7 % n=78 exp −0.001 % ; fenêtre récente n=8 décisifs,
  insuffisant, forward-test en cours).
- **CHANGEMENT D'INGESTION MAJEUR : feature_store 72 → 489 outcomes complets.**
  Figé à 72/500 sur 4 runs (12→14/06), le gate apprentissage saute à **489/500**
  (2942 features, grades NO_TRADE 2643 / A_SETUP 244 / WATCH 55). Les outcomes
  se bouclent enfin ; `apprentissage_autorise` reste **false** mais à ~11
  outcomes du seuil, il devrait franchir 500 d'ici 1-2 runs. C'est le fait
  saillant de la nuit côté infra : une source de mining (les issues des
  A_SETUP/WATCH de Prime) s'ouvre bientôt. Je n'ai PAS pu la miner ce soir
  (gate fermé + ce n'est pas un signal strategy_families testable par le juge).
- **Mining trades réels TENTÉ, négatif** : les métadonnées par trade sont
  dégénérées (session="REAL" sur les 66 trades GOLD, score=None, ADX<30
  uniforme, RSI mid uniforme) → aucun régime exploitable à extraire. Sam trade
  GOLD à 66/78 (SHORT 43 / LONG 23, WR ~60 % chaque sens, exp +0.015/+0.019 %, quasi nul net). Confirme backlog #5 : attendre n≈150 ET des métadonnées
  réellement renseignées. Ce constat a motivé le CHOIX D'ACTIF de HK (l'or).
- **Macro 12→15/06** : aucune surprise RÉALISÉE à miner (actuals nuls sur la
  fenêtre). Gros bloc banques centrales À VENIR (BoJ/RBA 16/06, **FOMC 17/06**) ;
  rien d'exploitable en dérive post-event tant que les surprises ne sont pas
  publiées → non miné (cohérent avec les runs précédents).
- **Autopsie des 2 verdicts de cette nuit (tous deux KILLED, réellement nouveaux) :**
  - **HJ (ichimoku_chikou_confirm GOLD 1h, 1er test famille z 1.645)** : n_eff
    **614**, exp **−0.106 %**, t **−2.567**, **0/3 fenêtres positives**, IC95
    (−0.199, −0.005) entièrement < 0. La triple confluence Ichimoku, le setup
    "haute conviction" canonique (Chikou dégagée + prix vs nuage + Tenkan>Kijun), n'est pas seulement non significative : elle est **significativement
    perdante** net de coûts. **4e mécanisme Ichimoku réfuté** (après kumo_break
    HC, tk_cross HF, kijun_reject HG) et **2e franchement négatif** (avec HG). Le
    filtre de confluence le plus strict échoue comme les triggers uniques : sur
    l'or 1h, l'alignement des composantes Ichimoku ne crée aucun edge. Périmètre
    Ichimoku **quasi clos** : ne reste que `twist` (changement de couleur du
    nuage), mécanisme distinct, au backlog.
  - **HK (mean_reversion GOLD 1h, variant_of=H2, z 1.96)** : n_eff **556**, exp
    **−0.039 %**, t **−1.502**, **0/3 fenêtres positives**, IC95 (−0.088, +0.014)
    à cheval sur 0 (borne haute à peine positive). Le fade d'un excès ±1 %/6h ne
    survit pas aux coûts sur l'or non plus, robustesse cross-asset NÉGATIVE du
    résultat de H2 (déjà tué sur l'ES). Pas de famine (n=556) : c'est bien
    l'absence d'edge net, pas l'échantillon, qui tue. La réversion intraday
    existe peut-être en brut, mais le spread/slippage 1h la mange entièrement, cohérent avec l'intuition "fader coûte cher".
- **Bilan honnête** : 2 testées / 2 tuées, **2 réellement nouvelles** (pas de
  doublon ce soir). Nuit volontairement RESSERRÉE à 2 hypothèses : le périmètre
  des familles existantes est largement épuisé (momentum, mean_reversion,
  session, 4 mécanismes Ichimoku réfutés, COT en famine), et forcer un 3e test
  aurait été cosmétique. La vraie info neuve de la nuit est l'ingestion (gate
  489/500 imminent). Mortalité 100 % = santé.

## 2026-06-16 13h, autopsie midday (PRIME ANALYST)
- **Matinée 09h->13h : 0 trade, 9 cycles NO_TRADE.** GOLD forecast LONG fort
  (tf_15m 0.84->0.92) MAIS regime TENDANCE HACHEE -> abstention CORRECTE : le
  momentum directionnel sans regime tendanciel propre = faux ami (= edge nul
  mesure par HA/HH net de couts). US500 RANGE -> NO_TRADE.
- **A_SETUP 13:02 GOLD LONG conf 7.2** : entry 4333.78 (~0.28% sous le prix),
  stop 4315.8, valide 45m. **Garde-fou MAX_ENTRY_ATR=1.5 OK** : entree ramenee a
  ~1.5xATR15m -> joignable en intraday (vs ~1.3% mediane avant correctif). 1er
  A_SETUP observable post-garde-fou ; suivre son outcome (rempli ? TP1 ?) a 17h.
- **Entry-mode (feature store) : NON concluant.** A_SETUP GOLD clusterises sur
  2 jours seulement (US500 4j) -> pseudo-replication, t-stats = artefacts
  (US500 ret_4h t=-26 = 1 seance de baisse, fenetres recouvrantes). Derive 4h
  GOLD du bon cote (+0.06% gross) mais NULLE net. Re-evaluer quand n_jours >>.
- **0 hyp soumise** : momentum_regime 1h epuise sur GOLD/US500 (regime plus
  strict -> famine 0.55/32~22, 0.60/35~11 ; exit-only -> DUPLICATE car exit_rule
  hors hypothesis_key ; ZN famine ; DX inaccessible ; pas de 15m au lake).
  Pas de test cosmetique sur le compteur de deflation GLOBAL. SPEC momentum_breakout livree a Sam.

## 2026-06-16 17h (PRIME ANALYST, slot evening), outcomes intraday + test priorite (a)

- **Sante VERTE** : watcher cycle 17:00 (frais <12m), datafeed tradingview pur,
  gate apprentissage 840/500 (progresse depuis 754 a 13h), 0 outcome MIXED
  exclu (ret_4h corrige tient), lab 18/17/0/0 -> 19/18/0/0 apres ce run.
- **Outcome des 3 signaux LONG du jour = AUCUN rempli (et c'est une BONNE chose).**
  - GOLD A_SETUP 13:03 entry 4333.78 (repli ~0.28% sous marche 4347), valide
    45 min : prix retrace seulement jusqu'a **4338.8** (~13:50) -> jamais
    atteint 4333.78 dans la fenetre. NON REMPLI. Le marche a ensuite glisse a
    4323 (17:00). Un LONG rempli serait sous l'eau (-0.24%), stop 4315.8 non
    touche (min jour 4317.68).
  - US500 LONG 13:45 puis re-trigger 14:28, entry 7548.76 (repli) : prix
    descendu seulement a **7552.9** (15:07) dans les fenetres de validite ->
    NON REMPLI ; le marche a ensuite glisse a 7539.8 (sous l'entry).
  - **Lecon** : forecast LONG persistant en regime RANGE/TRANSITION/HACHEE, mais
    le REALISE a ete baissier/plat. Les entrees-REPLI non remplies ont EVITE
    trois longs perdants. Sur CE regime, l'entree-repli >= l'entree-marche
    (qui aurait pris des longs a contre-tendance). n=1 jour, anecdotique, mais
    pile la question priorite (b) ; confirme la conditionnalite de regime (HH/HI).
- **Test HL (priorite a, TP placement)** : GOLD momentum_regime 1h, k4/thr0.3,
  meme regime trend 0.45/30, exit "laisser courir" TP 2.0%/stop 0.8%/h48 (RR
  2.5), variant_of=HH. -> **KILLED** (n=58, exp_net **+0.1851%**, IC95
  (-0.112, 0.492), t=1.115 < z 2.241, fenetres +0.21/-0.03/+0.31). Mort sur
  SIGNIFICATIVITE, PAS sur le signe : l'exp ponctuelle passe de +0.0017% (HH,
  TP serre 1.0%) a +0.185% (TP large 2.0%) -> **le placement du TP COMPTE,
  l'edge momentum vit bien dans la queue droite** qu'un TP serre tronquait.
  Mais bruit dominant (IC large, t faible). Resultat utile : oriente priorite
  (a) vers TP large, n'autorise PAS de promotion.

## 2026-06-16 23h (PRIME ANALYST, slot evening), bilan séance + validité externe HL

- **Santé VERTE** : watcher cycle 22:59 (frais <12 min), datafeed tradingview
  pur (6 flux GOLD/US500 15m/1h/1m), gate apprentissage 970/500 (progresse
  depuis 840 à 17h, 754 à 13h), 0 outcome MIXED exclu (ret_4h corrigé tient),
  0 erreur dans prime_watcher.log, lab 19/18/0/0 -> 20/19/0/0 après ce run.
- **Bilan séance du bot** : 485 NO_TRADE, 5 A_SETUP, 4 WATCH, **TOUS LONG**,
  sur une séance **baissière/plate** (GOLD 4347->4331 ~-0.37%, US500
  7560->7508 ~-0.69%). Régimes dominants côté GOLD : TRANSITION 86 / RANGE 86 /
  HACHÉE 53 / MOYENNE 22 ; côté US500 : HACHÉE 106 / RANGE 96 / TRANSITION 31 /
  MOYENNE 14. **Le forecast LONG (1h +0.335 GOLD, 4h positifs) a persisté toute
  la journée CONTRE le réalisé baissier.** Au dernier cycle 22:59 le forecast
  US500 a enfin basculé SHORT (15m -0.84 / 1h -0.68 ; 4h encore +0.30). Aucun
  setup n'a été gradé tradable au sens RR/confluence ce soir (NO_TRADE partout).
  Lecon : un filtre de régime trend (ER>=0.45/ADX>=30) aurait EXCLU l'essentiel
  de la journée (HACHÉE/RANGE/TRANSITION) -> il PROTÈGE ; le momentum brut
  long-only en régime non-trend aurait saigné. Renforce la conditionnalité HH/HI.
- **Test HM (priorité a, validité externe de HL)** : US500/ES=F 1h,
  momentum_regime k4/thr0.3, régime trend 0.45/30, exit "laisser courir"
  TP 2.0%/stop 0.8%/h48 (RR 2.5), variant_of=HL. -> **KILLED** (n=39, exp_net
  **-0.1134%**, IC95 (-0.420, 0.209), t=-0.746 < z 2.326, fenêtres
  +0.065/-0.275/-0.293, 1/3 positive). **Le résultat HL ne se généralise PAS.**
  L'estimation ponctuelle GOLD (+0.185%) était du **bruit de queue spécifique à
  l'or**, pas un levier de placement-TP généralisable : sur un 2e actif
  indépendant la même config exit-large est NÉGATIVE. Conclusion convergente
  HH(+0.0017)/HL(+0.185 non signif)/HM(-0.113) : **le SIGNAL momentum_regime est
  le facteur limitant, pas l'exit.** Réoriente fermement la priorité (a/b) vers
  la famille **momentum_breakout** (entrée-marché en régime tendanciel, SPEC
  déjà livrée à Sam) plutôt que vers l'optimisation du TP sur un signal faible.
- **Reco promotion** : 0 stratégie en PAPER -> section muette (vérifiée).

## 2026-06-16 nocturne (CHERCHEUR, slot 23h30), clôture Ichimoku + edge signaux Prime

- **Ingestion** : pas de research/PAUSE. Lake frais (GC=F/ES=F 1h = 13733/13695
  barres, dernière bougie 2026-06-16T04:00Z). **GATE APPRENTISSAGE FRANCHI** :
  feature_store 975/500, `apprentissage_autorise=true` (était 489 le 15/06, 72
  figé avant, le saut du 15/06 est CONFIRMÉ, pas un artefact). resim USER
  inchangé (WR 57.7% n=78, exp -0.001% ; fenêtre récente 8 décisifs < 15,
  insuffisant). journal.json figé (rien de neuf à autopsier côté exécution).
- **Edge des signaux Prime eux-mêmes (backlog #1, source ouverte ce soir)** : mesure OBSERVATIONNELLE (hors harness, pas un verdict), join features+outcomes
  ret signé par direction, IC bootstrap-jours :
  - **A_SETUP** (n=135, **100% LONG**) : ret_1h +0.012% (IC -0.024,+0.013),
    **ret_4h -0.021% IC95 (-0.223, -0.014) borne haute < 0 → NÉGATIF** sur la
    fenêtre, WR 41.5%.
  - **WATCH** (n=42, **100% LONG**) : ret_4h +0.496% WR 90.5% mais
    **IC95 (-0.097, 0.846) à cheval sur 0** (n petit, peu de jours).
  - **Caveat capital** : direction 100% LONG = dégénérée sur une fenêtre
    baissière/plate (cf. analyste 23h). Ceci mesure « Prime long, marché baissier
    sur CETTE fenêtre », PAS un edge structurel régime-général. Le ret_4h négatif
    des A_SETUP reflète le biais long persistant contre le réalisé baissier
    (même histoire que le forecast qui n'a basculé qu'à 22:59), pas une preuve
    d'anti-edge. À re-mesurer quand la direction se diversifiera et n_jours croît.
- **2 tests harness, clôture du périmètre Ichimoku** (backlog #2 du 15/06).
  Raison spécifique vérifiée AVANT de tester : `twist` est le SEUL mécanisme de
  DÉBUT de tendance (vs les 4 entrées de continuation déjà mortes) → hypothèse
  distincte, pas cosmétique. Exit = convention continuation identique HF/HG/HJ
  (stop 0.8/tp 1.5/h48), aucun nouveau degré de liberté.
  - **HN gold_ichimoku_twist** → **KILLED** : n=175, exp **-0.0748%**,
    IC95 (-0.222, +0.088), t -0.974 < z 1.645, fenêtres -0.085/-0.124/-0.028
    (**0/3 positive**).
  - **HO us500_ichimoku_twist** (variant_of=HN) → **KILLED** : n=143, exp
    **-0.0772%**, IC95 (-0.229, +0.079), t -1.002 < z 1.96, fenêtres
    +0.006/-0.089/-0.139 (**1/3 positive**).
  - **Lecture** : convergence cross-asset frappante (-0.075% / -0.077%, ~le coût
    de trading), aucun edge net. **5e ET DERNIER mécanisme Ichimoku réfuté →
    PÉRIMÈTRE ICHIMOKU CLOS** (kumo_break, tk_cross, kijun_reject,
    chikou_confirm, twist : 5/5 morts sur GOLD 1h ; twist confirmé mort aussi
    sur US500). Ni continuation, ni amorce : Ichimoku ne produit pas d'edge net
    de coûts sur cet actif/TF. SIGN-FLIP INTERDIT (un -0.075% ne fait pas un
    edge inverse).
- **Lab après run : 22 testées / 21 tuées / 0 papier / 0 promues** (mortalité
  ~95% = santé). Compteur GLOBAL respecté : 2 tests, 0 cosmétique, 3e slot non
  consommé (famille épuisée, forcer aurait dilué).

## 2026-06-17 13h (PRIME ANALYST midday)
- **Contexte : JOUR FOMC** : décision Fed 18:00 UTC (20:00 Paris) + dot plot +
  press conf 18:30 ; US Retail Sales 14:30 Paris. Pré-FOMC = attentisme.
- **Matinée→midi (09:02→12:59, 43 cycles) : 43 NO_TRADE sur les DEUX actifs.**
  GOLD TRANSITION(36)/RANGE(6), px 4330→4331 (**+0.02%, PLAT**), forecast
  LONG(28)/SHORT(11). US500 RANGE(20)/TRANSITION(12)/HACHÉE(11), px 7535→7518
  (**-0.23%**), forecast SHORT(21)/NEUTRAL(15). AUCUNE tendance propre.
- **Lecture momentum** : chop pré-FOMC, rien à capter. Le bot reste correctement
  à l'écart, cohérent avec la thèse (le momentum exige de la tendance, absente).
- **HQ (test du jour), momentum_regime à HORIZON SWING 1d** : KILLED sur
  n_eff=12<30, MAIS point estimate fortement positif (+1.55% net, t 3.70 > z
  2.45, IC95 (0.66,2.32)>0, fenêtres 0/+0.86/+1.90). **1er momentum_regime à
  passer 3/4 checks.** Contraste net avec l'intraday 1h (plat à tout knob). À
  tempérer : 37L/2S sur bull séculaire du gold → l'estimation peut ÊTRE le bull,
  pas un edge généralisable ; n_eff=12 trop fin pour trancher. **La dimension
  horizon n'est PAS close comme l'intraday** : backlog (plus d'épisodes/actifs).
- **Lab après run : 24 testées / 23 tuées / 0 papier / 0 promues** (~96%).

## 2026-06-17 17h (PRIME ANALYST evening)
- **Contexte : JOUR FOMC** : décision Fed 20:00 Paris (dans ~3h) ; séance ENTIÈRE
  pré-FOMC, attentisme.
- **Séance 13:05→17:04 (43 cycles) : 43 NO_TRADE sur les DEUX actifs.** GOLD RANGE
  (43/43), px 4328→4347 (**+0.44%**, dérive haussière modeste), forecast LONG(32)/
  NEUTRAL(11). US500 **TENDANCE HACHÉE (43/43)**, px 7518→7502 (**−0.21%**), forecast
  **SHORT(40)/NEUTRAL(3)** : biais baissier net mais HACHÉ, jamais gradé. Aucune
  tendance PROPRE de la séance.
- **Lecture momentum** : chop pré-FOMC, rien à capter. Bot correctement à l'écart, cohérent avec la thèse. Bilan du jour : ~180 NO_TRADE cumulés sur 4 slots, 0 trade USER.
- **HR (test du jour), momentum_regime SWING 1d sur ES=F** (backlog #1 du 13h,
  variant_of=HQ, config + exit IDENTIQUES, seul l'actif change GOLD→ES) : **KILLED,
  exp −0.4025%** (NÉGATIF), n_eff=8, t −0.695 ≪ z 2.498, IC95 (−1.30,0.92), fenêtres
  1/3 (0/4 checks). **TRANCHE le confound de HQ** : même config, +1.55% sur GOLD vs
  −0.40% sur ES → l'edge NE voyage PAS cross-asset → le +1.55% de HQ était très
  probablement le **bull séculaire du gold**, pas un edge momentum généralisable.
  n_eff=8 trop fin pour PROUVER un anti-edge ES, mais le CONTRASTE de signe (config
  identique) retire à HQ son caractère généralisable. **Dimension horizon REFERMÉE.**
- **Cause structurelle** : gate ER45/ADX30 sur 1d → trop peu d'épisodes indépendants
  (GOLD n_eff=12, ES n_eff=8) ; un seul actif n'atteint jamais n_eff≥30 sur 5 ans.
- **Edge Prime report-only** : INCHANGÉ vs 09h (6 jours, 135 A_SETUP/42 WATCH, 100%
  LONG dégénéré), aucune conclusion nouvelle, reconduit. Script 17h corrige le chemin
  feature_exports (le 09h pointait à tort vers research/).
- **Familles existantes épuisées pour momentum_regime** : intraday 1h plat (HH→HP),
  swing 1d non généralisable (HQ/HR), Ichimoku clos. Reste = nouvelles familles (token
  Sam) : momentum_breakout (#1), momentum_regime_session (#2), swing 1d multi-actifs.
- **Lab après run : 25 testées / 24 tuées / 0 papier / 0 promues** (~96%).

## 2026-06-17 23h (PRIME ANALYST evening, post-FOMC)
- **Contexte : POST-FOMC** : décision Fed tombée à 20:00 Paris. Bascule RISK-OFF
  nette : VIX +12.2%, DXY +0.85%, 10Y +1.04%. Forecast SHORT sur les DEUX actifs
  (GOLD repasse SHORT après LONG l'aprem ; US500 SHORT conf 10/10 aligné 6/6).
  Régime TENDANCE HACHÉE 🔴 sur les deux. px US500 ~7502→7436 (−0.9%).
- **Séance 17:04→22:56 (~2000 cycles) : tous NO_TRADE.** Vetoes = session OVERNIGHT
  (spreads élargis) + RR<2.0. Setups OTE_RETRACEMENT SHORT à RR 1.0-1.6 (entry_capped),
  jamais gradés. Bilan jour : ~230 NO_TRADE cumulés / 4 slots, 0 trade USER.
- **Lecture momentum** : la bascule post-FOMC est le type de mouvement directionnel
  que la thèse voudrait capter, MAIS (a) survient en OVERNIGHT (vetoée), (b) régime
  classé HACHÉ pas tendance propre, (c) repricing en gap sur news ≠ tendance
  persistante intraday. Bot correctement à l'écart.
- **HS/HT (tests du soir), 1er test de la famille `momentum_breakout`** (approuvée
  par token Sam, commit 51a0e61 ; backlog #1 des 4 slots ; spec 13/06). Entrée-marché
  sur cassure Donchian20 + gate ER0.45/ADX30 + exit stop0.6/tp1.0/24h (canonique HH).
  DEUX actifs testés d'emblée (pré-emption du confound cross-asset HQ→HR), config
  identique, seul l'actif change :
  - **HS GOLD 1h : KILLED, exp +0.0097% (≈0)**, n_eff=54 (≥30 ✅), t=0.098≪z1.645,
    IC95 (−0.168,0.177), fenêtres 2/3 mais d'ampleur triviale → 2/4 checks. PLAT.
  - **HT US500 1h : KILLED, exp −0.0891% (NÉGATIF)**, n_eff=44 (≥30 ✅), t=−0.978≪z1.96,
    IC95 (−0.256,0.083), fenêtres 1/3 → 1/4. NÉGATIF.
- **Résultat le plus PROPRE de l'arc** : PAS un problème de puissance (n_eff 54/44 ≥30,
  vs HQ/HR 12/8). Le juge a de quoi conclure et conclut plat/négatif. **Le MODE
  D'ENTRÉE n'est pas l'ingrédient manquant** : remplacer le repli (OTE) par la cassure
  dans le sens du momentum, gate identique, ne dégage aucun edge net de coûts.
  Persistance (momentum_regime) ET cassure (momentum_breakout) convergent : momentum
  intraday 1h GOLD/ES = flat net de coûts, quel que soit l'entrée. Les coûts mangent
  le signal brut.
- **Dimension « mode d'entrée » REFERMÉE** (avec puissance). Reste à éprouver : la
  SESSION (momentum_regime_session, backlog #1, token Sam) ; confluence news+régime.
- **Edge Prime report-only** : INCHANGÉ (6 jours, 135 A_SETUP/42 WATCH, 100% LONG).
  Les SHORT post-FOMC (ret_4h non bouclé) seront le 1er vrai lot SHORT demain → slot 09h.
- **Lab après run : 27 testées / 26 tuées / 0 papier / 0 promues** (~96%).

## 2026-06-17 23h30 (CHERCHEUR NOCTURNE, attaque la PUISSANCE du 1d par pool GOLD+ES)
- **Fait neuf méthodo** : l'analyste avait refermé l'horizon 1d sur un MANQUE DE
  PUISSANCE (HQ n=12, HR n=8) en croyant l'agrégation multi-actifs « hors lake ».
  FAUX : GC=F+ES=F 1d sont dans le lake et `harness.evaluate` POOLE nativement les
  actifs d'un même `data` dict (même source yfinance → garde anti-basis OK). Levier
  unique de la nuit : pooler GOLD+ES en 1d, triggers/exits TOUS hérités (zéro DOF neuf).
- **HU momentum_regime 1d POOLÉ (variant_of HQ) → KILLED, 2/4 checks** : n_eff=**20**
  (de 12+8, TOUJOURS <30 même poolé !), exp **+0.769%** (effondré depuis +1.55% de HQ),
  IC95 **(0.037, 1.497)** : **borne basse > 0**, fenêtres **2/3 +**, MAIS t=1.93 < z=**2.539**
  (9e test famille) et n<30. Double lecture : (a) la dilution +1.55→+0.77 par
  l'échantillon bear-inclus d'ES **corrobore que HQ était en grande partie le bull du
  gold** ; (b) MAIS un **résidu positif underpowered survit** (IC_bas 0.037>0, 2/3 fen+) :
  le 1d n'est PAS refermé par un verdict d'edge, seulement par la PUISSANCE. C'est le
  **seul endroit de tout l'arc où le momentum montre une borne basse d'IC > 0**.
- **HV momentum_breakout 1d POOLÉ (variant_of HS) → KILLED, underpowered** : n_eff=**14**
  (une fenêtre à 0 trade), exp +0.817%, IC **(−0.15, 1.80)** à cheval sur 0, t=1.69<z2.13.
  Le gate ER/ADX quotidien est encore plus sélectif → le breakout 1d ne se déclenche
  quasi jamais. Mécanisme d'entrée alternatif, même mur de puissance.
- **HW mean_reversion 1d POOLÉ (variant_of H2) → KILLED, BIEN POWERED** : n_eff=**341**,
  exp **−0.1146%** (négatif), IC **(−0.276, 0.035)**, fenêtres **0/3 +** (toutes négatives),
  t=−1.33. Seul test 1d non limité par la puissance → **verdict propre** : la
  surréaction QUOTIDIENNE ne réverse pas net de coûts (cohérent avec la réversion 1h
  morte H2 −0.065 / HK −0.039 ; le 1d est même un peu PLUS négatif). Réversion **close
  à tout horizon** sur GOLD/ES.
- **Synthèse 1d** : les deux mécanismes MOMENTUM (regime, breakout) restent
  **sous-puissants même poolés** (n 20 / 14 < 30), le seul chemin honnête est PLUS
  d'instruments / un historique plus long (PAS un sweep, PAS DXY/VIX/ZN non-tradés).
  Le momentum 1d garde un **résidu positif intrigant** (HU IC_bas>0) qui mérite la
  puissance ; la mean_reversion 1d est, elle, **réfutée nette** (powered, négative).
- **Edge Prime report-only** : INCHANGÉ (6 jours, 135 A_SETUP/42 WATCH, 100% LONG,
  buckets régime ≈1 jour → non interprétables). Lot SHORT post-FOMC pas encore bouclé.
- **Lab après run : 30 testées / 29 tuées / 0 papier / 0 promues** (~97%).

## 2026-06-18 09h (matin), momentum 1d clôturé avec puissance
- **Prod** : 100 cycles 00h→09h = 100 NO_TRADE (GOLD TRANSITION 80%, US500 HACHÉE/
  TRANSITION), forecast sans conviction, 0 trade USER. Abstention CORRECTE en chop, le momentum intraday n'a rien à capter. Dernier setup prod = 16/06 (tous LONG) ;
  rien le 17 ni le 18 (~2 j de grille NO_TRADE, risk-off post-FOMC résiduel).
- **Juge** : HX (GOLD 1d momentum INCONDITIONNEL, k6/thr0.5) KILLED **POWERED**
  n_eff=181, exp **+0.144 %** (n.s., IC [−0.10, +0.40]) ; HY (ES contrôle) KILLED
  −0.083 % (n.s.). Le +1.55 % de HQ s'**effondre** à zéro statistique dès qu'on
  retire le filtre de régime et qu'on obtient n≈180 → le « résidu » 1d était de la
  **sélection-de-filtre + bêta-gold**, pas du momentum. **Thèse momentum close au 1d
  avec puissance** (après 1h, breakout, regime, pool). Rouvrir = donnée (tâche Sam),
  pas knob. Pistes restantes : SESSION (token Sam) et confluences hors-momentum.

## 2026-06-18 13h (midi), bascule downtrend GOLD + session descriptive referme l'angle
- **Prod** : 143 cycles 00h→13h. Matinée 100 % NO_TRADE (chop), puis dès ~11h Paris
  **downtrend GOLD intraday naissant** : 4307→4260 (−1.1 %), régime HACHÉE/MOYENNE,
  forecast **SHORT 22/22 cycles**, orderflow delta ≈ −21 500, prix sous le VAL. Premiers
  **4 WATCH SHORT** du jour (OTE, RR ~1.1-1.3), **aucun A_SETUP** → 0 trade USER.
  US500 RANGE 22/22. Abstention correcte sur tendance immature + RR serré.
- **Cohérence (à suivre)** : WATCH SHORT GOLD affichent des drivers **pro-LONG**
  (taux↓, silver↑) à côté d'une direction SHORT (technique/orderflow priment). Interne
  (WATCH ne pousse pas d'alerte Telegram → Sam ne l'a pas vu). Diff+test à proposer evening.
- **Juge** : **0 hypothèse soumise** : discipline. Les 7 familles exprimables sont
  TOUTES KILLED (28 hyp réelles), momentum clos avec puissance ce matin. Re-sweep =
  durcir Bonferroni à vide. Max 2 ≠ minimum 2.
- **Diagnostic DESCRIPTIF session** (`exp_2026_06_18_13h.py`, hors coûts/IC/WF) : momentum
  1h stratifié par session. GOLD meilleure = **LONDRES** (+0.084 % brut, win 53 %), PAS NY
  (+0.019 %, win **48.6 % < 50 %**) ; ES ~0 partout. La seule cellule positive (LONDRES-GOLD)
  est **gold-spécifique** (ES contredit) + cost-marginale = **bêta-gold**, pas un effet
  session. **L'intuition NY=tendanciel n'est PAS corroborée.** → motivation FAIBLE pour la
  famille `momentum_regime_session` : NE PAS prioriser. Angle session refermé (descriptif).
- **Reco promo** : NON (0 paper réel). **Lab 32/31/0/0.** Piste vivante restante :
  confluences HORS-momentum (mining des ~80 trades USER), cible evening.

## 2026-06-18 23h (soir), 1er A_SETUP du jour : direction juste, entrée OTE NOFILL
- **Prod** : ~70 cycles 17h→23h. Après 38 WATCH SHORT GOLD étalés (RR serrés), **premier
  A_SETUP de la journée** à 21:04→21:21 Paris (4 cycles) : **GOLD SHORT OTE_RETRACEMENT**,
  conf 7.2, entrées 4225.95→4218.62, stop ~4238, TP ~4174, **RR 2.74→3.05**, régime TENDANCE
  MOYENNE 🟡, confluence forte (forecast SHORT aligné 15m/1h/4h, orderflow delta ≈ −13 000,
  prix sous VAL). **4 pushes Telegram `ok:true`.**
- **Réalisé** : GOLD a continué de chuter (low 4203.89, prix ~4209). Pour le SHORT à 4221.37 :
  **MFE +0.414 %** favorable, **MAE ≈ 0** (jamais revenu au-dessus de l'entrée), TP/SL non
  touchés. MAIS journal = **`EXPIRED` / `NOFILL`** : les limites OTE étaient au-dessus d'un
  marché qui chutait → **le pullback de remplissage n'est jamais venu**. Direction JUSTE
  (+0.41 % dispo) mais **entrée ratée** → prod flat (0 capté, 0 coût).
- **Synthèse momentum du jour (2 épisodes convergents)** : (1) clean-trend scalp 13:45 = entrée
  REMPLIE puis mean-reverte (a saigné) ; (2) OTE 21h = entrée NON REMPLIE car tendance vraiment
  directionnelle. **Le problème n'est pas la direction mais la CAPTURE nette.** = PRIORITÉ §81(b)
  entry-mode. **Mais NON jugeable sur le lake** (pas d'orderflow/forecast/value-area) → spec
  Option A (feature store enrichi, attendre puissance) pour Sam. Rouvrir = DONNÉE, pas knob.
- **Juge** : **0 hypothèse** (espace exprimable épuisé, 28 KILLED). **Reco promo** : NON
  (paper = 1 fixture retirée). **Santé VERTE** (cycle 22:59, gate 1940/500, 0 erreur). **Lab 32/31/0/0.**

## 2026-06-18 23h30 (chercheur nocturne), cassure Donchian PURE bien-powered : referme "turtles naïfs"
- **Levier neuf de la nuit** : la cassure Donchian-20 SANS filtre de régime (er_min=0/adx_min=0
  → la cassure de canal canonique, Turtle System 1). Tout l'arc breakout antérieur (HS/HT 1h,
  HV 1d poolé) imposait le gate ER≥0.45/ADX≥30 → si sélectif que HV n'avait que **n_eff=14**
  (une fenêtre à 0 trade) : son KILLED mesurait surtout un MANQUE DE PUISSANCE, pas l'absence
  d'edge de la cassure. **Question canonique jamais jugée proprement** : le trend-following le
  plus naïf paie-t-il net de coûts sur GOLD/US500 au swing 1d ?
- **Verdict (paire GOLD↔ES, exit 1d calibré unique stop1.2/tp2.4/h10, AUCUN retuning)** :
  - **HZ_gold_donchian_nogate_1d → KILLED**, mais **enfin BIEN-POWERED** : n_eff=**63**,
    exp_net **+0.419 %**, **3/3 fenêtres positives**, MAIS IC95 **(−0.011, 0.846)** borne basse
    juste < 0, t=1.924 < z déflaté **2.965** (33e test famille). Résidu GOLD positif, sous le mur
    de la déflation, **exactement le motif HU/HQ** (le 1d gold montre un + non démontrable).
  - **IA_es_donchian_nogate_1d → KILLED** propre négatif : n_eff=**64**, exp_net **−0.107 %**,
    **0/3 fenêtres positives**, t=−0.55. Le contrôle ES **infirme** l'edge.
- **Cross-read (bull-gold)** : la positivité n'existe **que** sur GOLD, l'ES la contredit →
  cohérent avec **bêta passive du gold haussier**, PAS du trend-following généralisable. Cette
  fois **bien-powered des deux côtés** (n 63/64) : verdict plus solide que HV (n=14). **La
  cassure naïve ne constitue pas un edge sur les instruments de Sam.** Angle breakout no-gate
  refermé proprement.
- **Mining descriptif des 78 trades USER réels (report-only, backlog #2)** : (1) **session/ADX/
  score NON peuplés sur les REAL_TRADE** (uniquement sur AI_SIGNAL) → le conditionnement régime/
  score espéré **n'est pas faisable** sur les fills manuels (constat infra utile). (2) **Post-perte** :
  le trade suivant une LOSS → WR **51.5 %** (17/33) vs **61.4 %** (27/44) après un gain (~−10 pts),
  cohérent avec un léger tilt, mais exp ≈ plat des deux côtés et n petit → **descriptif, aucune
  conclusion** (pas d'IC, non jugeable sur le lake). (3) Direction : LONG 54.8 %/−0.073 % vs
  SHORT 59.6 %/+0.047 %, dans le bruit, **aucun sign-flip**.
- **Reco promo** : NON (0 paper réel). **Lab 34/33/0/0** (mortalité ~97 % maintenue). Prod GELÉE.

## 2026-06-19 09h (analyst), GOLD overnight : direction JUSTE, capture ~NULLE (récidive §81b)
- **Prod** : séquence dense de **GOLD SHORT `OTE_RETRACEMENT`** (18/06 19:05 → 19/06 05:30, entries
  4226 → 4138). GOLD a chuté **~4226 → ~4137 (~−2.1 %)**, régime affiché **TENDANCE PROPRE 🟢**
  04:37-05:05 (A_SETUP conf 7.8, RR 2.0-2.4) puis MOYENNE 🟡. **Direction SHORT excellente.**
- **Réalisé** : **6 entrées / 7 EXPIRED (NOFILL)** : les limites OTE posées AU-DESSUS d'un marché
  qui descend en ligne, le repli de remplissage n'est jamais venu. La seule remplie (05:30) sur un
  micro-rebond s'est refermée sans gain net notable. **Capture ~nulle malgré ~2 % directionnels dispo.**
- **Diagnostic** : RÉCIDIVE EXACTE du 18/06 soir. Pas la direction, la **CAPTURE** → **PRIORITÉ §81(b)
  entrée-marché vs OTE en clean-trend**. NON jugeable sur le lake (pas de simulation de fill OTE ni
  d'orderflow) ; la version lake-exprimable (`momentum_regime`/`momentum_breakout`) est déjà KILLED.
  → reste la **spec Option A** (feature store enrichi, MFE/MAE marché vs fill OTE) pour Sam. DONNÉE, pas knob.
- **Juge** : 1 levier (paire ichimoku kumo-break **1d swing**, jamais testé à cet horizon) → **2 KILLED**.
  IB_gold n=25 exp +0.20 % (1/3 fenêtres, sous-powered) ; IC_es n=29 exp −0.07 %. **Signature gold-beta**
  identique à HZ/IA d'hier → 2ᵉ jour de suite : trend-following 1d sur gold = beta passive, pas un edge.
  **Angle ichimoku-au-swing refermé.** **Reco promo NON** (0 paper). **Santé VERTE** (cycle 08:59, gate
  2134/500, ret_4h OK, outbox 39/39, 1 crash 18/06 auto-cicatrisé). **Lab 36/35/0/0.** Macro légère ;
  19/06 = OPEX triple-witching (pinning US500 PM à surveiller). Prod GELÉE.

## 2026-06-19 13h (analyst midday), beta-gold TRANCHÉ par 3ᵉ instrument (dollar)
- **Prod matin (09h→13h)** : A_SETUP GOLD SHORT 07:59 (entry 4171.61, RR 1.82) rempli ~08:21
  → GOLD descend ~4150 (profit latent) puis re-chope ~4162, **trade TOUJOURS OUVERT** (ni TP
  4141 ni SL 4188). US500 : WATCH SHORT OTE conf 7.0 mais **entry CAPPED → RR ~1.04**, jamais
  A_SETUP, **aucun fill** : marché **pinné max-pain 7500** (OPEX triple-witching). Régime = chop
  pur (HACHÉE 🔴 / TRANSITION 🟡), F&G 14, VIX +5 %.
- **Verdict momentum du jour** : régime HOSTILE au momentum (pinning + Extreme Fear + chop) ;
  rien à capter. La prod a bien lu (RR-floor a filtré les OTE US500 non-réachables). Rien que le
  momentum aurait mieux fait ce matin.
- **Cohérence (non-bug)** : le fill overnight 05:30 (GOLD SHORT 4138.42) a été **STOPPÉ**
  (−0.406 %, exit 4155.22 > stop), pas « flat » comme écrit à 09h. Sémantique, conclusion
  inchangée (capture overnight négative).
- **Juge, PAIRE neuve (3ᵉ instrument = DOLLAR DX-Y.NYB, arbitre du confond beta-gold)** :
  substitution d'instrument PURE des tests gold 1h KILLED (params/exit identiques, aucune valeur
  pêchée), aux 2 modes d'entrée.
  - **ID_dollar_momentum_regime_1h → KILLED** : n=16 (sous-powered), exp **−0.10 %**, 1/3 fenêtres,
    t=−0.57. variant_of HH.
  - **IE_dollar_momentum_breakout_1h → KILLED BIEN-POWERED** : n=**34**, exp **−0.048 %**, 1/3
    fenêtres, t=−0.68. variant_of HS.
  - **Cross-read décisif** : GOLD positif non-démontrable (beta) · ES négatif · **DOLLAR négatif
    bien-powered** → 3 instruments × 2 familles. **Le momentum de tendance intraday n'est pas un
    edge net de coûts sur les macros liquides** ; la positivité gold = beta passive. **Arc
    momentum-intraday-lake-exprimable FERMÉ.** Caveat : DOLLAR sur coûts FALLBACK génériques (sonde
    de facteur, pas reco, le bot ne trade pas le DXY).
- **Reco promo** : NON (0 paper). **Lab 38/37/0/0** (~97 %). Prod GELÉE. Marge restante = CAPTURE
  §81b (non lake-jugeable) → spec data Option A pour Sam.

## 2026-06-19 17h (analyst après-midi), le TP à 0.16 pt : §81a, pas seulement §81b
- **Le trade vivant** : A_SETUP GOLD SHORT 07:59 / fill 08:21 (entry 4171.61, stop 4188.25,
  tp1 4141.40, RR 1.82) **TOUJOURS OUVERT** à 17h. Champs réalisés (journal) : **mfe 0.72 %**,
  mae −0.26 %, `lo_since=4141.56` : le plus-bas est venu mourir à **0.16 pt** du TP (4141.40)
  **sans le déclencher**, puis l'or a reflué vers ~4148.8 (+0.56 % latent, RANGE ⚪ PM). Stop
  (4188.25) jamais menacé (hi 4182.48).
- **Diagnostic, la nuance qui manquait** : depuis 3 jours l'autopsie blâme la CAPTURE D'ENTRÉE
  (§81b, OTE NOFILL). Aujourd'hui l'entrée A REMPLI et la direction était JUSTE, et on a quand
  même rendu le gain. La cause ici n'est PAS l'entrée mais le **placement du TP (§81a)** : un TP
  posé pile sur la MFE attendue (0.726 % vs MFE réalisée 0.72 %) est, en pratique, **inatteignable** : il faut que le marché aille STRICTEMENT au-delà de son extrême réalisé. Un TP marginalement
  plus proche, OU un verrou partiel / trail au-delà de +0.5 %, capturait ce trade. C'est la 1ʳᵉ
  preuve intraday (n=1, donc indicative) que la marge n'est pas QUE l'entrée : c'est aussi
  l'**exit/lock**.
- **Le 2ᵉ fill du jour (05:30 SHORT 4138.42)** : mfe **0.20 %** seulement, jamais near-TP,
  STOPPÉ −0.43 % (exit 4155.22). Chop overnight → direction non confirmée, rien à verrouiller.
  Asymétrie nette : le signal de NY-pré-open (08:21) porte, l'overnight (05:30) ne porte pas.
- **Limite** : seuls **2 fills** ont le tracking mfe/mae (champ récent) → autopsie capture
  QUALITATIVE, pas statistique. C'est exactement ce que l'**Option A** (feature store enrichi
  MFE/MAE marché-vs-fill, spec 13h) résoudrait à n>15. Rien de neuf à JUGER sur le lake.
- **Régime PM** : GOLD RANGE ⚪ (delta −95.9k, vendeurs mais sans tendance propre), US500 TENDANCE
  MOYENNE 🟡 fc LONG mais NO_TRADE (RR/confluence insuffisants), 🟡 PRUDENCE, F&G 14, post-OPEX.
  Le momentum n'avait rien de net à capter l'après-midi ; la prod a eu raison de rester flat.
- **Juge** : 0 soumission. L'arc momentum-intraday lake-exprimable est FERMÉ (13h, 3 instr × 2 fam) ;
  le lake n'a que 1h/1d (pas de 15m) ; cot_extreme GOLD était déjà testé (HD, 06-13 → dedup l'a
  attrapé). Aucune hypothèse NEUVE on-thème exprimable dans les familles existantes sans re-knob →
  **je ne churne pas la déflation** (discipline). La seule idée neuve (momentum_regime LOCALISÉ
  PAR SESSION) exige une famille COMPOSÉE → **spec pour Sam** (rapport 17h). **Lab 38/37/0/0.**
  Reco promo NON (0 paper). Santé VERTE. Prod GELÉE.

## 2026-06-19 ~23h45 (CHERCHEUR nocturne), le lake est ÉPUISÉ, et c'est mesurable

Slot chercheur nocturne (après les 4 slots analyste 09/13/17/23h). Mon autopsie
porte sur le **lab** (l'intraday du jour est couvert ci-dessus par l'analyste) :
pourquoi l'espace lake-jugeable est clos, et ce que disent les 291 setups prod.

- **Ingestion** : `resim_report.py` → référence USER **inchangée** (WR 57.7 % n=78,
  exp −0.001 %/trade ; fenêtre récente **8 décisifs** seulement, IC boot-jours
  (0.055, 0.64) → < 15, **insuffisant**, statu quo). `feature_store.py` → gate
  **2378/500**, apprentissage autorisé, **0 MIXED**, **291 setups avec outcome**
  (+91 vs les 200 du 18/06 ; A_SETUP 271 / WATCH 186 / NO_TRADE 4565).
  `journal.json` exécution figée (dernier USER 08/06), **0 PAPER** → `check_demotions`
  sans objet. Aucune injection externe (news/calendrier traités comme donnée).

- **AUTOPSIE LAB, épuisement DÉMONTRÉ, pas supposé** : les **11 familles** de
  `strategy_families.py` ont toutes été jugées et **toutes tuées** (registry 38/37).
  La dernière famille à n'avoir que 2 instances, `cot_extreme`, est **épuisée sur
  le lake** : `cot_5y.parquet` ne contient de COT que pour **GOLD et US500**, et les
  deux sont tués (HD gold exp −0.46 % n=29 ; HE es exp +0.03 % n=21, contrarian
  10/90, négatif/plat des deux côtés, sous-powered). Le relancer voudrait dire soit
  **sweeper l'exit** (ce qu'aurait fait `IF_gold_cot_extreme_1d`, écrit au slot 17h
  mais à juste titre **non soumis** : changer tp 2.5→4.0/h 10→15 pour sauver HD mort),
  soit **mode="follow"** (sign-flip après contrarian tué). Les deux sont interdits.
  → **Aucune hypothèse lake-jugeable NEUVE n'existe sans re-knob/sweep/sign-flip.**

- **MINING 291 setups (report-only, score prod HORS-lake → NON jugeable)** : deux
  anomalies contre-intuitives à signaler à Sam (descriptif, pas d'IC, proxy ret_4h
  signé 4h sans stops/coûts, comparaisons multiples, **aucune conclusion**) :
  1. **WATCH (+0.21 %, n=134) > A_SETUP (−0.06 %, n=157)** : les setups de conviction
     SUPÉRIEURE rendent MOINS à 4h. Indice possible d'**entrée tardive sur extension**
     des A_SETUP, à creuser, pas à conclure.
  2. **TENDANCE PROPRE 🟢 NÉGATIVE (−0.23 %, n=60)** vs TENDANCE MOYENNE 🟡 (+0.24 %,
     n=123) : le régime « tendance propre » sous-performe (drag concentré sur
     **ASIAN×PROPRE −0.28 %, n=54**). Cohérent avec un effet d'**épuisement de
     tendance** / mauvaise asymétrie d'entrée en trend mûr.
  - Session : **LONDON +0.34 % (n=51)** et **NY_PM +0.32 % (n=29)** portent ;
    **US_PM −0.20 %**, **NY −0.17 %**, **US_CLOSE −0.17 %** pèsent. Re-confirme
    l'asymétrie « pré-open/Europe porte, US-PM chope » vue par l'analyste (n=2 fills).
  - Ces structures **vivent dans la donnée prod**, pas dans le lake → elles
    **motivent des specs** (famille composée régime×session ; vol_extreme), **pas**
    une soumission au juge.

- **Verdict nocturne** : **0 soumission**, par épuisement vérifié du lake (pas
  paresse). Forcer un 39e test inflaterait la déflation Bonferroni GLOBALE pour
  zéro information neuve. **Lab 38/37/0/0**, mortalité ~97 % maintenue = santé.
  Reco promo NON (0 paper). Prod GELÉE ; rien ici n'autorise de changement live.

## 2026-06-20 ~23h45 (CHERCHEUR nocturne), fermeture de la matrice ichimoku × US500 (3 cellules comblées, 3 KILLED)

Slot chercheur nocturne (après les 4 slots analyste week-end 09/13/17/23h, tous
🟢 santé verte / 0 trade / marché fermé samedi). Mon autopsie porte sur le **lab** :
contrairement aux nuits précédentes (« 0 soumise, lake épuisé »), un audit
**asset-par-asset** (et non famille-par-famille) révèle une vraie surface NEUVE.

- **Ingestion** : `resim_report.py` → référence USER **inchangée** (WR 57.7 % n=78,
  exp −0.001 %/trade ; fenêtre récente **8 décisifs**, IC boot-jours (0.055, 0.64)
  → < 15, **insuffisant**, statu quo, aucune décision avant 1 mois forward-test).
  `feature_store.py` → gate **2378/500**, apprentissage autorisé, **0 MIXED**,
  **291 setups avec outcome** (inchangé vs 19/06, week-end, 0 donnée neuve).
  `journal.json` exécution figée (dernier USER 08/06), **0 PAPER** → `check_demotions`
  sans objet. Lake rafraîchi 07:00 (mêmes 6 actifs + COT). Aucune injection externe.

- **DÉCOUVERTE (révision du « lake épuisé »)** : la batterie ichimoku a été jugée
  **5/5 KILLED sur GOLD** (HC kumo, HF tk_cross, HG kijun_reject, HJ chikou, HN twist)
  mais seulement **2/5 généralisée à US500** : kumo (IC, 1d) et twist (HO, 1h). Les
  reports nocturnes parlaient de « 11/11 familles tuées », vrai au niveau **famille**,
  mais **3 cellules ichimoku × US500-1h étaient VIDES** : tk_cross, kijun_reject,
  chikou_confirm. US500 est tradé par le bot (on-thème), ES=F est dans le lake
  (13719 barres 1h, yfinance homogène) → **jugeable cette nuit**. Précédent exact :
  HO (généralisation twist→US500, mêmes params/exit, variant_of). **Ni re-knob, ni
  sign-flip, ni hors-thème** : même question de validité externe.

- **3 SOUMISES → 3 KILLED** (exit canonique ichimoku-1h stop0.8/tp1.5/h48, speed
  standard, déflation Bonferroni GLOBALE z≈3.0) :
  - **IF** tk_cross US500 : n=152, exp **−0.047 %**, t=−0.45, IC95 (−0.198, +0.099),
    fenêtres (−0.10, +0.03, −0.06). variant_of HF.
  - **IG** kijun_reject US500 : n=208, exp **−0.038 %**, t=−0.25, IC95 (−0.162, +0.084),
    fenêtres (−0.14, +0.03, −0.00). variant_of HG (qui était t=−5.97 sur GOLD).
  - **IH** chikou_confirm US500 : n=329, exp **−0.020 %**, t=+0.45, IC95 (−0.124, +0.087),
    fenêtres (+0.02, −0.01, −0.07). variant_of HJ.
  Tous **bien powered** (n≫30), tous exp≈0 / t≈0, aucun ne passe le moindre check.
  Lecture : sur US500 ces 3 signaux sont **du bruit centré sur zéro** (moins négatifs
  que sur GOLD où kijun_reject saignait −0.28 %, pas un edge pour autant : exp net ≤ 0,
  IC chevauche 0). Le cross-read habituel tient : ichimoku ne paie pas net de coûts.

- **CE QUE ÇA FERME** : ichimoku est désormais jugé **EXHAUSTIVEMENT sur les 2 actifs
  tradables** (GOLD 5/5, US500 5/5). Le constat « ichimoku épuisé » cesse d'être une
  assertion avec des cellules vides → c'est un **fait démontré**. Les nuits futures ne
  doivent plus reproposer ichimoku × {GOLD, US500} sans nouvelle famille/horizon/donnée.

- **Verdict nocturne** : **3 soumissions, 3 KILLED** par discipline de complétude
  (pas du churning : surface réellement vide, bien-powered, prior faible assumé).
  **Lab 41/40/0/0**, mortalité ~98 % maintenue = santé. Reco promo **NON** (0 paper).
  Prod **GELÉE** ; rien ici n'autorise de changement live. Le juge tranche, Sam promeut.

## 2026-06-21 09h, Analyst matinal (dimanche, marché fermé)

- **Santé 🟢 6/6** : cycle 08:57 (<12 min, 100 cycles/j), resim USER inchangé (WR 57.7 %
  n=78, fenêtre 8<15 insuffisante), gate 2378/500 0 MIXED, ret_4h se remplit (2538/9009),
  0 erreur log, datafeed tradingview 4/4, outbox 6/6 ok:true cohérents. Aucune correction requise.
- **Autopsie momentum** : 200 décisions du jour = **100 % NO_TRADE / 100 % RANGE ⚪** (GOLD+US500),
  F&G 23 Extreme Fear. Régime RANGE = terrain le plus hostile au momentum (gate ER/ADX ne
  déclenche pas) → bot NO_TRADE À RAISON, aucun trade live à autopser. Le momentum n'aurait ni
  fait mieux ni pire (pas de signal). Lundi 22/06 = 1re séance post-CB, calme côté US (CAD CPI +
  Lagarde 14:30 ; 1er vrai catalyseur US = Flash PMI mardi 23/06 15:45 Paris).
- **0 hypothèse soumise (discipline)** : données lake identiques au nocturne d'hier (dimanche →
  0 barre neuve) ; familles momentum exhaustivement KILLED exp≈0 ; matrice ichimoku fermée 5/5
  GOLD+US500 ; RR/TP-par-régime arithmétiquement vide sur entrées à edge nul ; confluences
  neuves (momentum×session, momentum×COT) NON exprimables sans nouvelle famille (token Sam).
- **Backlog Sam** : (1) lake 15m = déblocage thèse intraday ; (2) spec famille
  `momentum_regime_session` fournie (momentum gaté ER/ADX restreint fenêtre cash US, variant_of HH).
- **Reco promo NON** (0 PAPER). Lab 41/40/0/0. Prod GELÉE.

## 2026-06-21 23h30, Chercheur nocturne (dimanche soir, lake figé vendredi)

- **Ingestion** : pas de `research/PAUSE`. resim Gate-1 USER **inchangé** (WR 57.7 % n=78
  exp −0.001 %, fenêtre récente 8 décisifs < 15 = insuffisante, statu quo). feature_store
  gate **2378/500**, apprentissage_autorisé, **0 MIXED**, 291 setups. **Lake byte-identique
  à hier soir** : dernier bar GC=F/ES=F 1h = vendredi **19/06 03:00 UTC**, 1d = 19/06 ; le
  download 07:00 a tourné mais yfinance n'a rendu **0 barre de week-end**. 1re surface neuve
  = lundi 09h. Aucune injection externe (calendar/news traités en donnée seule).
- **Autopsie lab (matrice ichimoku par horizon)** : audit signal×horizon → ichimoku fermé
  5/5 en **1h** sur GOLD et US500, mais au **swing 1d** seul kumo_break était jugé (IB/IC,
  19/06). Les 3 confluences tk_cross / kijun_reject / chikou_confirm n'avaient **jamais** de
  verdict 1d (cellule explicitement teed-up par le backlog #1 du nocturne 20/06, route b).
- **3 soumissions, 3 KILLED** (II/IJ/IK, pool GOLD+US500, 1d, exit swing stop1.2/tp2.4/h10
  = IB/IC/HQ/HR, speed=standard) :
  - II tk_cross : n_eff **36**, exp **−0.063 %**, IC95 (−0.59, +0.48), t=−0.225, z=3.038.
  - IJ kijun_reject : n_eff **69**, exp **−0.041 %**, IC95 (−0.45, +0.35), t=−0.243, z=3.045.
  - IK chikou_confirm : n_eff **249**, exp **+0.021 %**, IC95 (−0.18, +0.22), t=+0.097, z=3.052.
  - **Tous bien-powered** (n_eff≥30, contrairement aux mono HQ n=12 / HR n=8 KILLED « faute
    de n ») : le **pool** a livré la puissance nommée par le lab → **close MESURÉ**, pas une
    défaite de puissance. Tous exp≈0, t≈0, IC chevauche 0 → **bruit centré sur zéro**, aucun
    edge. Le franc négatif gold-1h (HG kijun t=−5.97) ne survit pas au swing poolé : c'était
    de la sélection 1h sur gold, pas un effet stable.
- **Ce que ça ferme** : ichimoku est désormais jugé sur **{1h,1d} × {GOLD,US500}** pour **4/5
  signaux** (kumo, tk_cross, kijun_reject, chikou). Seul **twist_1d** reste vide (4ᵉ signal,
  hors budget 3/nuit, prior le plus faible, HN/HO twist à plat en 1h) → résidu unique, déféré.
  « Ichimoku épuisé au swing » cesse d'être une assertion : c'est un **fait mesuré bien-powered**.
- **Verdict nocturne** : **3 KILLED** par complétude jugeable (cellule réellement vide, clean,
  precedent exact IB/IC + HU/HV/HW ; ni re-knob, ni sign-flip, ni hors-thème). **Lab 44/43/0/0**,
  mortalité ~98 % maintenue = santé. Reco promo **NON** (0 paper). Prod **GELÉE** ; rien ici
  n'autorise de changement live. Le juge tranche, Sam promeut.

## 2026-06-22 09h, Analyst matinal (lundi, 1re surface lake NEUVE)

- **Santé** : VERTE 6/6. Watcher cycle 08:55 (<12 min), 0 erreur prime_watcher.log, datafeed
  tradingview 6/6, briefing 09:00 cohérent (GOLD 4198 MIXED / US500 7492 MIXED / PRUDENCE / F&G 20).
  feature_store gate 2486/500 (+108 vs nocturne), 0 MIXED, 299 setups, ret_4h se remplit (2648/4171).
  resim USER inchangé (WR 57.7% n=78 exp -0.001%, récent 8<15 décisifs = insuffisant).
- **Autopsie** : journal inchangé depuis vendredi (week-end+lundi matin 100% NO_TRADE) → aucun trade
  live à autopser. Régime d'ouverture TRANSITION/RANGE MIXED, NO_TRADE des 2 côtés à raison, terrain
  hostile au momentum. Pas de catalyseur US 1er rang (CAD CPI+Lagarde 14:30, Flash PMI US = mardi).
- **Lake enfin frais** : dernier bar lundi 22/06 04:00 UTC (vs vendredi 19/06 gelé tout le week-end),
  +1.5 jour. La surface neuve promise par le nocturne 21/06 est arrivée à l'heure.
- **1 soumission, 1 KILLED, dernière cellule de la matrice ichimoku** :
  - **IL_pool_ichimoku_twist_1d** (pool GOLD+US500, 1d, exit stop1.2/tp2.4/h10, speed standard,
    variant_of HN, famille test #45) : n_eff **30**, exp_net **+0.5612%**, IC95 **(−0.007, +1.178)**,
    t **1.792** vs z déflaté **3.059**, fenêtres (12;−0.074)(11;+0.953)(7;+1.035) = 2/3 positives.
  - **Résultat le plus VIVANT de toute la matrice ichimoku** (seul point estimate nettement positif,
    2/3 fenêtres à ~+1%), mais **KILLED proprement** : IC95 borne basse effleure zéro (−0.007 → effet
    non distinguable de zéro) et t≪z déflaté. Twist = événement rare (n=30 même poolé). Aucun
    sign-flip, aucun re-knob. À re-vérifier SI le lake 1d s'épaissit nettement, pas avant (sinon mining).
- **Ce que ça ferme** : ichimoku jugé **5/5 sur {1h,1d}×{GOLD,US500}** : plus aucune cellule vide,
  plus aucun résidu déféré. « Ichimoku épuisé au swing » est un fait mesuré COMPLET et bien-powered.
- **Verdict** : Lab **45/44/0/0**, mortalité ~98% = santé. Reco promo NON (0 paper ; le near-miss
  twist n'autorise rien). Prod GELÉE ; rien ici n'autorise de changement live. Le juge tranche, Sam promeut.

## 2026-06-22 17h, Analyst après-midi (trigger momentum LIVE raté, ON-THÈSE)

- **Santé** : VERTE 6/6. Cycle 17:01 (<6 min), 0 erreur log, datafeed tradingview 6/6. feature_store
  gate 2664/500 (+90 vs 13h), 0 MIXED, 299 setups, ret_4h se backfille. resim USER inchangé
  (WR 57.7% n=78 exp -0.001%, 8<15 décisifs = insuffisant). Lake TOUJOURS byte-identique 07:00.
- **ÉVÉNEMENT LIVE ON-THÈSE** : à 16:00 (14:00 UTC) le bot a émis une alerte scalp `trend_day`
  **US500 LONG** : ADX15m 35.9 (>30), ER 0.475 (>0.45), 15m/1h alignés, **TENDANCE PROPRE 🟢 @ 7527.7**,
  zones rebond EMA20 15m 7503.5 / EMA50 15m 7493.2. **Réalisé** : retournement en 28 min, régime
  PROPRE→HACHÉE, cassure NETTE des deux zones de rebond, bas **7466.6** (−0.81%), rebond partiel 7480
  (−0.63%) à 17h. **Aucun catalyseur macro** (Waller Low 13:00 UTC, pas d'event US 1er rang) → reversal
  purement flux/technique. Un momentum « achat sur repli » aurait pris position à 7503/7493 = perdant.
- **Lecture thèse** : filtre de régime « propre » (ADX 35.9, ER 0.475, valeurs franchement
  tendancielles) **n'a PAS protégé** du reversal intraday → confirme EN LIVE le KILL backtest de HA
  (12/06, « filtre de régime SEUL insuffisant »). La confluence manquante = invalidation STRUCTURELLE
  (cassure EMA rebond / clôture 15m), pas « plus d'ADX ». n=1, ne tue pas la thèse mais chiffre le risque.
- **Grader rigoureux** : NO_TRADE 2/2 tout l'après-midi → s'abstenir était CORRECT, le réalisé lui a
  donné raison. Séparation scalp-advisory / grader-décisionnel saine, pas un bug. journal inchangé
  depuis 19/06 16:21 (alerte non journalisée, advisory). GOLD plat TRANSITION 🟡, NO_TRADE à raison.
- **Hypothèses** : 0. Le trigger est 15m → INJUGEABLE faute de lake sous l'heure (déblocage [DONNÉES]
  n°1). Lake byte-identique 07:00, 11 familles toutes KILLED dessus → re-soumettre = doublon/re-knob
  interdit. Nouvelle spec déposée : `momentum_trend_invalidation` (trend-day + invalidation structurelle).
- **Verdict** : Lab 45/44/0/0, reco promo NON (0 paper). Prod GELÉE. Le juge tranche, Sam promeut.

## 2026-06-22 23h, Analyst soir (clôture de séance : le reversal n'a jamais été repris)

- **Santé** : VERTE 6/6. Cycle 22:55 Paris (<5 min), 0 erreur log, watchdog 0 o, datafeed
  tradingview 6/6 (pas de fallback). feature_store gate **2796/500** (+132 vs 17h), 0 MIXED,
  299 setups, ret_4h continue de se backfiller. journal inchangé depuis 19/06 16:21 (120 signals,
  WR 59.3% exp +0.059%, week-end + lundi sans trade live tracké). Outbox tout ok:true, cohérent.
  Lake **byte-identique 07:00** (4e passage consécutif).
- **CLÔTURE DE L'AUTOPSIE DE 16:00** : après le retournement (signal LONG @ 7527.7 → bas 7466.6),
  US500 **n'a JAMAIS repris** le niveau du signal sur le reste de la séance. Trajectoire 15:00→21:00 UTC :
  régime HACHÉE 🔴 → TRANSITION 🟡 → RANGE ⚪, chop **7460-7488**, clôture **7471.6** (≈ **−0.74%**
  sous le signal, jamais retesté). **Un momentum « achat sur repli » entré à 7503/7493 serait resté
  sous l'eau toute la soirée** : le reversal n'était pas un bruit ré-absorbé, mais un vrai changement
  de pied tenu jusqu'à la clôture. Renforce (n=1 toujours) le constat : le filtre ER/ADX seul ne
  protège pas, et ici même un trailing-stop large n'aurait pas sauvé un LONG.
- **GOLD** : dérive 4199.95 → 4189.67 (bas **4172.0**), TRANSITION 🟡 → RANGE ⚪, NO_TRADE toute la
  soirée. Un setup `OTE_RETRACEMENT` SHORT (conf 7.7, 4/4 aligné, RR 1.38 @ 4196) a bien été **VETO**
  (session OVERNIGHT spreads élargis + news radar 🔴) → NO_TRADE. Directionnellement le SHORT aurait
  été marginalement bon (4196→4172) mais le veto overnight/news-rouge est la bonne discipline.
- **Régime de fin de séance** : radar **🔴 NE PAS TRADER** (F&G 20 Extreme Fear, 3 news
  incertaines/contradictoires), briefings 18:00 et 21:00 cohérents. Terrain hostile au momentum :
  s'abstenir est le bon trade. Grader NO_TRADE partout = correct, validé par le réalisé.
- **Hypothèses** : 0. Lake byte-identique, 11 familles toutes judged-and-KILLED dessus → re-soumettre =
  doublon/re-knob = data-mining interdit. Le trigger 16:00 vit en 15m → injugeable (déblocage [DONNÉES]
  n°1). Spec `momentum_trend_invalidation` reste sur le token de Sam.
- **Verdict** : Lab 45/44/0/0, reco promo NON (0 paper). Prod GELÉE. Le juge tranche, Sam promeut.

## 2026-06-22 nocturne, Chercheur (verif registry-vs-code + blocage infra COT poole)

- **Surface lake byte-identique 07:00** (5e passage de la journee, apres les 4 slots analyste).
  resim USER inchange (WR 57.7% n=78 exp -0.001%), feature_store gate 2803/500 (0 MIXED, 299
  setups, ret_4h backfille), journal fige depuis ven 19/06 (120 signals). 0 erreur pipeline.
- **Verif directe** : les 11 familles du registry == les 11 de strategy_families.FAMILIES, toutes
  judged-and-KILLED sur cette surface (matrice ichimoku close 5/5 sur 1h/1d x GOLD/US500).
  "11 familles toutes KILLED" est donc EXACT, pas approxime.
- **Angle neuf envisage et ECARTE, power-remedy COT poole GOLD+US500** : HD (gold COT n=29 exp
  -0.46%) et HE (es COT n=21 exp +0.027%) ont ete KILLED le 13/06 pour SOUS-PUISSANCE (extremes
  COT rares). Pooler les deux (~50 trades) est le remede de puissance approuve du lab (cf II/IJ/IK,
  HU/HV/HW). MAIS : harness.evaluate passe UN ctx_fn keye sur le timestamp seul, partage par tous
  les actifs du pool ; or COT-GOLD != COT-ES au meme instant => un pool COT en un seul appel
  CONTAMINERAIT le contexte. Cle jamais testee (HD/HE mono) mais INJUGEABLE proprement sans
  extension du harness. Je n'ai PAS lance le test contamine (remplir un quota avec un test biaise
  = interdit). Backlog #3 (NOUVEAU) : ctx_fn par actif (~5 lignes, token Sam) -> 1 hyp bien-powered
  jugeable (COT contrarian poole, meme direction, PAS un sign-flip).
- **Hypotheses** : 0 (resultat correct sur surface identique : tout serait doublon/re-knob/test
  contamine). VIX-vol-conditional ecarte aussi (aucune famille ne lit un champ ctx de vol).
- **Verdict** : Lab 45/44/0/0, reco promo NON (0 paper). Prod GELEE. Le juge tranche, Sam promeut.

## 2026-06-23 09h (analyst midday), momentum SHORT du matin : la BONNE direction (n=1), miroir du LONG raté d'hier
- **Contexte régime** : nuit/matin RISK-OFF net, VIX +3.1%, NASDAQ -2.23%, F&G 23 (Extreme Fear),
  forecast Prime SHORT sur GOLD ET US500 (toutes TF). Les DEUX actifs ont chuté : GOLD ~4133→4114
  (-0.7% sur la fenetre 05:24→09:00, briefing 09:00 -1.91% j), US500 ~7438→7381 (-0.77%), US500
  passe TENDANCE PROPRE 🟢 a partir de ~07:41 (downtrend qui se nettoie).
- **Evenement ON-THESE** : 05:36 alerte 🔥 SCALP TENDANCE **US500 SHORT** (ADX15m 40.3 >30, ER 0.451
  >0.45, 15m/1h alignes, "conditions du 5 juin reunies") + setups Prime **GOLD SHORT** repetes
  05:14→06:09 (entry ~4142, tp 4114.92 ; 06:09 entry 4130.5 tp 4092.2). **Cette fois la direction
  momentum etait BONNE** : GOLD a touche la zone TP1 (4114), US500 SHORT ~-0.74%. La tendance a
  PERSISTE apres le trigger, exactement l'inverse du LONG @7527.7 d'hier 16:00 (reversal, -0.81%).
- **MAIS le bot n'a pas trade** : alertes en session OVERNIGHT/PRE_NY ; grade retombe A_SETUP→WATCH→
  NO_TRADE des 08:31 sans conversion A_SETUP propre en session NY. Donc "would-have", pas un trade
  tracke. Ironie honnete du registre vivant : le scalp QUE le bot pouvait trader (hier 16:00 NY) a
  PERDU ; celui qui a GAGNE (ce matin 05:36) etait correctement veto overnight. n=2 split, aucun
  des deux ne valide le scalp momentum live.
- **Lecture** : l'edge du scalp depend ENTIEREMENT de la persistance post-entree, que ER/ADX
  (retrogrades) ne predisent pas, hier non, aujourd'hui oui. C'est precisement le KILL de HA
  (filtre de regime SEUL insuffisant) et l'argument pour la confluence trend_invalidation : on ne
  predit pas la persistance, mais on peut COUPER vite a la cassure (aurait sauve hier, aurait
  laisse courir aujourd'hui). Le FORECAST directionnel (SHORT/SHORT) etait juste en live (+1 sur 2
  actifs), mais forecast != trade : aucun setup tradeable propre en session.
- **Hypotheses** : 0. Surface lake ENFIN fraiche (barre journaliere lundi 22/06 cloturee + barre
  partielle mardi 23/06 ; daily 1257 barres), MAIS +1 barre journaliere ne re-ouvre AUCUN verdict
  decisif (re-knob/doublon interdit ; twist_1d ne se re-teste que si le lake 1d "epaissit
  nettement", pas +1 barre). Les 11 familles == FAMILIES, toutes judged-and-KILLED, matrice
  ichimoku 5/5 complete. Confluences manquantes (trend_invalidation, COT poole par-actif,
  momentum×session intraday) NON exprimables / token Sam + lake 15m.
- **Verdict** : Lab 45/44/0/0, reco promo NON (0 paper). Prod GELEE. Le juge tranche, Sam promeut.

## 2026-06-23 17h, Analyst (PRIME momentum intraday)

- **Contexte live** : risk-off net cet apres-midi (VIX +11.9%, NASDAQ -2.74%, F&G 23 Extreme
  Fear). US500 hache-baissier ; GOLD range/transition. Bot 100% US500 SHORT A_SETUP en continu
  depuis 09:21 Paris (OTE_RETRACEMENT, sell-limit AU-DESSUS du prix, TP en-dessous).
- **Trajectoire US500 realisee (cycles)** : bas du jour 7358.8 (15:27) -> RETRACEMENT HAUSSIER
  net jusqu'a pic 7417.4 (16:17, +59 pts) -> repli 7394.3 (16:55) -> 7401.1 (17:01). Regime passe
  TENDANCE MOYENNE 🟡 -> TENDANCE HACHEE 🔴 a 15:49 quand le rebond devient violent (label correct).
- **AUTOPSIE FILL/TP (le coeur)** : pour la 1ere fois de la journee un VRAI retracement haussier
  a teste les sell-limits OTE. Trois cas exposes :
  1. Cluster 11:27-12:27 (entry ~7395, tp 7353.9) : prix max sur la fenetre ~7382 -> JAMAIS rempli,
     PUIS prix tombe a 7358.8 (~5 pts au-dessus du TP) = la cible aurait quasi ete touchee mais le
     trade n'a jamais ete entre (NO-FILL, would-have). Confirme le 13h.
  2. Setup 15:44 (entry 7395.96, tp 7349.5) : prix monte 7392.9->7399.1 et CROISE 7395.96 vers
     15:55-16:00 -> 1er FILL plausible du jour (~7396). MAIS immediatement +21 pts ADVERSES
     (pic 7417.4) puis retour ~7401 -> position SOUS L'EAU, TP 7349.5 a ~50 pts. Fill = couteau qui
     tombe : entree pile au sommet du rebond.
  3. Setup 16:01 (entry 7418.52, tp 7377.23) : pic realise 7417.4 -> rate le fill de ~1 pt (textbook
     OTE near-miss), PUIS prix retombe a 7394 -> aurait file vers le TP. NO-FILL par 1 pt.
- **Lecture nette (n=1 live, on-these, 4e jour consecutif)** : l'OTE_RETRACEMENT est le point de
  defaillance recurrent, et il echoue de DEUX facons OPPOSEES le meme jour : (a) en down-drift
  persistant -> NO-FILL (cas 1 & 3) ; (b) quand le retracement arrive enfin -> FILL pile au sommet
  d'un spike haché -> drawdown immediat (cas 2). La DIRECTION (SHORT) reste juste toute la journee ;
  l'edge n'est NI dans la direction NI dans "attendre un meilleur prix", c'est le MODE D'ENTREE
  (sell-limit OTE) qui est mal apparie au regime haché. Renforce en live : (i) le KILL de HA
  (filtre de regime seul insuffisant), (ii) l'argument momentum_trend_invalidation (entree au
  marche/breakout a la cassure + coupe rapide), (iii) le besoin du lake 15m pour JUGER fill+TP.
  Les trois restent INJUGEABLES sans lake 15m (deblocage n1) / token Sam (famille).
- **GOLD** : cluster SHORT matinal (03:46-08:09) direction correcte (~4153->4118, -35 pts) ;
  apres-midi NO_TRADE (TRANSITION/range, 4125-4127) correct.
- **Hypotheses** : 0. Lake byte-identique 07:00 (= surface 09h ; l'apres-midi live n'est PAS dans
  le lake, re-download quotidien 07:00) -> aucune surface neuve, 11 familles toutes KILLED dessus,
  re-soumettre = doublon/data-mining interdit. Pas de lake 15m -> autopsie fill/TP injugeable.
- **Verdict** : Lab 45/44/0/0, reco promo NON (0 paper reel ; l'entree "PAPER" du registry =
  sentinel TEST_JUDGE_pass, exclu par lab_counters, pas une strategie). Prod GELEE.

## 2026-06-23 23h (evening), FILL réussi, TP non livré (dissociation des 2 failles)
- **US500 SHORT entry 7396.46 (OTE, OPEN)** : high soir 7406.9 > entry -> **FILL ce soir** (le retracement absent à 13h arrive). Bas 7363.3 = ~33 pts en faveur, MAIS **TP 7352.74 (VAL) raté de ~11 pts** (= même écart qu'à 13h : 7363.5 vs 7353.9). Stop 7422.28 jamais menacé. Position OPEN, ~+21 pts latents (7375.5), hold overnight.
- **GOLD SHORT entry 4142.47 (signal 17:42)** : high 4142.3 -> **rate le fill de 0.17 pt**, puis -> 4107.9 (aurait filé ~35 pts). NO-FILL near-miss (réplique du US500 16:01).
- **Chiffre clé** : journal.stats `ai_fill_rate=25.9%`, 20 `expired_nofill`. Le fill est le goulot structurel, désormais quantifié.
- **Lecture** : 5e jour, DIRECTION SHORT juste. Les 2 failles DISSOCIÉES aujourd'hui : (1) FILL (sell-limit OTE au-dessus, NO-FILL ou near-miss), (2) TP (cible VAL trop lointaine pour l'amplitude livrée en régime haché, ~11 pts manquants x2). Injugeable sans lake 15m.
- **Hypotheses** : 0 (lake byte-identique 07:00, pas de 15m, 11 familles KILLED -> doublon interdit). **Verdict** : Lab 45/44/0/0, reco promo NON, prod GELEE.

## 2026-06-23 nocturne, Chercheur (mining journal réel : la distribution MFE NUANCE la lecture "TP trop loin")
- **Ingestion re-vérifiée** : pas de PAUSE ; lake tous `*.parquet` mtime **2026-06-23 07:00** (5e passage, surface identique aux runs 09h/13h/17h/23h, **toujours 1h/1d, pas de 15m**) ; resim USER WR 57.7% [IC95 46.6-68.0] n=78 exp −0.001% (figé, journal sans trade live tracké) ; feature_store **3301/500**, **0 MIXED**, 458 setups, ret_4h backfill OK ; 11 familles registry == `strategy_families.FAMILIES` (vérifié), 44 KILLED + 1 sentinel PAPER (`TEST_JUDGE_pass`). Aucune injection dans news/calendrier (donnée traitée comme telle).
- **Mining descriptif (journal.json, lecture seule, PAS un verdict-juge)** : sur les signaux IA avec entry+tp+mfe (n=44) : **20 NOFILL** (le goulot, cf. `ai_fill_rate=25.9%`) et **24 fillés**. Parmi les 24 fillés : TP touchée 13/24 ; ≥50% de la distance TP 16/24. Distribution **BIMODALE** : les 4 perdants fillés ont une **MFE médiane 0.11% (max 0.20%)** vs TP-dist médiane 0.71%, ils bougent à peine en faveur (≈ dans la bande de coût/spread) avant de se retourner ; les 15 gagnants ont une **MFE médiane 2.06%** : ils filent loin.
- **Lecture qui CORRIGE l'intuition du jour** : le cas live de ce soir (US500, MFE ~0.45% / TP ~0.6%, raté de ~11 pts → ratio ~0.75) ressemble à "TP trop loin", mais sur les 44 trades du journal les **near-miss 0.5-0.9× sont RARES**. Le mode d'échec dominant reste le **NO-FILL (20)**, puis des **reversals à très faible MFE (~0.1%)** qu'une TP rapprochée ne sauve PAS (sous le coût). Rapprocher la TP **caperait surtout les gagnants à ~2%** qui portent l'espérance. → Le tradeoff (hit-rate ↑ vs reward ↓, coûts fixes) est **ambigu et doit être JUGÉ en espérance nette sur lake 15m**, pas estimé à l'œil sur 1 cas live. Item backlog "TP par régime" **reframé** : prix potentiel faible, risque (caper les 2%) élevé.
- **Hypothèses : 0** (surface identique → re-soumettre = DUPLICATE ; re-knob/sign-flip interdits ; objet le plus riche injugeable sans 15m). **Verdict** : Lab 45/44/0/0, reco promo NON, prod GELÉE.

## 2026-06-24 13h, Analyst (GOLD : le goulot FILL en direct, OTE incompatible avec le momentum sens-unique)
- **Santé VERTE 6/6** : watcher cycle 12:59 ; feature_store 3574/500 (+88 vs 09h), 0 MIXED, 487 setups ; resim figé (exp +0.318% IC95 0.017-0.578) ; journal 143 sig WR 58.6% exp +0.056% ; 0 ERROR ; 0 ok:false. Lab 45/44/0/0.
- **GOLD = no-fill systématique en direct** : 4 A_SETUP SHORT (07:37/08:48/09:42/10:42), TOUS EXPIRED (no-fill), entries chassées 4089→4076 pendant que le prix dérivait 4090→4055 (−35 pts, sens unique, prix sous le VAL 4080.85, recent_delta −60k). L'entrée OTE = sell-limit AU-DESSUS du marché : en dérive baissière le retracement n'arrive jamais → fill jamais obtenu. Direction JUSTE (Silver −1.66%, forecast 15m/1h/4h tous négatifs) mais capture ZÉRO. ai_expired_nofill 20→23, ai_fill_rate 25.9%→23.3%.
- **Lecture (racine commune des 2 goulots)** : hier US500 = goulot TP (fillé, TP-VAL trop loin) ; aujourd'hui GOLD = goulot FILL (jamais fillé). Même racine : OTE_RETRACEMENT est une entrée mean-reversion appliquée à une thèse momentum. Trend fort → OTE ne fille pas ; haché → fille mais TP loin pas atteint. Dans les deux cas momentum non monétisé. → backlog `momentum_trend_invalidation` (entrée marché/breakout) monte en priorité n°2.
- **Nuance régime** : GOLD labellisé TRANSITION/RANGE mais réalisé = dérive directionnelle −35 pts → le label ER/ADX sous-estime la directionnalité ; un déclencheur d'entrée marché devrait s'appuyer aussi sur l'alignement forecast multi-TF (ici 3/3 négatifs).
- **Hypothèses : 0** (lake byte-stable 07:00, 1h/1d, pas de 15m ; 11 familles KILLED ; objet entrée-marché injugeable sans 15m + famille pas encore approuvée). Reco promo NON, prod GELÉE.

## 2026-06-24 23h (evening), Analyst : l'OTE A monétisé le momentum (2 TP), corrige la lecture 17h
- **Fait neuf (corrige le 17h "la seule monétisation décisive est une PERTE")** : les 2 fills OPEN au 17h ont clôturé GAGNANTS sur TP. GOLD a trendé ~4090→3959.97 (−3.2 %, SHORT confirmé : Silver −6.7 %, forecast 15m/1h/4h négatifs). **3 fills décisifs** : 15:42 entry 4009.01→stop 4025.3 = **−0.406 %** ; 15:51 entry 4026.51→TP 3997.22 = **+0.727 %** (RR 1.85) ; 17:19 entry 4009.80→TP 3965.00 = **+1.117 %** (RR **2.83**). Somme +1.438 %, moy +0.48 %/trade, **2 TP/3 dont une RR 2.83**.
- **Ce que ça tranche (LIVE n=3)** : (1) thèse "OTE ne monétise jamais le momentum" = FAUX cet ap-m/soir ; (2) "TP trop loin" = spécifique au RÉGIME HACHÉ, sur un vrai trend-day la TP RR 2.83 est touchée (confirme reframe chercheur 23/06) ; (3) entrée-marché et OTE sont COMPLÉMENTAIRES : market-entry aurait capté la dérive sens-unique du MATIN (7 no-fills), l'OTE a capté la continuation à retracements de l'ap-m. → AJOUTER l'entrée-marché, pas remplacer l'OTE.
- **Tension métrique** : ai_expired_nofill 29→34, ai_fill_rate 23.7→22.7 % (soir : 18:13 GOLD, 18:40/18:51 US500 EXPIRED). Le fill-rate brut baisse MAIS les fills réalisés sont fortement rentables → fill-rate à pondérer par l'espérance/fill, pas lu seul.
- **Soir** : GOLD rebond 3959→~4000 (mean-rev post −3.2 %) ; US500 NO_TRADE toute la journée (HACHÉ, 0 fill) ; veto OVERNIGHT → NO_TRADE 2 actifs. Risk-off 6e jour (VIX 19.5, F&G 17).
- **Hypothèses : 0** (lake byte-stable 07:00, 1h/1d, pas de 15m ; 11 familles KILLED ; entrée-marché injugeable sans 15m + famille pas approuvée). **Verdict** : Lab 45/44/0/0, reco promo NON, prod GELÉE.

## 2026-06-24 nuit (chercheur nocturne), l'ADX-à-l'entrée ne sépare PAS gagnants/perdants OTE
- **Re-vérif surface** : lake byte-stable 07:00 (1h/1d, **pas de 15m**), 11 familles registry == `strategy_families.FAMILIES`, **toutes KILLED** (44 verdicts + 1 sentinel `TEST_JUDGE_pass` synthétique exclu par `lab_counters`). `lab_counters()` = **45/44/0/0**. Santé OK : resim equity x20 1407.31€ (== events, pas de dérive), feature_store **3795/500 0 MIXED 0 ERROR**. Aucune injection (token `'edit '` du calendrier = "Credit Card Spending", bénin).
- **Mining descriptif (journal complet, feed CFD ≠ lake, PAS un verdict-juge)** : sur les **21 fills CLOSED IA** (OTE_RETRACEMENT), 12 WIN / 6 LOSS / 3 FLAT. Parmi les 13 décisifs avec ADX-à-l'entrée enregistré : **ADX ne discrimine pas** : WIN médiane ADX 32.7 vs LOSS médiane **36.05** (les pertes sont si possible à ADX *plus haut* : pertes à 47.0 et 52.1). ADX<25 (haché) WR 2/3 ; ADX≥25 (trend) WR 7/10, pas de séparation nette.
- **Le vrai discriminateur est le MFE réalisé** (tautologique avec l'issue) : **MFE≥0.5 % → 6/6 gagnants ; MFE<0.5 % → 3/7**. Les perdants se définissent par "à peine bougé en faveur (MFE 0.0/0.07/0.11/0.21) puis retournement", confirme la bimodalité du chercheur 23/06.
- **Ce que ça TEMPÈRE** : le narratif analyste n=3 "trend-day → l'OTE gagne" est juste *ex post*, mais le **label de régime disponible À L'ENTRÉE (ADX) ne prédit pas la qualité du fill**. On ne peut pas gater l'entrée sur l'ADX. → argument pour conditionner une future `momentum_trend_invalidation` sur **l'alignement forecast multi-TF** (instinct analyste correct) PLUTÔT que sur le label ADX. Caveats : n=13, feed CFD, MFE/issue tautologique, descriptif.
- **Hypothèses : 0** (surface byte-identique → re-soumission = DUPLICATE, re-knob = data-mining interdit, sign-flip interdit ; pooled-COT bloqué par `simulate` qui appelle `ctx_fn(ts)` sans `asset` = fix dans harness.py protégé). **Verdict** : Lab 45/44/0/0, reco promo NON, prod GELÉE.

## 2026-06-25 09h, Analyst (nuit+matin RANGE bilatéral, 0 trade ; breakout multi-TF bloqué par l'API famille, pas que le 15m)
- **Santé VERTE 6/6** : watcher cycle 08:57 ; feature_store **3977/500** (+189 vs 23h), 0 MIXED/0 ERROR, 624 setups, ret_4h OK ; resim equity x20 1407.31€ (== events, pas de dérive) ; journal 156 sig WR 58.4% exp +0.062%, 0 open (last_updated 24/06 19:40, aucun trade overnight = veto OVERNIGHT) ; prime_watcher.log 1.08 MB 0 error ; Telegram 1 msg (briefing 09:00) 0 ok:false. Lab 45/44/0/0. Injection : token bénin « Cr**edit** Card Spending » (pas un ordre).
- **Autopsie** : fenêtre 23:03→08:57 (219 cycles) = **0 A_SETUP, 0 fill, 0 trigger** ; 2 GOLD WATCH SHORT (05:18/08:02) jamais promus. **GOLD ~3978** (rebond 3959.97→~4000 puis re-dérive, forecast 4h −0.77 SHORT mais prix DANS la value area POC 3984.83/VAL 3965.75 → pas de cassure) ; **US500 ~7409** RANGE (15m/1h +0.3/+0.4 LONG mais 4h plat → pas d'alignement multi-TF). RANGE bilatéral → le bot n'a RIEN pris = comportement voulu (coût faux signal > espérance en range), pas une faille. Métriques fill inchangées (expired_nofill 34, fill_rate 22.7 %).
- **Catalyseur du jour (à autopsier 13h/17h)** : Core PCE m/m **14:30 Paris** (f 0.3 % vs p 0.2 %, High USD) + Final GDP q/q, jauge Fed, potentiel trend-maker. Question ouverte : l'OTE fille-t-elle la cassure post-PCE ou la rate comme le matin du 24/06 ? Risk-off 7e jour : F&G **12** (↓ vs 17, stress s'approfondit), gold_bias +7 / spx_bias −7.
- **Constat code neuf (affine le backlog)** : la confluence breakout multi-TF (chercheur 24/06) **n'est pas bloquée QUE par le lake 15m** : la famille `momentum_breakout` **ignore `ctx`** (`strategy_families.py:351`, `fn(window, ctx=None)` ne lit que `window`), alors que le harness câble bien `ctx_fn(ts)→signal_fn(window, ctx)` (`harness.py:146`). Le breakout 1h gaté par la tendance 1d (calculable sur lake 1h+1d EXISTANT, sans 15m) exige donc une famille **ctx-aware** → spec `momentum_breakout_htf` posée dans le rapport (token Sam). Breakout déjà KILLED 6× en inconditionnel (gated ER/ADX + Donchian no-gate).
- **Hypothèses : 0** (lake byte-stable 07:00 1h/1d sans 15m ; 11 familles KILLED ; breakout multi-TF injugeable tant que la famille ne lit pas `ctx`). **Verdict** : Lab 45/44/0/0, reco promo NON, prod GELÉE.

## 2026-06-25 13h, Analyst (midday RANGE, GOLD en COIL pré-PCE : alignement multi-TF qui se forme)
- **Santé VERTE 6/6** : watcher cycle 12:58 ; feature_store **4065/500** (+88 vs 09h), 0 MIXED/0 ERROR, 626 setups, ret_4h OK ; resim equity x20 1407.31€ (== events, pas de dérive) ; journal 156 sig WR 58.4% exp +0.062%, 0 open (last_updated 24/06 19:40) ; datafeed tradingview tous flux ; Telegram 3 msg (briefings 09:00/12:00 + analyst 09h) 0 ok:false. Lab 45/44/0/0. `ai_expired_nofill` 34 / `ai_fill_rate` 22.7 % inchangés (0 fill/expiry depuis hier soir). Injection : token bénin « Cr**edit** Card Spending » (pas un ordre).
- **Autopsie** : 09h→13h = **0 A_SETUP, 0 fill, 0 trigger** (143 cycles). **Fait neuf GOLD ~3982** : pour la 1re fois today le forecast est **3/3 SHORT-aligné** (15m −0.32 / 1h −0.09 / 4h −0.70 ; le 15m s'est retourné dans le sens du 4h depuis 09h) ET `recent_delta` fortement négatif (−65k/−83k), **POURTANT label RANGE ⚪ + prix collé au POC 3984 (DANS la value area, VAL 3973.86 non touché)** = **dérive vendeuse absorbée sans cassure = coiling pré-catalyseur**. NO_TRADE justifié (déclencheur VAL non donné). **US500 ~7414** : RANGE→TRANSITION 🟡 mais forecast conflictuel (15m −0.16 / 1h +0.245 / 4h −0.13) = NEUTRAL, aucun alignement → NO_TRADE.
- **Catalyseur imminent (post-session)** : Core PCE m/m **14:30 Paris** (f 0.3 % vs p 0.2 %, High USD, `actual:null` confirmé non publié) + Final GDP q/q 1.6 %. Potentiel trend-maker. **Cas-test live du backlog n°2** : si le PCE résout le coil par une jambe SHORT, l'OTE_RETRACEMENT fillera-t-elle la cassure ou la ratera-t-elle comme le matin du 24/06 ? → à autopsier au 17h avec l'`actual`. Risk-off 7e jour (F&G 12, gold_bias +9 / spx_bias −8).
- **Hypothèses : 0** (lake byte-stable 07:00 1h/1d sans 15m, surface identique au 09h → re-soumission = DUPLICATE, re-knob = data-mining interdit, sign-flip interdit ; spec `momentum_breakout_htf` déjà posée au 09h, attend token Sam, non re-posée). **Verdict** : Lab 45/44/0/0, reco promo NON, prod GELÉE.

## 2026-06-25 17h, Analyst (post-PCE, le coil a résolu À LA HAUSSE : thèse SHORT du 13h falsifiée)
- **Santé VERTE 6/6** : watcher cycle 17:00 ; feature_store **4151/500** (+86 vs 13h), 0 MIXED/0 ERROR, 627 setups, ret_4h OK ; resim equity x20 1407.31€ (== events, 0 dérive) ; journal 156 sig WR 58.4% 0 open (last_updated 24/06 19:40, 0 trade neuf) ; Lab 45/44/0/0 ; Telegram 10 msg today 0 ok:false ; watchdog.log 0 o, prime_watcher.log 1.1 Mo 0 error. `ai_expired_nofill` 34 / `ai_fill_rate` 22.7% inchangés. Injection token bénin « Credit Card Spending ».
- **Autopsie** : 187 cycles, **0 A_SETUP / 0 fill / 0 trigger**, 6 WATCH non promus. **FAIT NEUF** : le cas-test live posé au 13h a tranché, au 13h GOLD coilait à 3984 forecast **3/3 SHORT-aligné**, j'avais demandé si le PCE résoudrait le coil par une jambe SHORT fillable. **Réalité : résolution À LA HAUSSE** : GOLD 3984 (13h) → max 4033 (briefing 15:30 : 4026 +0.87%, Silver +1.76%) → 4011 (17h). VAL 3973 effleuré (low 3967.99) mais cassure durable UP au-dessus de VAH 4008. Forecast SHORT du 13h **wrong-footé** → **NO_TRADE correct = victoire défensive**. US500 dérive baissière hachée 7412→low 7323→7377 (~−0.5%), forecast SHORT-aligné, 0 setup. PCE `actual` toujours null dans le cache mais prix = vérité-terrain (gold+/spx−/USD faible = dovish/refuge). Risk-off 7e jour (F&G 12).
- **Mise en garde backlog n°2** : le lake GC_F 1d ferme 4181.9→4129.9→3990.3→~4008 = tendance 1d **DOWN** au début du 25/06. Un gate `momentum_breakout_htf` « breakout dans le sens de la tendance 1d » aurait autorisé SHORT / bloqué LONG = mauvais côté de la résolution UP. **Le gate 1d lagge le retournement 24→25.** Ne tue pas la spec (injugeable, famille inexistante, token Sam) mais documente son talon d'Achille, à éprouver par le juge, pas présumer gagnant.
- **Hypothèses : 0** (lake byte-stable 07:00 1h/1d sans 15m, 11 familles toutes KILLED, re-soumission=DUPLICATE, re-knob/sign-flip interdits ; spec breakout_htf déjà posée 09h). **Verdict** : Lab 45/44/0/0, reco promo NON, prod GELÉE.

## 2026-06-25 nuit (chercheur nocturne), la TP n'est PAS le goulot côté pertes : les LOSS sont des réversions immédiates
- **Re-vérif surface** : lake byte-stable **2026-06-25 07:00** (1h/1d, **toujours pas de 15m**), 11 familles registry == `strategy_families.FAMILIES`, **toutes KILLED**. `lab_counters()` = **45/44/0/0**. Santé OK : resim equity x20 **1407.31 €** (== baseline, 0 dérive), feature_store **4288/500 · 0 ERROR · 1 MIXED exclu**, journal 157 sig (+1 vs nuit dernière). Aucune injection (calendar/news : 0 token impératif ; « Credit Card Spending » bénin).
- **Autopsie position live US500 SHORT (le trade que l'analyste 23h demandait de suivre)** : `AI_US500_1782407233`, entry 7369.09 fillé 19:15 Paris, stop 7394.81, TP1 7322.3 (RR 1.82). À 23:30 Paris (dernier intrabar 21:30 UTC) **TOUJOURS OPEN ~flat** : MFE +0.38 % (low 7341.1, **TP1 à −0.635 % NON atteint, manque ~0.25 pt-%**), MAE −0.27 % (high 7389.3, stop NON touché), `fill_quality=PARTIAL`. Ni TP ni stop ⇒ candidat **WIN_TIME** (sortie horizon ~flat-positif), pas une perte.
- **Mining non-redondant (TP-distance, backlog n°3 ; ≠ ADX du 24/06)** : sur les **16 fills CLOSED IA dé-dupliqués par (asset, entry)** : re-émissions du même setup collapsées, ex. 7 lignes US500 entry 7510.33 → 1, **9 WIN / 4 LOSS / 3 WIN_TIME**. Séparation **nette à MFE ≈ 0.5 %** :

| Bucket | n | MFE réalisé | TP-distance posée | Lecture |
|---|---|---|---|---|
| **LOSS** | 4 | **0.03-0.20 %** (méd 0.11) | 0.63-1.11 % | réversion immédiate, MFE **sous la TP la plus serrée** |
| **WIN** | 9 | 0.56-2.41 % (méd ~0.78) | 0.38-1.40 % | TP atteinte |
| **WIN_TIME** | 3 | 0.60-2.06 % | 0.63-2.11 % | 2 near-miss à <0.04 % de leur propre TP |

- **Ce que ça tranche (descriptif, feed CFD ≠ lake, PAS un verdict-juge)** : côté PERTES, **la distance de TP n'est pas le goulot** : les 4 LOSS ont un MFE max 0.20 %, soit **sous la TP la plus serrée jamais posée (0.63 %)** : aucune TP plus proche ne les convertit, elles **se retournent avant de bouger** (MAE −0.38/−0.54 %) = **échec de qualité d'ENTRÉE, pas de gestion TP**. Côté WIN_TIME, resserrer la TP ne capte que des gains marginaux (near-miss ~0.6-0.7 %) = second ordre. ⇒ **backlog n°3 « placement TP par régime » reste DÉPRIORISÉ** ; le levier est à l'entrée (éviter les fills à réversion immédiate) = **backlog n°2 (entrée-marché / alignement forecast multi-TF)**. Confirme la bimodalité (23/06) et complète le mining ADX (24/06 : l'ADX ne gate pas), **même racine : le discriminateur est le momentum POST-entrée, pas un paramètre de gestion**. *Caveats : n=16 (4 LOSS seulement), feed CFD, MFE/issue tautologique, descriptif → cadre les specs, ne valide rien.*
- **Hypothèses : 0** (surface byte-identique → re-soumission = DUPLICATE ; re-knob = data-mining interdit ; sign-flip interdit ; breakout gated ER/ADX déjà KILLED 6× ; `momentum_breakout_htf` ctx-aware = famille inexistante, token Sam ; placement TP = `position_policy`, **non jugeable par `harness.evaluate`** qui juge les entrées). **Verdict** : Lab 45/44/0/0, reco promo NON, prod GELÉE.

## 2026-06-26 09h, Analyst (la prod a TRADÉ la nuit : 1 WIN_TIME US500 + 1 LOSS GOLD à réversion immédiate = manuel live « le levier est à l'entrée »)
- **Santé VERTE 6/6** : watcher cycle 08:57 ; feature_store **4471/500** (+183 vs nuit), 1 MIXED exclu / 0 ERROR, 672 setups, ret_4h OK ; resim equity x20 1407.31€ (== baseline, 0 dérive) ; journal 159 sig 0 open WR 58.4% exp +0.063% ; prime_watcher.log 1.16Mo 0 error ; Telegram 6 msg today 0 ok:false. Lab 45/44/0/0. Injection : token bénin « Cr*edit* Card Spending ».
- **Autopsie, 2 fills (1re activité depuis 4 sessions)** : (1) **US500 SHORT `AI_US500_1782407233`** (carry-over 25/06) CLOSED 03:16 Paris exit 7360.9 = **+0.11% WIN_TIME** : ni TP1 (7322.3, MFE +0.38% manqué ~19pts) ni stop touchés, sortie horizon ~flat-positif → exactement la classe prédite par le chercheur 23h30. En régime HACHÉ la TP plein-R au prior-low sous-remplit (bémol backlog n°3, gestion). (2) **GOLD SHORT `AI_GOLD_1782442535`** (A_SETUP 02:55 RANGE ⚪) CLOSED 06:56 exit 4015.11 = **STOP-OUT ≈ −0.41%** : MFE +0.16% SEULEMENT puis retournement → **réversion immédiate**, MFE sous la TP la plus serrée (0.63%) → aucune TP ne le sauve = **échec d'ENTRÉE pas de gestion** (LE pattern du mining 25/06, live). SHORT GOLD pris en RANGE alors que le marché est bid (coil résolu UP 25/06) = momentum contre le flux. (3) GOLD SHORT 4008.02 EXPIRED no-fill. `ai_fill_rate` 22.7→25.5%, `ai_expired_nofill` 34→35.
- **Nuance backlog n°2 (contre-exemple au caveat 25/06 17h)** : lake GC_F 1d = 3990.3→4030.5→**4025.0** = dernière barre 1d **UP** → un gate `momentum_breakout_htf` « pas de short si 1d monte » aurait **BLOQUÉ le GOLD SHORT perdant** = miroir inverse du 25/06 (où le 1d laggait DOWN et aurait autorisé un short au mauvais moment). ES_F 1d DOWN → gate aurait autorisé le US500 WIN_TIME (neutre). **n=2, injugeable, famille inexistante (token Sam), lag 24→25 = talon d'Achille persistant.** On documente, on ne présume rien.
- **Régime 08:57** : GOLD ~4030 RANGE forecast conflictuel (15m +0.47/1h +0.35/4h −0.23, DANS value area POC 4021) → NO_TRADE validé ex-post (rebond UP post stop-out) ; US500 ~7338 HACHÉ forecast SHORT mais RR 1.12-1.62 + veto OVERNIGHT → NO_TRADE. F&G 13. **0 High-impact today** (2 Medium UoM 16:00 + Kashkari Low) → journée calme/range, peu favorable à l'OTE plein-R.
- **Hypothèses : 0** (lake byte-stable 07:00 1h/1d sans 15m, 11 familles KILLED, re-soumission=DUPLICATE, re-knob/sign-flip interdits ; breakout_htf = token Sam ; TP par régime = position_policy hors harness.evaluate). **Verdict** : Lab 45/44/0/0, reco promo NON, prod GELÉE.

## 2026-06-26 nuit (chercheur nocturne), biais 66/66 SHORT quantifié + mining MFE rafraîchi (la 1re LOSS qui casse la séparation propre) + preuve code des 2 verrous token-Sam
- **Re-vérif surface** : lake byte-stable **2026-06-26 07:00:0X** (vérifié mtime, 1h/1d, **toujours pas de 15m**). Week-end devant (samedi 27/06 marchés FERMÉS) → **pas de nouvelle surface avant lundi 29/06 07:00**. 11 familles registry == `strategy_families.FAMILIES` (`momentum, mean_reversion, session_hour, cot_extreme, momentum_regime, momentum_breakout, ichimoku ×5`), **44 KILLED + 1 sentinelle synthétique** (`TEST_JUDGE_pass`, exclue) → `lab_counters()` = **45/44/0/0** (vérifié en direct). Santé : resim equity x20 **1348.81 €** (== 23h analyst, 0 nouveau décisif ; n décisifs **12 < 15** insuffisant assumé), feature_store **4779/500 · 0 ERROR · 1 MIXED exclu**, 731 setups outcome, 7 jours order-flow, modèle gelé ; journal **162 sig** (INCHANGÉ vs 23h), **0 open / 0 pending**. Aucune injection (`news_cache` + `calendar_cache` : 0 token impératif sur le scan `ignore|exec|commit|delete|override|edit|run…`).
- **Contribution 1, biais directionnel QUANTIFIÉ (cadre, pas redondant)** : sur **TOUS les 66 signaux IA** (03/06→26/06, GOLD 34 + US500 32), **66/66 = SHORT, ZÉRO LONG jamais émis** (64 OTE_RETRACEMENT + 1 SHORT_CONTINUATION_FIB + 1 INTRADAY-SHORT-MOMENTUM). Le seul trend-day de la fenêtre (GOLD +1.5% le 26/06, clôture sur les plus-hauts) était **LONG et n'a jamais pu être tradé** : le moteur n'a structurellement aucun chemin vers un long. C'est la **caution chiffrée la plus forte** du levier backlog n°2 (`momentum_breakout_htf` ctx-aware = autoriser un long quand le 1d monte), passe le « short-biaisé » qualitatif des analystes à un **fait : 0/66**.
- **Contribution 2, mining MFE/réversion RAFRAÎCHI (n=19 dédup vs 16 au 25/06, +2 LOSS du jour ; descriptif feed CFD ≠ lake, PAS un verdict-juge)** : 19 fills CLOSED IA dé-dupliqués par (asset, entry) = **10 WIN / 6 LOSS / 3 WIN_TIME**.

| Bucket | n | MFE réalisé | Lecture |
|---|---|---|---|
| **LOSS** | 6 | **0.03-0.54 %** (méd 0.16) | réversions ; **mais la queue monte à 0.54 %** (US500 26/06) |
| **WIN** | 10 | 0.56-2.41 % (méd 1.22) | TP atteinte |
| **WIN_TIME** | 3 | 0.38-0.72 % (méd 0.60) | sorties horizon ~flat-positif |

- **Ce que ça TEMPÈRE honnêtement** : le 25/06 montrait une séparation **propre** LOSS≤0.20 % vs WIN≥0.56 % (gap 0.20→0.56). La **LOSS US500 du 26/06 13:53 (MFE 0.54 %, MAE −0.35, pnl −0.363)** est **la 1re perte à percer ce plafond** : elle a couru **+0.54 % = quasi un MFE de gagnant** avant de se retourner plein stop. Le gap discriminant s'effondre à 0.54→0.56 → **le MFE précoce n'est PLUS un séparateur propre** entre futur-gagnant et futur-perdant. **Ce qui SURVIT quand même** : les 6 LOSS ont **toutes** un MFE **sous la TP la plus serrée jamais posée (0.63 %)** → aucune TP réalistement plaçable ne convertit le **bucket** perte en gains → **le levier reste à l'ENTRÉE**, pas dans la distance de TP (backlog n°3 toujours dépriorisé). *Réserve anti-data-mining : choisir une TP à 0.50 % APRÈS avoir vu ce MFE = peeking ; n=1 ; une TP ≤0.54 % toucherait aussi les WIN_TIME (0.38-0.72) → c'est une `position_policy`, non jugeable par `harness.evaluate`. On documente, on ne prescrit pas.*
- **Contribution 3, PREUVE au niveau code des 2 verrous token-Sam (plus seulement asserté)** : (a) **breakout_htf ctx-aware** : `evaluate()` construit `signal_fn = strategy_families.build_signal(family, params)` (harness.py:239) → impossible d'injecter un signal_fn custom lisant ctx depuis une expérience ; **seule `_cot_extreme` lit `ctx`** (strategy_families.py:159, `cot_pctile`), `_momentum_breakout` accepte mais **ignore** ctx (:351). Donc gater le breakout 1h par la tendance 1d **exige** une famille modifiée = **strategy_families.py protégé = token Sam**. (b) **`ctx_fn` par actif (backlog n°4, pool COT)** : les 2 `cot_extreme` existants sont **mono-actif et sous-powered** : `HD_gold` n_eff **29**, exp −0.46 ; `HE_es` n_eff **21**, exp +0.03 ; les deux **n_eff < 30** → KILLED par manque de puissance autant que d'edge. Pooler GOLD+US500 1d (même direction contrarian, **PAS un sign-flip**) donnerait 29+21=50 raw → **seul chemin vers n_eff≥30** ; clé non-duplicate (assets diffèrent). **MAIS** `simulate` appelle `ctx_fn(float(bar[0]))` (harness.py:146) = **timestamp seul, sans asset** ; GOLD et US500 1d partagent les **mêmes timestamps quotidiens** → le ctx_fn **ne peut pas** distinguer quel `cot_pctile` rendre → pooling **impossible** sans signature `ctx_fn(ts, asset)`. **Fix = ~1 ligne dans harness.py (protégé) = token Sam.** Le verrou est mécanique, pas conceptuel.
- **Hypothèses : 0** (surface byte-identique → re-soumission = DUPLICATE ; re-knob = data-mining interdit ; sign-flip après 2 shorts perdants + GOLD clos haut = INTERDIT ; les 2 leviers éclairés ce soir = token Sam prouvé au code ; placement TP = `position_policy` hors `harness.evaluate`). **Verdict** : Lab 45/44/0/0, reco promo NON, prod GELÉE. **À autopsier lundi 29/06 09h** : le refresh lake 07:00 capte-t-il enfin la cassure GOLD (close 1d > 4025) rendant le gate 1d-UP jugeable, et le moteur sort-il du 0/66-short si le 4h GOLD bascule LONG ?

## 2026-06-27 09h (analyst, samedi week-end), le refresh 07:00 capte la cassure 1d GOLD, mais la barre est DÉGÉNÉRÉE
- **Santé VERTE 6/6** : watcher cycle 08:55 (<12min) ; feature_store **4779/500** INCHANGÉ, 731 setups, 0 ERROR / 1 MIXED exclu, ret_4h OK, 7j order-flow ; resim equity x20 **1348.81€** (== 23h/nuit, 0 dérive, n décisifs 12<15 assumé) ; journal **162 sig** INCHANGÉ 0 open/pending WR 57.8% exp +0.058% ; prime_watcher.log 1.23Mo 0 error ; watchdog 0 octet depuis 17/06 ; datafeed tradingview 0 fallback ; Telegram 1 msg (briefing week-end) 0 ok:false cohérent. Injection : news/calendar 0 token impératif.
- **FAIT NEUF (répond à moitié à la question du chercheur nocturne)** : le refresh lake **07:00 samedi** ajoute la barre `GC_F_1d` vendredi 26/06 → close **4078.70 > 4025**, séquence 1d **3990.3→4030.5→4078.70 = 2 clôtures UP**, lag lake↔live **s'effondre ~63→~10 pts** (live 4088.87). La prémisse du gate 1d-UP (backlog n°2) est désormais VISIBLE en donnée. ES_F_1d vendredi = OHLC réel close **7401.75 DOWN** → divergence : gate autoriserait long GOLD / bloquerait long US500.
- **MAIS la barre 1d GOLD est DÉGÉNÉRÉE** : O=H=L=C=4078.70, **volume 2724 recopié de jeudi** = single-print plat, zéro amplitude intraday. Contraste ES_F_1d a une vraie amplitude (7459.5/7357.25). → la « cassure 1d » GOLD est un **instantané de close, pas une séance réglée** : la close (4078.70) est exploitable, mais le **high/low/volume de la barre fraîche = bruit**. Le talon d'Achille du 1d ne disparaît pas, il **MUTE : de lag (vendredi) à dégénérescence de barre fraîche (ce matin)**. Un gate breakout qui lirait le RANGE 1d serait nourri d'une bougie plate sur GOLD au pire moment → exiger qu'il lise la **close 1d**. On documente, on ne présume rien avant le refresh réglé de lundi.
- **Autopsie : RIEN** (week-end, 0 fill, journal/feature_store inchangés). Cycles sur quotes figées (GOLD 4088.87 / US500 7332.7, TRANSITION 🟡, forecast GOLD 15m+0.48/1h+0.53/**4h −0.41** = confluence multi-TF toujours absente). Verdict vendredi tient : moteur short-biaisé (0/66 long), GOLD trend-day LONG jamais tradé.
- **Hypothèses : 0** (surface +1 barre 1d dégénérée ≠ test neuf → re-soumission DUPLICATE ; 15m absent ; 11 familles KILLED ; re-knob/sign-flip interdits ; 2 leviers = token Sam prouvés au code ; TP par régime hors harness ; week-end → pas de surface tradeable avant lundi 07:00). **Verdict** : Lab 45/44/0/0, reco promo NON, prod GELÉE. **À autopsier lundi 09h** : le refresh réglé remplace-t-il la barre plate par une vraie OHLC (cassure confirmée vs artefact) ? GOLD continue/réverse ? le 4h bascule-t-il LONG (sortie du 0/66-short) ?

## 2026-06-27 13h (analyst, samedi week-end), RIEN à autopsier (0 fill) ; le 4h GOLD reste −0.41 (le moteur ne sort pas du 0/66-short) ; volume-recopie bilatérale = artefact systématique du refresh
- **Santé VERTE 6/6** (tout == 09h) : watcher cycle 12:56 (<12 min) ; feature_store **4779/500** INCHANGÉ, 731 setups, 0 ERROR/1 MIXED, ret_4h OK, 7 j ; resim equity x20 **1348.81€** (0 dérive, n décisifs 12<15) ; journal **162 sig** INCHANGÉ 0 open/pending WR 57.8% exp +0.058% ; prime_watcher.log 1.24Mo 0 error ; watchdog 0 octet depuis 17/06 ; datafeed tradingview 0 fallback ; Telegram 3 msg today 0 ok:false (l'unique ok:false de l'outbox date du 21/06). Injection : news/calendar 0 token impératif. Lab 45/44/0/0.
- **Autopsie : RIEN** (week-end, 0 fill, journal/feature_store byte-identiques). Cycles 12:51/12:56 sur quotes FIGÉES (GOLD 4088.87 TRANSITION 🟡 forecast 15m+0.48/1h+0.53/**4h −0.41** recent_delta +40430 acheteur ; US500 7332.7 TRANSITION 🟡 forecast 15m−0.58/1h−0.29/**4h −0.77** recent_delta +579 ≈plat), les 2 NO_TRADE.
- **Réponse 13h à la question du chercheur nocturne** (« le 4h GOLD bascule-t-il LONG → sortie du 0/66-short ? ») : **NON.** Sur un week-end entier de quotes figées, le 4h GOLD reste **−0.41** (== 09h) alors que le live 4088 est AU-DESSUS de la close 1d 4078.70 et que 15m/1h sont positifs. Le non-événement EST un résultat : **le laggard est le forecast 4h lui-même** → re-cadre backlog n°2 (gate HTF plus rapide = `momentum_breakout_htf` ctx-aware, token Sam). Pas une hyp neuve, une confirmation.
- **Précision sur la barre 1d dégénérée (affine 09h)** : GC_F_1d vendredi O=H=L=C=**4078.70** vol 2724 (FLAT, single-print) ; ES_F_1d vendredi 7431/7459.5/7357.25/**7401.75** vol 1670252 (vraie amplitude, close DOWN). Séquence close GOLD 1d 3990.3→4030.5→4078.70 = 2 clôtures UP (confirmé). **Détail neuf** : le **volume de la barre fraîche est recopié de la barre précédente sur LES DEUX actifs** (GC 2724==2724, ES 1670252==1670252) → recopie volume = **artefact SYSTÉMATIQUE du refresh 07:00**, pas spécifique GOLD. Propre à GOLD = l'**OHLC flat**. ⇒ close 1d exploitable, high/low GOLD + volume des deux = bruit ; un gate breakout doit lire la **close 1d**. Talon d'Achille 1d a muté (lag → bougie plate + volume recopié), pas disparu. Injugeable jusqu'au refresh réglé lundi.
- **Hypothèses : 0** (surface byte-stable depuis 07:00, 15m absent, 11 familles KILLED, re-soumission DUPLICATE, re-knob/sign-flip interdits, 2 leviers = token Sam prouvés au code, TP par régime hors harness, week-end → pas de surface tradeable avant lundi 07:00, 0 fill → 0 test harness). **Verdict** : Lab 45/44/0/0, reco promo NON, prod GELÉE.

## 2026-06-27 17h (analyst, samedi week-end), RIEN à autopsier (0 fill, 3ᵉ lecture figée) ; le 4h GOLD reste −0.41 pour la 3ᵉ fois ; recent_delta passe à None (order-flow gelé)
- **Santé VERTE 6/6** (tout == 09h/13h) : watcher cycle 16:58 (<12 min, 189 cycles aujourd'hui) ; feature_store **4779/500** INCHANGÉ, 731 setups, 0 ERROR/1 MIXED, ret_4h OK, 7 j ; resim equity x20 **1348.81€** (0 dérive, n décisifs 12<15) ; journal **162 sig** INCHANGÉ (last_updated 26/06 14:10) 0 open/pending WR 57.8% exp +0.058% ; prime_watcher.log 1.26Mo (+0.02 cycling) 0 error ; watchdog 0 octet depuis 17/06 ; datafeed tradingview 0 fallback ; Telegram 5 msg today 0 ok:false (l'unique ok:false outbox date du 21/06). Injection news/calendar 0 token impératif. Lab 45/44/0/0.
- **Note audit** : `test_skeptic_scope.py` non-suivi en RACINE (hors research/), script d'analyse de scope GOLD+US500 sur user_trades, antérieur à la session, inoffensif mais mal placé → signalé à Sam (déplacer dans research/ ou supprimer) ; je n'y touche pas (hors périmètre), non committé.
- **Autopsie : RIEN** (week-end, 0 fill, journal/feature_store byte-identiques). Cycles 16:53/16:58 sur quotes FIGÉES strictement == 13h (GOLD 4088.87 TRANSITION 🟡 forecast 15m+0.48/1h+0.53/**4h −0.41** ; US500 7332.7 TRANSITION 🟡 forecast 15m−0.58/1h−0.29/**4h −0.77**), les 2 NO_TRADE. **recent_delta = None** au dernier cycle = order-flow cesse d'actualiser week-end gelé (cohérent, pas un bug : pas de tape marchés fermés).
- **Réponse 17h (3ᵉ lecture)** à « le 4h GOLD bascule-t-il LONG → sortie du 0/66-short ? » : **NON, 3ᵉ fois consécutive.** Le 4h GOLD reste **−0.41** (== 09h == 13h) malgré live 4088 > close 1d 4078.70 et 15m/1h positifs. Le laggard EST le forecast 4h lui-même → re-cadre backlog n°2 (gate HTF plus rapide = momentum_breakout_htf ctx-aware, token Sam). Confirmation, pas hyp neuve.
- **Hypothèses : 0** (surface byte-stable depuis 07:00, 15m absent, barre 1d dégénérée ≠ test neuf=DUPLICATE, 11 familles KILLED, re-knob/sign-flip interdits, 2 leviers = token Sam prouvés au code, TP par régime hors harness, week-end → pas de surface tradeable avant lundi 07:00, 0 fill → 0 test harness). **Verdict** : Lab 45/44/0/0, reco promo NON, prod GELÉE. **À autopsier 23h / lundi 09h** : refresh réglé 07:00 lundi remplace-t-il la barre plate par une vraie OHLC ? GOLD continue/réverse le gain week-end ? le 4h bascule-t-il LONG = sortie du 0/66-short ?

## 2026-06-27, CHERCHEUR NOCTURNE (samedi→dimanche week-end), mining du dataset USER élargi par l'import CSV (n=180) : breakeven, AUCUNE structure conditionnable ne survit à un IC
- **Contexte** : depuis le 23h analyst, l'import CSV a porté la référence USER (fills réels Revolut) de **78 → 180 CLOSED** (09/06→26/06 ; le mining couvre 19/05→26/06). Lake byte-stable depuis 07:00 (1h/1d, **toujours pas de 15m**), week-end → **0 surface tradeable avant lundi 29/06 07:00**. AI **66/66 SHORT** inchangé (import = 0 AI, 0 fill 27/06). Injection news/calendar = 0 token impératif. Lab 45/44/0/0, 11 familles registry == `strategy_families.FAMILIES` (re-vérifié en direct ce run).
- **Mine du protocole §3 sur n=180 (descriptif feed réel, PAS un verdict-juge ; ICs Wilson/bootstrap partout)** : GLOBAL WR **56.7 %** [49.4-63.7], **meanpnl +0.002 %** CI[−0.049,+0.053] = **discrétionnaire de Sam strictement breakeven net** sur un échantillon 2,3× plus grand. Décomposition, **AUCUN sous-groupe ne sort son IC de zéro** :
  - par actif : GOLD n=137 (56.2 %, −0.002 %), US500 n=36 (58.3 %, +0.029 %), reste n≤2 (bruit).
  - par direction : **SHORT n=114 (59.6 %, +0.027 %) vs LONG n=66 (51.5 %, −0.041 %)** : les deux CI straddle 0.
  - par stratégie : SCALP_CFD n=102 (+0.005 %), HISTORIQUE_IMPORT n=57 (+0.005 %), SCALP_REBOND n=20 (−0.007 %), tous CI⊃0.
  - séquentiel : after_WIN n=97 (58.8 %, −0.021 %) vs after_LOSS n=75 (53.3 %, +0.037 %) = **pas de tilt revanche/discipline** significatif.
- **FAIT NEUF #1 (limite dure de l'import)** : les lignes importées **ne portent PAS les champs de régime** : `adx` manquant/zéro sur **180/180**, `vix`/`dxy` idem, `session='REAL'` sur 180/180, `mfe_pct` non-None sur **1/180**. ⇒ la « donnée neuve » **ne peut PAS être conditionnée à un régime/session** (le cœur même de la conditionnalité-de-régime du protocole) ni minée en MFE. L'import grossit l'échantillon **mais n'ajoute aucun axe de conditionnement** : il confirme le breakeven, il n'ouvre aucune hypothèse régime-conditionnée.
- **FAIT NEUF #2 (affine backlog n°2, le 0/66-short)** : le **même humain, sur les mêmes instruments, a pris 66 LONGs** (51.5 % WR, −0.041 %) là où le moteur IA a émis **0 long / 66 short**. ⇒ le 0/66-AI-short est un **artefact du MOTEUR, pas une propriété du marché** (les longs sont prenables et l'ont été). Ça **renforce** « le moteur n'a aucun chemin vers le long » comme **lacune structurelle** (backlog n°2 = `momentum_breakout_htf` ctx-aware, token Sam) ; **mais ça TEMPÈRE** toute présomption que le long gaté serait gagnant : les 66 longs humains sont **breakeven négatif (−0.041 %)**, pas un edge. Le gate 1d-UP reste à **éprouver par le juge**, pas à présumer gagnant, cohérent avec le caveat lag/dégénérescence-1d des analystes.
- **Hypothèses : 0** (discipliné). Le mining est **descriptif sur feed production CFD ≠ lake** → nourrit specs/backlog, **n'ouvre AUCUN test `harness.evaluate`** (qui juge des familles de signaux sur le lake, pas les fills discrétionnaires). Surface lake byte-identique → re-soumission = DUPLICATE ; re-knob = data-mining ; sign-flip INTERDIT (les 66 shorts humains à +0.027 % ne « prouvent » pas un long perdant, ni l'inverse) ; 2 leviers riches = token Sam prouvés au code (analyste 26/06). **Verdict : Lab 45/44/0/0, reco promo NON, prod GELÉE.**
- **À autopsier lundi 29/06 09h** : (a) refresh **réglé** 07:00 remplace-t-il la barre GC_F_1d plate (O=H=L=C 4078.70, vol recopié) par une vraie OHLC = cassure confirmée vs artefact ? (b) GOLD continue/réverse le gain week-end ? (c) le **4h GOLD bascule-t-il LONG** = 1re sortie du 0/66-short ? (d) si Sam tranche l'import (garder/revert backup) : re-mesurer si les rows ré-importées portent enfin adx/vix/session (sinon le mine reste non-conditionnable).

## 2026-06-28 17h (analyst, dimanche week-end), RIEN à autopsier (0 fill) ; 1re entrée autopsy du jour ; le 4h est le SEUL composant byte-constant (15m/1h toggle entre 2 états, 4h figé) → laggard 4h renforcé
- **Santé VERTE 6/6** : watcher cycle **16:57** (<12 min, **186 cycles** aujourd'hui, duration ~21 s) ; feature_store **4779/500** INCHANGÉ (731 setups, 0 ERROR/1 MIXED, ret_4h OK, 7 j order-flow) ; resim equity x20 **1348.81€** (0 dérive, 12 décisifs<15, exp +0.277% [0.039-0.49]) ; prime_watcher.log **1.327 Mo** (+0.01 cycling) 0 error ; datafeed **tradingview** 4/4 streams 0 fallback ; Telegram **7 msg today** 0 ok:false (unique ok:false outbox = 21/06). Injection news/calendar **0 token impératif**. Lab **45/44/0/0** (déflation test n°46, z requis 3.07).
- **Autopsie : RIEN** (week-end, 0 fill, journal/feature_store byte-identiques). **FAIT NEUF 17h, la surface n'est PAS strictement byte-figée** : sur les 186 cycles du jour, les forecasts prennent **exactement 2 états discrets** par actif (prix byte-figé 4088.87/7332.7), GOLD ∈ {15m+0.33/1h+0.38, 15m+0.48/1h+0.53}, US500 ∈ {15m−0.58/1h−0.29, 15m−0.43/1h−0.14}. **Le 4h est le SEUL composant BYTE-CONSTANT toute la journée** (GOLD **−0.413**, US500 **−0.767**). Le toggle 15m/1h = recompute moteur sur candles cachées (2 fenêtres), pas un mouvement de marché (close fermé). Les 2 actifs restent TRANSITION 🟡 / NO_TRADE dans les deux états.
- **Réponse 17h** à « le 4h GOLD bascule-t-il LONG ? » : **NON** : et le 17h le durcit : le 4h GOLD n'est pas seulement figé à −0.41, il est le **point fixe** de toute la surface du jour pendant que le reste oscille. Le laggard structurel **EST** le gate 4h lui-même (live 4088 > close 1d 4078.70, 15m/1h positifs dans un des 2 états, 4h refuse). Re-cadre backlog n°2 (`momentum_breakout_htf` ctx-aware, token Sam). Confirmation, pas hyp neuve.
- **Hypothèses : 0** (surface toggle entre 2 états déjà vus = pas de surface tradeable NEUVE → re-soumission DUPLICATE ; 15m lake absent ; 11 familles KILLED ; re-knob/sign-flip interdits ; import USER non-conditionnable faute champs régime ; 2 leviers = token Sam prouvés au code ; TP par régime hors harness ; dimanche → pas de surface tradeable avant lundi 29/06 07:00 ; 0 fill → 0 test harness ouvert). **Verdict : Lab 45/44/0/0, reco promo NON, prod GELÉE.**
- **À autopsier 23h / lundi 09h** : (a) refresh **réglé** 07:00 lundi remplace-t-il la barre GC_F_1d plate (O=H=L=C 4078.70) par une vraie OHLC = cassure confirmée vs artefact ? (b) GOLD continue/réverse le gain week-end ? (c) le **4h GOLD bascule-t-il enfin LONG** = 1re sortie du 0/66-short ? (d) **nouveau muet** cette nuit (pattern ~3-4 j → risque vers 01-02/07 ; `powercfg /lastwake` à relever si oui).

### 2026-06-28 23h (evening, bilan dimanche, marché fermé)
- **Santé VERTE 6/6** : watcher cycle **22:57** (<12 min, **253 cycles** aujourd'hui, duration ~18-23 s) ; continuité PARFAITE depuis le muet 04:24 (seul gap >12 min du jour = **26.3 min @03:58**, déjà root-causé veille OS, AUCUN nouveau muet entre 17h et 23h) ; feature_store **4779/500** INCHANGÉ (731 setups, 0 ERROR, ret_4h OK, 7 j order-flow) ; resim equity x20 **1348.81€** (0 dérive, 12 décisifs<15, exp +0.277% [0.039-0.49]) ; USER n=180 WR 56.7% exp +0.002% ; prime_watcher.log **1.344 Mo** (+0.017 vs 17h = cycling normal) **0 error** ; datafeed **tradingview** 4/4 0 fallback ; Telegram **11 msg today** 0 ok:false. Injection news/calendar **0 token impératif**. Lab **45/44/0/0** (déflation test n°46, z requis 3.07).
- **Autopsie : RIEN de neuf** (week-end, 0 fill). Le **FAIT NEUF du 17h est CONFIRMÉ sur le JOUR COMPLET** (253 cycles vs 186 à 17h) : prix byte-figés (GOLD 4088.87 ×253, US500 7332.7 ×253), forecasts en **exactement 2 états discrets** par actif, GOLD {(15m+0.48/1h+0.53)×137, (15m+0.33/1h+0.38)×116}, US500 {(15m−0.58/1h−0.29)×205, (15m−0.43/1h−0.14)×48}. **4h BYTE-CONSTANT toute la journée** : GOLD **−0.413** ×253, US500 **−0.767** ×253. Le 4h est l'**unique point fixe** de la surface ; laggard structurel = le gate 4h lui-même. Confirmation sur N complet, pas hyp neuve.
- **Hypothèses : 0** (surface toggle 2 états déjà vus = pas de surface tradeable NEUVE → DUPLICATE ; 15m lake absent ; 11 familles KILLED ; re-knob/sign-flip interdits ; import USER non-conditionnable ; 2 leviers token Sam ; dimanche → pas de surface tradeable avant lundi 29/06 07:00 ; 0 fill → 0 test harness ouvert). **Verdict : Lab 45/44/0/0, reco promo NON, prod GELÉE.**
- **À autopsier lundi 29/06 09h** : (a) refresh 07:00 lundi remplace-t-il la barre GC_F_1d plate (O=H=L=C 4078.70) par une vraie OHLC ? (b) GOLD continue/réverse le gain week-end (live 4088.87 > close 1d 4078.70) ? (c) le **4h GOLD bascule-t-il enfin LONG** = 1re sortie du moteur hors 0/66-short ? (d) **nouveau muet** cette nuit (pattern ~3-4 j, dernier 04:24 le 28/06 → prochain risque ~01-02/07 ; `powercfg /lastwake` à relever si oui).

## 2026-06-28, CHERCHEUR NOCTURNE (dimanche→lundi, week-end · marché fermé), le backlog #5 ("re-tester twist_1d sur lake épaissi") est INACTIONNABLE par le harness tel quel (dédup code-vérifié + démontré empiriquement)
- **Contexte ingestion (re-vérifié ce run)** : pas de `PAUSE`. Lab `lab_counters()` = **45/44/0/0** (déflation test n°46 → z_req ~3.07). Lake = 13 parquet mtime 07:00 ; **frontière réelle vérifiée (ts epoch→UTC)** : 1d GC_F/ES_F dernier bar = **vendredi 26/06** (OHLC RÉELLE, GC dernier 1d O4044/H4111/L3998/C4096, semaine volatile low 3963 le 24/06 → close 4096), 1h dernier bar = **26/06 20:00 UTC**. **Toujours aucun 15m.** resim USER WR 56.7% n=180 exp +0.002%, equity x20 **1348.81€** (0 dérive). feature_store 4779/500, 731 setups, 0 ERROR. journal 264 sig (USER 180/AI 66/None 18), 0 fill 28/06. Injection news/calendar **0 hit**.
- **CORRECTION DE CADRAGE** : la barre 1d "plate" O=H=L=C=4078.70 vue par les analystes ce week-end est le feed **PRODUCTION TradingView CFD** (figé week-end), **PAS le lake yfinance** (distinct, voulu). Le lake **n'est pas figé sur du Friday-19 périmé** : il porte la **semaine complète de trading** jusqu'au 26/06. "Lake byte-stable depuis 07:00" reste vrai (0 bar neuf sur le week-end, normal) mais la frontière est **courante-au-vendredi**, pas stale.
- **FAIT NEUF (structurel, code-vérifié harness.py:66-70 + 228-231)** : `hypothesis_key = sha256(family, params, sorted(assets), timeframe)[:16]`. (1) **`exit_rule` n'est PAS dans la clé** → changer stop/tp/horizon ne crée pas une hypothèse neuve (re-knob déguisé). (2) un doublon de clé retourne `{"verdict":"DUPLICATE"}` et **RETOURNE AVANT tout `_registry_append`** → le harness **ne ré-évalue JAMAIS** une cellule déjà jugée, **même si le lake a gagné des barres**.
- **COROLLAIRE, backlog #5 inactionnable** : `IL_pool_ichimoku_twist_1d` (twist pool 1d) jugé le **22/06** KILLED, **n_eff=30 PILE au seuil**, exp **+0.56%** (le "seul point estimate positif" du backlog), IC **[−0.007, 1.178]** (borne basse <0), t=1.79 ≪ z_req=3.06. Le lake 1d a depuis gagné ~4 barres/actif (frontière 22/06→26/06) = **exactement la condition du backlog #5** : mais re-soumettre la même clé = DUPLICATE, pas de nouveau verdict.
- **DÉMONSTRATION EMPIRIQUE** (`exp_2026_06_28_nocturne.py`) : re-soumission de la cellule IL (params/assets/tf identiques au verdict 22/06) → `verdict=DUPLICATE` (collision avec `IL_pool_ichimoku_twist_1d` du 2026-06-22), **lab_counters inchangé** (45/44/0/0 avant=après), **registry len inchangé** (45=45), invariant **0-effet-de-bord OK**. Le chemin DUPLICATE retourne avant l'append → **0 déflation brûlée** (re-tester ne coûte rien mais ne donne rien).
- **PROPOSITION (token Sam, harness.py protégé, je ne touche pas)** : pour rendre #5 actionnable sans ouvrir la porte au re-knob, ajouter une **empreinte de données** à `hypothesis_key` (fingerprint lake : nb barres + ts du dernier bar par actif/tf). Lake inchangé → reste DUPLICATE (bon) ; après N barres neuves → cellule distincte = re-test honnête sur donnée fraîche (family/params/exit identiques, donc pas un re-knob). Spec only.
- **Hypothèses : 0** (matrice fermée ; 2 leviers riches = token Sam derrière fichiers protégés : `momentum_breakout_htf` ctx-aware strategy_families.py:351 + pool COT via `ctx_fn(ts,asset)` harness.py:146 ; dédup bloque le re-test sur lake épaissi ; re-knob/sign-flip interdits ; import USER non-conditionnable ; 15m absent ; dimanche → 0 surface tradeable avant lundi 07:00). **Verdict : Lab 45/44/0/0, reco promo NON, prod GELÉE.**
- **À autopsier lundi 29/06 09h** : (a) refresh 07:00 lundi, vraie OHLC sur la prod ? (b) GOLD continue/réverse le gain week-end ? (c) le **4h GOLD bascule-t-il LONG** ? (d) **nouveau muet** cette nuit (pattern ~3-4 j, dernier 04:24 le 28/06 → risque ~01-02/07) ? (e) Sam tranche-t-il l'import journal.json (garder/revert) et le fingerprint-clé du backlog #5 ?

### 2026-06-29 13h (midday, lundi, séance Europe, marché ouvert)
- **Santé VERTE 6/6** : watcher cycle **12:56** (<12 min, **286 events** today, duration ~16-21 s) ; feature_store **4977/500** (vs 4889 à 09h, **+88 outcomes**, 731 setups, 0 ERROR/1 MIXED, 8 j order-flow) ; resim equity x20 **1348.81€** (0 dérive, 12 décisifs<15 exp +0.277% [0.039-0.49]) ; USER n=180 WR 56.7% exp +0.002% ; prime_watcher.log **1.384 Mo** (+0.011 vs 09h) **0 error** today ; datafeed **tradingview** 6/6 0 fallback ; Telegram **3 msg today** (briefing 09:00, Analyst 09h, briefing 12:00) 0 ok:false (unique=21/06). Injection news/calendar **0 token**. Lab **45/44/0/0** (déflation test n°46, z_req 3.07). 0 muet ce matin (risque ~04:00 non matérialisé → prochaine fenêtre ~01-02/07).
- **Autopsie, 0 fill, 0 A_SETUP, 0 WATCH (tout NO_TRADE)**. Régime du jour : GOLD 240 RANGE / 38 TRANSITION / **8 TENDANCE HACHÉE** (dernière heure) ; US500 134 RANGE / 9 TRANSITION / 0 HACHÉE.
- **FAIT NEUF 1, GOLD = mouvement directionnel du jour (baissier)** : ~4 058 (09h) → **~4 036** (12:56), −1.4% jour. Régime bascule **RANGE→TRANSITION→TENDANCE HACHÉE** en accélérant la baisse ; 4h passe −0.40→**−0.547** SHORT-aligné (15m −0.77/1h −0.50). **Confirme la nuance 09h backlog n°2** : 4h-short directionnellement CORRECT (prix descend) → le grief « gate 4h trop lent » est régime-dépendant (ne mord QUE quand prix MONTE plus vite que la bougie 4h). **MAIS TENDANCE HACHÉE = whipsaw = le PIRE régime momentum** ; scanner NO_TRADE → rester plat est défendable, évidence **CONTRE** une entrée momentum-short, pas pour une hyp.
- **FAIT NEUF 2, US500 = test live du grief n°2 en marché HAUSSIER** (question (c) du 09h) : ~7 378 (+0.64%) → **~7 396 (+0.79%)**, NASDAQ +1.34% en tête ; 15m +0.4/1h +0.20 LONG mais **4h NÉGATIF toute la matinée** (−0.013→−0.163→−0.313) → LONG gated. **Nuance décisive** : 4h près de ZÉRO (pas blocage fort), régime classé **RANGE ⚪** (pas tendance), hausse = **dérive de range** sous résistance 7 398 (pas cassure propre). → grief ne mord que sur **vraie tendance haussière rapide** ; US500 n'en fournit pas une → **ni confirmation ni réfutation, test propre toujours PENDANT**.
- **Hypothèses : 0** (mouvement du jour GOLD atterrit en HACHÉE = whipsaw, perdant attendu pour momentum ; régime live non-backtestable faute de 15m lake ; US500 = range-drift sans tendance ; 45 familles KILLED→DUPLICATE ; re-knob/sign-flip interdits ; import USER non-conditionnable ; 2 leviers neufs = token Sam : `momentum_breakout_htf` ctx-aware sf:351 + pool COT harness:146, + fingerprint-clé pour débloquer backlog #5). **Verdict : Lab 45/44/0/0, reco promo NON, prod GELÉE.**
- **À autopsier au 17h (ouverture US 15:30)** : (a) GOLD, tendance hachée se résout en TENDANCE propre (test momentum-short) ou réverse en RANGE (whipsaw confirmé) ? (b) US500, casse-t-il 7 398-7 405 en tendance haussière propre avec 4h LONG = test grandeur nature backlog n°2 en marché haussier, toujours pendant ? (c) un A_SETUP à l'ouverture US (1re occasion momentum réelle de la semaine) ? (d) feature_store reprogresse, equity stable ?

## 2026-06-29, CHERCHEUR NOCTURNE (lundi→mardi, US clôturé), FAIT NEUF de DONNÉES : la barre GOLD 1d de frontière est CORROMPUE (plate), défaut systématique GC_F_1d (55 barres) / absent ES → SECOND blocage indépendant sur le backlog #5 + correction honnête du cadrage 28/06
- **Contexte ingestion (re-vérifié ce run)** : pas de `PAUSE`. Lab `lab_counters()` = **45/44/0/0** (déflation test n°46 → z_req ~3.07). Lake = 13 parquet mtime **2026-06-29 07:00** (refresh lundi). Frontière (ts epoch→UTC) : 1d GC_F (1257)/ES_F (1258) dernier bar = **29/06 EN FORMATION**, dernière COMPLÈTE = **26/06** ; 1h dernier bar = **29/06 04:00 UTC**. **Toujours aucun 15m.** resim USER WR 56.7% n=180 exp +0.002%, equity x20 **1348.81€** (0 dérive, 12 décisifs<15). feature_store **5202/500** (+5 vs 5197 bilan 23h), 733 setups, 0 ERROR/1 MIXED, 8j order-flow. journal 264 sig (USER 180/AI 66/None 18), **0 fill 29/06**, last_updated 26/06 (artefact import, hors research/). Injection news/calendar = **0 token impératif** (4 hits "edit" = "Cr-edit" ForexFactory, bénins).
- **Décision-prod 29/06 (rien à rouvrir, 0 fill)** : chop des DEUX côtés, **0 A_SETUP / 2 WATCH** non escaladés. GOLD TENDANCE HACHÉE 🔴 (119 cyc), −1.5% via whipsaw jamais tendance propre → momentum-short perdant attendu. US500 RANGE ⚪ toute la montée (219/254), +1.2% range-drift, 4h LONG seulement à 19h (après moitié du move) → filtre ADX/ER (= HA tué 12/06) n'aurait pas pris ; entrée tardive ≈ +0.2% brut ≈ coûts. NO_TRADE défendable, « could-have » US500 le + net de la semaine **mais sous le bruit**.
- **FAIT NEUF (structurel, code+donnée-vérifié), backlog #5 DOUBLEMENT bloqué** :
  - **BLOCAGE 1 (établi 28/06, re-confirmé)** : dédup gèle le re-test. `hypothesis_key = sha256(family,params,sorted(assets),tf)[:16]` (harness.py:66-70) ; doublon → `DUPLICATE` **avant** `_registry_append` (harness.py:228-231) → jamais de ré-évaluation même si le lake gagne des barres.
  - **BLOCAGE 2 (NEUF)** : la donnée de frontière GOLD 1d est **CORROMPUE**. Après le refresh lundi 07:00, `GC_F_1d` du **26/06** n'est plus la vraie OHLC (28/06 : O4044/H4111/L3998/C4096) mais **PLATE O=H=L=C=4078.70** (== valeur figée du feed production week-end). Défaut **systématique et spécifique à l'or** : **GC_F_1d = 55 barres plates / 1257 (~4.4%)**, **ES_F_1d = 0 / 1258**. Barre plate = range vrai NUL → signal ichimoku/twist 1d dégénère (Tenkan=Kijun=close). Donc même si BLOCAGE 1 était levé, re-tester twist_1d sur le lake « épaissi » injecterait une barre GOLD corrompue à la frontière.
- **CORRECTION HONNÊTE de mon cadrage 28/06** : j'avais écrit « la barre plate 4078.70 est le feed PRODUCTION, PAS le lake (distinct) ». **Faux en partie** : le refresh lundi a fait FUIR cette valeur plate DANS le lake GC_F_1d du 26/06. Le lake n'est pas immunisé contre l'artefact plat de l'or (55 exemplaires) ; ES reste propre (0).
- **DÉMONSTRATION EMPIRIQUE** (`exp_2026_06_29_nocturne.py`) : (a) audit plat → GC_F_1d 55 plates (frontière 26/06 range=0.00 CORROMPUE), ES_F_1d 0 plates (frontière 26/06 range=102.25 réelle) ; (b) re-soumission cellule IL (key 7184c7acc424e5ef) → **verdict=DUPLICATE** (collision IL_pool_ichimoku_twist_1d du 22/06), lab_counters inchangé (45/44/0/0 avant=après), registry len 45=45, **invariant 0-effet-de-bord OK**. Les deux blocages sont **indépendants et tous deux actifs**.
- **PROPOSITIONS (token Sam, fichiers protégés, je ne touche pas)** : (1) **filtre d'intégrité à l'ingestion** : rejeter/interpoler les barres GC_F_1d plates avant tout backtest 1d ; (2) **fingerprint-clé** (déjà proposé 28/06). **À coupler** : sans #1 le re-test resterait contaminé, sans #2 il resterait DUPLICATE, il faut **les deux** pour ressusciter #5. Spec only.
- **Hypothèses : 0** (matrice fermée 44 KILLED → DUPLICATE ; journée non-backtestable faute 15m lake ; évidence du jour CONTRE momentum des 2 côtés ; re-knob/sign-flip interdits ; import USER non-conditionnable ; 2 leviers riches = token Sam prouvés au code : `momentum_breakout_htf` ctx-aware sf:351 + pool COT `ctx_fn(ts,asset)` harness:146 ; re-test 1d doublement bloqué). **Verdict : Lab 45/44/0/0, reco promo NON, prod GELÉE.**
- **À autopsier mardi 30/06 09h** : (a) la barre GC_F_1d 29/06 (forming) se complète-t-elle en vraie OHLC ou retombe-t-elle dans le défaut plat ? (b) US500 dérive haussière continue en tendance propre (ADX qualifie) ou réverte ? (c) GOLD hachée baissière résout-elle en tendance ? (d) nouveau muet cette nuit (pattern ~3-4 j, dernier 28/06 04:24 → fenêtre ~01-02/07) ? (e) Sam tranche-t-il fingerprint-clé (#3) + filtre intégrité GOLD (#2) qui, ENSEMBLE, ressusciteraient #5 ?

---

## 2026-06-30 09h (Analyst), RÉFUTATION EMPIRIQUE : momentum short en HACHÉE sous le VAL

**Le forward-test a TRADÉ et PERDU 3 fois.** Première matérialisation de fills
depuis des jours. De 05:50 à 08:24 Paris, le scanner a émis **23 cycles A_SETUP
GOLD SHORT** (5 signaux journalisés), confiance montant jusqu'à **10/10** puis
9.8/10, régime **TENDANCE HACHÉE 🔴**, forecast 4h SHORT (-0.567→-0.717).

**Chemin de prix (prévu vs réalisé) :** low 3952 (03:16) → le bot short le
rebond 3968-3999 → **high 4032.8 (08:35)**. Après le 1er short (05:50), le prix
n'est JAMAIS redescendu sous l'entrée. Tous TP (3942-3973) inatteignables, tous
stops franchis.

**Résultat (journal.json AI_SIGNAL) :** 05:50 LOSS -0.407% · 06:02 LOSS -0.406%
· 06:35 NOFILL · 07:24 NOFILL · 08:14 (score **9.8**) LOSS -0.406%. **3 fills,
3 pertes.** Le signal le plus confiant = perdant. Resim equity x20 captée :
1348.81 → 1241.11 EUR (pipeline honnête).

**MÉCANISME (fait neuf order-flow) :** **23/23** A_SETUP émis **SOUS le POC
(~4022) ET SOUS le VAL (~4002)** → le bot a fadé la valeur ; le POC a aimanté le
prix vers le haut. En range/haché, shorter sous le VAL = mauvais côté
systématique.

**POURQUOI :** régime (HACHÉE = pire pour momentum, cf. HA tué 12/06) + position
order-flow (sous valeur) + calibration confiance inversée (10/10 au pire entry).
Le 4h-momentum SHORT était FAUX ; le biais news gold_bias=+5 (haussier) était
CORRECT. Le filtre ER/ADX seul n'a pas protégé.

**SUITE :** 0 hyp testable non-duplicate (exclure HACHÉE = duplicate des 31
momentum_regime ; porte order-flow value_gate = neuve mais famille protégée +
9 j order-flow seulement → DÉCRITE pour token Sam, pas soumise). Reco promo NON.

**À autopsier 30/06 13h :** (a) GOLD continue-t-il au-dessus du POC (réversion
complète) ou re-hache-t-il ? (b) le scanner ré-émet-il des shorts perdants cet
après-midi (persistance du biais short en haché) ? (c) US500 sort-il du RANGE ?
(d) nouveaux fills AI et leur issue ?

---

## 2026-06-30 13h (Analyst), SUITE : le scanner s'est AUTO-ARRÊTÉ à la reprise de la valeur

Résolution des 4 questions ouvertes du 09h. **(a)** GOLD a réverté à la valeur :
low 3952 (03:16) → high 4032.8 (08:35) → **4030.4 (12:58) AU-DESSUS du POC
(4022.84)**, VAL 4001.68 / VAH 4052.47 → POC-aimant haussier CONFIRMÉ live.
**(b)** Le biais short n'a PAS persisté : dès la reprise du VAL (~08:30) le
scanner a CESSÉ d'émettre, dernier `AI_SIGNAL` 08:14 (le 9.8 perdant), **0
nouvel A_SETUP / 0 fill l'après-midi** (84 NO_TRADE, 13 WATCH). Auto-correction.
**(c)** US500 RANGE/TRANSITION toute la journée, **NO_TRADE 120/120**, 7430→7454
au VAH. **(d)** 0 nouveau fill ; seuls fills du jour = 3 pertes GOLD du matin.

**Leçon (renforcée 2×) :** le grief n'est PAS un filtre de régime de plus (ER/ADX
a classé HACHÉE 🔴 et a quand même sorti du 10/10) mais la **porte order-flow
`value_gate`** (décrite 09h) : le scanner a eu raison de se taire quand le prix a
repris le POC ; il lui manque de se taire AUSSI quand il fade la valeur PAR LE BAS
(short < VAL). Cette porte aurait supprimé les 5 below-VAL perdants SANS bloquer
l'après-midi correct. Convergence : kill HA (12/06) + POC-aimant + auto-arrêt.

**Bug/observation structurelle (périmètre Sam, non bloquant) :** 2 messages
Telegram « ✅ Trade capturé : GOLD SHORT @4150.0 » à 09:46 (px marché ~4029 →
**@4150 aberrant**) MAIS non persisté (`journal.json` USER=180 inchangé, resim
n=180) → 0 pollution pipeline. Probable test manuel de Sam (telegram_inbox.py /
edge_zone.py modifiés). Noté ; vérifier que le price-source de capture ne peut
écrire une valeur aberrante en prod réelle. watchdog.log toujours 0 o (17/06).

**0 hyp** (matrice momentum fermée 44 KILLED → exclure-HACHÉE / session_hour =
DUPLICATE re-knob sur 3 fills d'1 jour ; seul levier neuf = `value_gate` order-flow
= token Sam + 9 j de données → non soumis). **Lab 45/44/0/0, reco promo NON, prod GELÉE.**

**À autopsier 30/06 17h (séance US) :** (a) US500 sort-il enfin du RANGE à
l'ouverture US (cassure propre du VAH 7454 ou faux breakout comme 29/06) ? (b)
GOLD tient-il au-dessus du POC ou re-hache-t-il en après-midi ? (c) nouveaux fills
AI et leur issue ? (d) la capture @4150 réapparaît-elle (test répété) ?

---

## 2026-06-30 17h (Analyst evening, séance US)

Les 4 questions ouvertes du 13h **tranchées par la séance US** (santé VERTE 6/6,
Lab 45/44/0/0, prod GELÉE, 0 hyp, reco promo NON).

**(a) US500 = 186/186 NO_TRADE sur la JOURNÉE.** Aprem : plus-haut **7477 (16:38)**
au-dessus du VAH matin 7454, **4h basculé LONG +0.16→+0.35** (15m +0.77), MAIS
**régime resté TRANSITION/RANGE** toute la séance, jamais tendance propre. Gain
réalisé ~+0.5 % brut en grind. Could-have momentum-long le plus net du jour mais
**marginal net** et hors signature tendancielle → NO_TRADE défendable. Ré-occurrence
ATTÉNUÉE du grief n°2 : ce n'est PAS un gate lent (le 4h a suivi) mais le régime
qui ne qualifie jamais « tendance » sur un grind de range.

**(b) GOLD récupère AU-DESSUS du POC, 4h SHORT ré-inversé.** Prix **4022 (15:32) →
4047 (16:38) → 4043 (17:00)** au-dessus du POC 4022.59, régime **HACHÉE→MOYENNE**.
POC-aimant haussier RE-CONFIRMÉ (3e source). MAIS **forecast 4h resté SHORT
(-0.33/-0.48) pendant que le prix MONTAIT** = calibration 4h ré-inversée (leçon du
matin répétée). Bot NO_TRADE l'aprem (0 A_SETUP) → aucun nouveau short fadé contre
la reprise. Bonne auto-correction.

**(c) 0 nouveau fill AI l'après-midi.** Day GOLD : 150 NO_TRADE / 13 WATCH / 23
A_SETUP (TOUS matinaux, dernier AI_SIGNAL 08:14). resim equity x20 1241.11 €
INCHANGÉ. Seuls fills = 3 pertes GOLD short du matin.

**(d) Capture @4150 NON répétée.** Seules occurrences = 2 msg de 09:46 Paris
(`silent:true`, px ~4029 → @4150 aberrant), non persistées (USER=180 inchangé).
Backlog (d) du 13h résolu. À garder : price-source de capture en prod réelle.

**Cohérence radar (non-actionnable) :** spx_bias -3/-4 (baissier) vs US500 +0.5 %
(monte) = anti-corrélé ~5e jour ; gold_bias +1/+2 vs GOLD +0.5 % cohérent. Biais-news
brut non fiable seul → pondérer par réalisé/order-flow, jamais inverser.

**NOUVEAU artefact (périmètre Sam) :** module SWING (`swing_scanner.py`/`swing_book.py`/
`swing_portfolio.json`/`run_swing.bat` à 15:36 + Telegram SWING ACTIONS 13:47, 7
tickers), hors périmètre momentum-intraday, non audité, aucun lien Gate-1.

**Verdict momentum du jour :** ne bat PAS la prod nette de coûts (GOLD = 3 pertes
matin + 4h faux ; US500 = grind de range marginal). NO_TRADE de l'aprem = correct.
Manque structurel = porte order-flow `value_gate` (token Sam + ≥20 j order-flow à
accumuler), pas un énième filtre régime. **0 hyp soumise (honnête).**

**À autopsier 30/06 23h (clôture US) :** (a) US500 tient-il le plus-haut 7477 /
casse-t-il enfin en tendance ou reflux comme 29/06 ? (b) GOLD reste-t-il > POC ou
re-hache en soirée (4h SHORT se réalise-t-il enfin ou reste-t-il faux) ? (c)
nouveaux fills AI soir ? (d) le module SWING émet-il d'autres signaux ?


---

## 2026-06-30 23h, Analyst evening (bilan de séance, clôture US)

Les 4 questions ouvertes du 17h tranchées sur la séance US complète.

**(a) US500, n'a PAS reflué (≠ 29/06), mais grind, pas tendance propre.** Le
plus-haut 7477 du 17h a TENU et s'est ÉTENDU : 7487 (18h) → 7496 (19h) → 7500.6
(21h, plus-haut du jour) → 7490 (22h), soit ~+0.85 % depuis le midi (7437) et le
4h LONG-aligné (+0.31/+0.35) tout l'après-midi/soir. **MAIS le régime n'a JAMAIS
qualifié une vraie tendance pendant la montée** : TRANSITION 🟡 (18h) → TENDANCE
HACHÉE 🔴 (19-20h) → un seul flicker TENDANCE MOYENNE 🟡 à 21h, **APRÈS** que le
prix ait atteint 7500 (le sommet), puis re-HACHÉE à 22h. **229/229 NO_TRADE.**
C'est la ré-occurrence (4e soir) du grief backlog n°2 : le « could-have momentum
long » le plus net du jour, mais la qualification tendancielle arrive AU SOMMET,
pas au départ → une entrée momentum à la qualification = achat du plus-haut.
NO_TRADE défendable. Divergence notable : `recent_delta` order-flow US500 NÉGATIF
(-1599) alors que le prix MONTE = montée sans flux acheteur net (grind short-squeeze/
faible volume), cohérent avec « pas une tendance propre ».

**(b) GOLD, re-haché/RANGE en soirée, 4h SHORT directionnellement moins faux mais
non-actionnable.** Après la reprise > POC de l'après-midi (4047 @16:38), GOLD est
retombé en RANGE ⚪ (18-22h), dérive 4028 → 4018 → **4007 en fin (SOUS le POC
4028.64, AU-DESSUS du VAL 3993.85 → toujours dans la zone de valeur)** ; le 4h est resté SHORT
(-0.18/-0.48) et cette fois le prix a légèrement BAISSÉ (4037→4007) → 4h SHORT
moins faux que ce matin, MAIS en RANGE (pas tendance) et amplitude ~-0.7 % en
hachant = non-actionnable, exposé aux rebonds. Bot **NO_TRADE soir = correct.**

**(c) Nouveaux fills AI soir : 0.** Day grades GOLD 193 NO_TRADE / 13 WATCH / 23
A_SETUP (TOUS matinaux, dernier 08:24) ; US500 229 NO_TRADE. resim equity x20
**1241.11 € INCHANGÉ** depuis 09h. Seuls fills du jour = 3 pertes GOLD short matin
(-0.407/-0.406/-0.406 %). Pipeline honnête (3 pertes capturées).

**(d) Module SWING : 1 seul msg (13:47), aucun autre soir.** Pas de nouvelle
émission. Hors périmètre momentum-intraday, non audité (décision Sam).

**Cohérence radar (non-actionnable, reconduite) :** 🟢 FENÊTRE CLAIRE, F&G 15,
`spx_bias -5` (baissier) alors que US500 a fait +0.85 % (monte) = **6e jour
anti-corrélé** sur le SPX ; `gold_bias +5` (haussier) alors que GOLD a fini en
légère baisse soir = aussi anti-corrélé aujourd'hui. Biais-news brut **non fiable
seul** → pondérer par réalisé/order-flow, jamais inverser (sign-flip interdit).

**Verdict momentum du jour (bilan) :** le momentum+confluence **ne bat PAS** la
prod nette de coûts. GOLD = 3 pertes le matin (4h SHORT faux, fade sous le VAL,
confiance culminant 10/10 au pire entry), puis silence correct. US500 = la plus
belle signature momentum-long du jour MAIS qualifiée tendancielle seulement au
sommet (7500) → entrée = achat du plus-haut. **NO_TRADE de l'après-midi/soir = la
bonne réponse.** Manque structurel inchangé = (i) porte order-flow `value_gate`
(token Sam + ≥20 j order-flow ; 9 j seulement) et (ii) détecteur de transition
range→tendance PRÉCOCE (qualifier la tendance AVANT le sommet, pas après), aucun
des deux n'est un re-knob de `momentum_regime` (HA tué 12/06). **0 hyp soumise
(honnête).**

---

## 2026-06-30 (nuit mardi -> mercredi), chercheur nocturne

**Decision-prod du 30/06 (rien a rouvrir ; deja autopsie par les analystes 09/13/17/23h).**
Journee a 3 fills, tous GOLD short du MATIN (05:50-08:24 Paris), 3 LOSS (-0.407/-0.406/
-0.406%), 2 EXPIRED NOFILL. Le bot a fade la zone de valeur SOUS le VAL/POC en regime
TENDANCE HACHEE ; le POC a aimante le prix vers le haut -> short systematiquement du
mauvais cote. Confiance culminant 10/10 au PIRE entry = calibration inversee. Apres 08:24 :
silence correct tout le reste de la journee (0 nouveau fill). US500 = plus belle signature
momentum-long du jour (4h LONG, plus-hauts 7500) MAIS qualifiee tendancielle seulement AU
SOMMET -> entree = achat du plus-haut, montee SANS flux acheteur net (recent_delta NEGATIF)
-> NO_TRADE = la bonne reponse. resim equity x20 1241.11 EUR INCHANGEE (0 fill nouveau).

**FAIT NEUF de DONNEES (suite du 29/06, code+donnee-verifie) :**
(1) La FRONTIERE GOLD 1d s'est AUTO-REPAREE. Reponse a ma question ouverte (a) du 29/06 :
la barre forming 29/06 s'est completee en VRAIE OHLC (range 66.8), +30/06 VRAIE OHLC
(range 81.3). La barre 26/06 plate (O=H=L=C=4078.70) est toujours plate mais desormais
INTERIEURE (a 2 barres de la frontiere). La frontiere COURANTE est donc PROPRE.
(2) CORRECTION HONNETE de mon cadrage du 29/06 : la distribution des 55 plates REFUTE ma
theorie "fuite du settle week-end dans le lake". Les 55 plates sont concentrees MI-SEMAINE
(Mar 14 / Mer 17, PAS le week-end) et reparties sur TOUTES les annees (2021->2026) : ce sont
des JOURS MANQUANTS yfinance backfilles par un settle unique, pas un artefact week-end.
Defaut reste SYSTEMATIQUE ~4.4% et SPECIFIQUE a l'or (ES_F_1d = 0 plate). -> Le filtre
d'integrite (backlog #2) reste justifie pour tout re-test 1d LONG historique (interieur
pollue), meme si la frontiere courante est propre. Dedup (backlog #5) toujours bloquant
(key 7184c7acc424e5ef -> DUPLICATE, invariant 0 effet de bord verifie).

**0 hyp soumise (honnete).** Matrice fermee (44 KILLED) ; 2 leviers neufs (porte order-flow
value_gate ; detecteur transition range->tendance precoce) = famille NOUVELLE = token Sam,
+ order-flow 9j = walk-forward sous-puissant. Accumuler l'order-flow (9 -> ~20j) = levier #1.


## 2026-07-01 09h (mercredi, ouverture Europe), analyst momentum intraday

**Fait neuf, OPPOSE a hier.** Le forward-test a repris sa campagne GOLD SHORT
(24 A_SETUP 01:33-08:59, scores 7.0->8.3, OTE_RETRACEMENT). Fills : 02:07 SHORT
@3970.74 stop 3986.62 -> LOSS -0.407% (stop touche) ; + 4 shorts OUVERTS (02:18
@3977.38 score 8.3 ; 03:19 @3984.19 ; 06:10 @3965.41 ; 06:49 @3971.38).

**Realise (tape GOLD 77 cycles) :** derive BAISSIERE 4007->3966 (~-1.0%),
recent_delta persistamment NEGATIF (-40k a -120k) = flux net VENDEUR. POC stable
~4029 (au-dessus), VAL ~3983, VAH ~4041. Regime TRANSITION->TENDANCE PROPRE/MOYENNE.

**Verdict :** hier la direction short etait FAUSSE (reversion vers POC, grief =
porte d'entree short sous VAL). AUJOURD'HUI la direction short est CORRECTE (flux
vendeur, prix derive bas) et pourtant la seule position resolue PERD : le stop
(3986.62) etait DANS la bande de bruit VAL(~3983)..POC(~4029) -> un rebond
POC-aimant intrabar l'a clippe AVANT que le prix descende vers 3966. Stop plus
large -> trade vert (entree 3970 vs px 3966). Les 4 shorts ouverts sont a/sous
entree = direction gagnante en cours, sort = survie des stops, pas sens.

**Raffinement du grief order-flow value_gate :** ce n'est pas seulement une PORTE
d'entree (supprimer short sous VAL en range, cas 30/06) mais aussi une GEOMETRIE
de STOP (cas 01/07). Un stop dans la bande VAL..POC est systematiquement clippe
par les bounces vers le POC MEME quand le flux/direction sont justes ; en flux
vendeur confirme, le stop devrait etre AU-DELA du VAH. Ne sauve PAS la these
momentum (resim IC (-0.061,0.416) contient 0) -> localise la FUITE (stop vs auction).

**0 hyp soumise (honnete) :** exclure-HACHEE/session/ADX = re-knob des 10
momentum_regime KILLED ; value_gate (porte+stop) = famille order-flow ABSENTE du
registry = token Sam + logique 15m injugeable sur lake 1h/1d + order-flow 10j
(seuil 20). DECRITE (spec 2 volets) pour Sam. Order-flow 9->10j : levier #1 avance
d'un jour. Reco promo NON (paper_strategies = TEST_JUDGE_pass RETIRED_TEST seul).
Sante VERTE 6/6. Question tranchee a 13h : les 4 shorts ouverts finissent gagnants
ou clippes ?


## 2026-07-01 13h (mercredi, seance Europe), analyst momentum intraday

**Question ouverte du 09h TRANCHEE, verdict brutal.** Les 4 shorts GOLD OUVERTS ont
TOUS PERDU : 3965.41 -> LOSS -0.408% (stop 10:21), 3984.19 -> LOSS -0.408% (stop
12:06), 3977.38 (score 8.3, le + confiant) -> LOSS_TIME -0.152% (12:22), 3971.38 ->
LOSS -0.408%. Avec la perte 3970.74 du matin = 5 shorts / 5 pertes. Session AI du
jour = WR 12.5% n=8.

**Tape GOLD (120 cycles) :** plus-bas 3961.13, plus-haut 4007.64. Derive baissiere
02:04 @4007 -> ~3961 (08-09h) avec recent_delta NEGATIF. PUIS retournement : des ~10h
le delta flippe fortement POSITIF (10:21 +72k, 11:44 +76k), prix rebondit 3961 ->
4003 (13:01), regime -> TENDANCE HACHEE/TRANSITION. POC ~4028 (aimant), VAL ~3978,
VAH ~4040.

**Verdict = refutation la plus forte a ce jour.** Ce matin je notais que la direction
semblait enfin juste (derive a 3961) et que le sort dependrait de la survie des stops.
Reponse : les stops n'ont pas survecu, et la "bonne direction" n'etait meme pas une
tendance -- c'etait du BRUIT dans une value-area qui a reverti vers son POC des
l'arrivee des acheteurs (delta +76k). Les etiquettes TENDANCE MOYENNE/PROPRE ont classe
du chop en tendance. Un stop de short dans la bande VAL..POC est clippe par le
rebond-POC QUELLE QUE SOIT la derive anterieure. La these momentum-short intraday sur
ce regime GOLD est refutee a l'execution MEME quand la direction macro est juste.

**Confirme les DEUX volets du grief order-flow value_gate :** Volet A (porte) -- le
scanner a continue d'emettre des A_SETUP GOLD SHORT jusqu'a 11:44 ALORS QUE recent_delta
etait deja POSITIF +72k/+76k et le prix rebondissait = shorter DANS le flux acheteur =
fader la valeur par le bas. Volet B (geometrie de stop) -- stop dans VAL..POC
systematiquement clippe par le rebond-POC. NUANCE NEUVE pour Sam : le declencheur du
Volet A devrait etre recent_delta > 0 (delta = signal AVANCE) et pas seulement prix<VAL
(position prix = signal RETARDE) ; le delta flippe positif AVANT que le prix ne remonte.

**Coherence resim verifiee (pas un bug) :** equity 1190.53 EUR et n decisifs 15
INCHANGES malgre 4 cloutures aujourd'hui -> resim mesure les positions EFFECTIVES
(clusters.effective_trades), la rafale d'une meme campagne collapse en UNE position
deja bookee. Le journal BRUT montre bien les 5 pertes individuelles (session AI WR
12.5%). Les deux vues sont coherentes.

**0 hyp soumise (honnete).** exclure-HACHEE/session/ADX = re-knob des 10 momentum_regime
KILLED (data-mining). value_gate (porte+stop, triplement confirme 30/06+01/07 09h+13h) =
famille order-flow ABSENTE du registry (token Sam) + logique 15m injugeable sur lake
1h/1d + order-flow 10j (seuil 20). DECRITE (spec affinee : declencheur delta>0) pour Sam.
Order-flow stationnaire 10j : levier #1. Reco promo NON. Sante VERTE 6/6.

---

## 2026-07-01 17h, RÉTRACTATION : la "bonne direction" du 09h était fausse

À 09h/13h je concluais : shorts perdants MAIS direction baissière (3961) juste, seuls
les stops dans VAL↔POC clippés. **À 17h : RÉTRACTÉ.** GOLD cote 4093, remonté 3961→4093
(+3.3 %) depuis le plus-bas du matin, recent_delta +65k à 16:57, POC ~3977 en dessous,
prix loin AU-DESSUS du VAH 4030. Ce n'était NI tendance NI direction juste : bruit dans
une value-area, POC-aimant réaspire puis dépasse par le haut. Les 5 shorts (02:07/02:18/
03:19/06:10/06:49, tous OTE_RETRACEMENT) auraient été profondément rouges s'ils avaient
survécu aux stops. Thèse momentum-short réfutée à l'exécution ET en direction.

**Volet B chiffré par les MFE (mesuré, plus supposé) :** 03:19 MFE +0.61 % (stoppé,
stop 4000 dans VAL↔POC clippé par rebond-POC), 02:18 score 8.3 MFE +0.44 % (sorti-temps
à −0.152 % après avoir été +0.44 % en faveur). Les trades AVAIENT un edge en vol ; c'est
le stop-dans-la-valeur + la sortie-temps qui les ont convertis en pertes. Stop correct =
au-delà du VAH, mais alors RR sous plancher = signal que le setup n'a pas sa place ici.

Grief order-flow value_gate = **quadruplement confirmé** (30/06 entrée + 01/07 09h + 13h
+ 17h réaspiration complète). Étiquette régime "TENDANCE PROPRE 🟢" sur un aller-retour
POC = angle mort persistant (chop classé tendance). 0 hyp soumise (value_gate = token Sam
+ lake incompatible + order-flow 10j stationnaire, seuil 20). Reco promo NON. Santé 6/6.

---

## 2026-07-01 23h (mercredi, bilan de séance, clôture US)

**LE FAIT DU 23h, REFUTATION SYMÉTRIQUE.** La journée GOLD s'est bouclée en
oscillation dans une value-area à POC STABLE (~3977 toute la journée) : prix
3961 (plus-bas matin) → 4093 (17h) → **4031 (22:59)**. **LES DEUX trend-days du
jour auraient PERDU :**
- **01:33 trend_day SHORT @3982** (adx 30.4, er 0.473, "TENDANCE PROPRE 🟢") →
  prix monté à 4093 = short FAUX (déjà autopsié 09h/13h/17h : 5/5 shorts perdus).
- **13:40 trend_day LONG @4077** (adx 39.9, er 0.484, "TENDANCE PROPRE 🟢") →
  prix redescendu à 4031 = **long AUSSI FAUX (-1.1 %)**.

C'est la réfutation la plus forte possible : **le même jour, le trend-day
labeler a émis "TENDANCE PROPRE 🟢" des DEUX côtés d'une oscillation autour d'un
POC-aimant, et les deux directions ont perdu.** Ce n'était ni une tendance short
ni une tendance long : du BRUIT dans une VA stable. À 22:59 le régime affiche
enfin **"TENDANCE HACHÉE 🔴"** : le système a rattrapé la réalité, mais un jour
trop tard.

**POINT DE SANTÉ POSITIF (divergence utile) :** malgré le trend_day LONG de
13:40, **le scanner n'a émis AUCUN A_SETUP LONG** (dernier trigger 09:44, 42
A_SETUP tous SHORT). Toute l'après-midi/soirée = grade **NO_TRADE**. Le filtre
de confluence A_SETUP a donc été **PLUS ROBUSTE que le trend_day labeler** : il a
supprimé les entrées LONG qui auraient doublé la perte. La fuite est dans
l'étiqueteur de régime (POC oscillation classée tendance), pas (ici) dans la
porte d'entrée A_SETUP.

**Grief order-flow value_gate = quintuplement confirmé** (30/06 entrée + 01/07
09h stop + 13h les deux + 17h réaspiration + 23h whipsaw symétrique LONG+SHORT).
L'angle mort "chop classé tendance" est désormais démontré SYMÉTRIQUEMENT.
Le correctif conceptuel pointe vers l'étiqueteur de régime (VETO "TENDANCE" quand
POC plat + prix oscillant dans une VA non-expansive), famille order-flow, token
Sam, DÉCRIT, PAS soumis (lake incompatible + order-flow 10j stationnaire).
0 hyp soumise. Reco promo NON. Santé VERTE 6/6.

---

## 2026-07-01 (nuit mercredi → jeudi), CHERCHEUR NOCTURNE

**Rien de nouveau côté décision-prod** (0 fill depuis 13h Paris, journal
`last_updated` 11:00 UTC ; les 5 pertes GOLD SHORT du matin déjà autopsiées
09h/13h/17h/23h). Valeur de la nuit = **re-vérif ingestion à l'octet** +
**résolution empirique de 2 questions ouvertes du 30/06** :

- **(c) RÉSOLUE, frontière GOLD 1d 01/07 = VRAIE OHLC** (O 4025 / H 4032 / L
  3983 / C 3992, range **49.0**) **malgré que le 01/07 soit un MERCREDI**, le
  jour-semaine le plus chargé en barres plates (17/55). Enseignement : être
  mercredi n'est **PAS suffisant** pour une plate, il faut que le jour soit
  **ABSENT** du feed. Ceci **confirme et raffine** la théorie 30/06 "jours
  manquants backfillés par un settle unique" et **réfute définitivement** la
  théorie 29/06 "fuite settle week-end". Dernière plate = 26/06, désormais à
  **3 barres** de la frontière (INTÉRIEURE). Frontière **PROPRE**, intérieur
  encore pollué ~4.4 % (spécifique or ; ES_F_1d = 0 plate).
- **(d) RÉSOLUE, AUCUN nouveau MUET** dans la fenêtre prédite ~01-02/07
  (pattern ~3-4 j, dernier 28/06 04:24). `prime_watcher.log` cycle **23:27
  Paris**, cadence ~5 min continue, **0 error/traceback** (grep=0).
  `watchdog.log` 0 octet depuis 17/06 (muet-par-conception, primaire sain).

**Autopsie signal (confirmée) :** la réfutation symétrique du 23h tient, 2
trend-days OPPOSÉS le même jour (SHORT 01:33 @3982 / LONG 13:40 @4077), tous deux
"TENDANCE PROPRE 🟢", tous deux PERDANTS, autour d'un POC stable ~3977 = bruit de
value-area classé tendance des DEUX côtés. Le filtre A_SETUP (0 A_SETUP LONG
émis l'après-midi) a été plus robuste que l'étiqueteur → le correctif
`orderflow_regime_veto` viserait l'étiqueteur, pas la porte. Famille order-flow,
token Sam, INJUGEABLE (lake 1h-1d incompatible + order-flow 10j stationnaire).

**Injection externe :** news_cache (7665 ch.) + calendar_cache (18810 ch.)
scannés, 3 hits = sous-chaînes bénignes ("US commitment", "Private Sector
Credit", "BOE Credit Conditions"), **0 impératif**. Traité en donnée.

0 hyp soumise (discipline, matrice fermée). Reco promo NON. Santé VERTE.

---

## 2026-07-02 13h (jeudi, séance Europe, T−90 min NFP), ANALYST midday

**0 fill, 0 A_SETUP, 0 trend_day today.** Rien à autopsier côté décision : la
prod est restée **flat en RANGE ⚪** toute la matinée (142 cycles NO_TRADE) avant
le NFP de 14:30 Paris. Comportement attendu et sain.

**Observation de CONTRÔLE (négatif du grief order-flow) :** hier (01/07) le
labeler a classé « TENDANCE PROPRE 🟢 » les 2 jambes d'une oscillation autour d'un
POC stable (whipsaw symétrique). **Aujourd'hui, dans un range tout aussi collé au
POC** (prix 4064 ≈ POC 4067, dans la VA 4033-4087, recent_delta −45k), le labeler
dit **RANGE** et le scanner tient **NO_TRADE**. La différence n'est donc PAS « prix
près du POC » (vrai les deux jours) mais la **poussée ADX/ER transitoire** qui
faisait hier basculer l'étiquette. **Le filtre n'est pas cassé en général** : il est aveugle au seul cas *POC plat + prix dans la VA + poussée ADX/ER SANS
expansion de largeur de VA*. Le veto order-flow décrit doit cibler précisément ce
cas (distinguer vraie expansion de VA d'un rebond-POC véloce).

**Santé VERTE 6/6.** feature_store 6467/500 (+276), order-flow **10 → 11 jours**
(levier #1, encore < seuil ~20). resim inchangé (edge non prouvé, IC contient 0).
**Nouvelle obs non bloquante :** `macro_calendar mode:null` à T−90 min du NFP, à confirmer au 17h que le verrou-event s'est armé autour de 14:30. 0 hyp soumise.
Reco promo NON.

---

## 2026-07-02 23h (jeudi, bilan séance, jour NFP), ANALYST evening

**LE FAIT DU JOUR : la prod a tradé après le NFP, et perdu.** Matinée = 142 NO_TRADE
RANGE pré-NFP (contrôle sain). Soir US = **10 A_SETUP US500 SHORT OTE_RETRACEMENT,
TOUS en `TENDANCE HACHÉE 🔴`** ; **1 fill (7454.52) → LOSS −0.362 %** (clôture 22:00),
**3 EXPIRED**.

**Order-flow US500 (cœur) :** le prix est resté SOUS la value-area toute la soirée
(< VAL < POC) MAIS a grimpé **7430 → 7468 vers le POC-aimant 7483** (réaspiration
par le BAS), pendant que **recent_delta a basculé −2115 → +1743**. Le scanner a
continué d'émettre A_SETUP SHORT jusqu'à 21:50 avec delta franchement positif =
fader la réaspiration.

**Raffinement du grief order-flow :**
1. **L'étiqueteur était HONNÊTE** (a dit `HACHÉE 🔴`, pas le faux `PROPRE 🟢` du
   01/07). Donc la fuite du jour = **porte A_SETUP + value-gate**, PAS l'étiqueteur.
   Le grief se généralise à **US500** et **au côté BAS** (POC-aimant tirant vers le
   HAUT depuis sous la VAL), miroir de la réaspiration par le haut sur GOLD.
2. **Volet A (veto delta≥0) re-confirmé** : aurait tué les shorts 20:27→21:50
   (delta +103 → +1743).
3. **Nuance honnête** : le fill PERDANT était le short de 19:38 (delta −2115 =
   order-flow-correct à l'entrée), Volet A ne l'attrape PAS, il a perdu quand même
   par réaspiration POC → argument pour **Volet B** (veto SHORT sous VAL vers POC
   au-dessus quand VA non-expansive). A+B ⇒ 0 short ⇒ 0 perte le 02/07.

**Santé VERTE**, caveat : 2 alertes DISQUE C (<15 Go) aujourd'hui, auto-résolu à
~38.8 Go (garde-fou OK). resim n déc 17 (7TP/10SL) exp +0.142 % IC(−0.11,0.367)
contient 0, equity x20 1142→1094.58 € (perte US500 bookée). USER n=201 (+21 ré-import
CSV) WR 56.2 % exp −0.004 %. feature_store 6685/500, order-flow 11 j (stationnaire).
**0 hyp soumise** (matrice fermée, order-flow injugeable <20 j + absente registry).
Reco promo NON (lab papier 0).

## 2026-07-02 (nuit jeudi → vendredi, post-NFP), CHERCHEUR NOCTURNE

**Verdict d'une ligne :** pipeline **sain**, **0 hypothèse soumise** (discipliné,
matrice fermée), et **question ouverte (c) du backlog RÉSOLUE** : la frontière 1d
du **02/07 (jeudi de NFP)** est **VRAIE OHLC des DEUX côtés** (GC range 43.5, ES
range 35.25) → re-confirme (3e nuit) la théorie "jours manquants backfillés",
réfute "fuite week-end". **0 nouveau fill depuis 23h** → rien à rouvrir sur la
décision-prod du jour (déjà autopsiée par l'analyst 23h : 1 fill US500 SHORT
−0.362 % + 3 EXPIRED, tous en HACHÉE).

**Re-vérif ingestion à l'octet (ce run, pas recopié) :** lake 13 parquet frontière
02/07 vraie OHLC ; resim n déc **17 (7TP/10SL)** exp **+0.142 %** IC(−0.11,0.367)
⊃ 0 = edge NON prouvé, equity x20 **1094.58 €** (inchangé depuis 23h) ; USER
Revolut **n=201** WR 56.2 % exp −0.004 % ; feature_store **6692/500** 917 setups
0 ERROR, order-flow **11 j** (STATIONNAIRE, <seuil 20) ; journal 301 signaux
last_updated 22:39 Paris ; lab **45/44/0/0**. **Santé VERTE** : watcher cycle
**23:28 Paris** (GOLD=NO_TRADE RANGE ⚪ OVERNIGHT), cadence ~5 min, `grep error=0`,
watchdog.log 0 octet depuis 17/06 (muet-par-conception). **0 nouveau MUET**
observé. **0 injection** : news_cache (4384 ch.) + calendar_cache (18810 ch.)
scannés → 2 hits = sous-chaînes bénignes ("Cr**edit**").

**Autopsie, rien de neuf à rouvrir (0 fill depuis 23h).** Le fait du jour
(prod a tradé post-NFP et perdu, grief order-flow côté BAS sur US500) est déjà
couvert par l'analyst 23h. Ma valeur cette nuit = (a) re-vérif octet de
l'ingestion, (b) résolution empirique de la question frontière (c). **0 hyp
soumise** : matrice fermée (44 KILLED, re-knob/sign-flip = data-mining interdit
z_req~3.07), seul levier neuf `orderflow_value_gate` (2 volets, cf. rapport)
triplement bloqué (famille absente du registry token Sam + lake 1h-1d incompatible
+ order-flow 11j<20). **Accumuler order-flow 11→~20 j = levier #1.** Reco promo
**NON** (lab papier 0). Écrit uniquement dans research/.

---
## 2026-07-03 09h (vendredi, US Bank Holiday)

**Matinée : 0 A_SETUP / 0 trigger / 0 trend_day / 0 fill** : tous cycles NO_TRADE
en TENDANCE MOYENNE 🟡, prod correctement flat un jour férié US (4 juillet observé
le vendredi 3). Journal last_updated 02/07 22:39 Paris (aucun fill depuis).

**Grief order-flow, confirmation SYMÉTRIQUE côté LONG.** GOLD grimpe 4165→4173
vers le VAH (4192, POC 4122.5, VAL 4099) avec `recent_delta` PERSISTANT NÉGATIF
tout le matin (-44k → -20k) et forecast 15m négatif (-0.06) pendant que 1h/4h
positifs. Montée de prix SANS confirmation order-flow (delta vendeur = distribution
/ réaspiration probable vers le POC en dessous). Miroir exact du grief 30/06→02/07
(côté SHORT : prix vers un aimant pendant que delta contredit). Un momentum-follower
naïf achèterait ; le scanner tient NO_TRADE = bon comportement. Le
`orderflow_value_gate` Volet A s'applique symétriquement (veto LONG si delta<0,
comme veto SHORT si delta≥0), la montée GOLD sans delta acheteur = cas-test propre
côté haut. Injugeable via lake 1h-1d (pas de POC/VAL/delta 15m) ; décrit non soumis.

**Santé** : VERTE 6/6. Order-flow 11→12 jours (+1). 2 caveats non bloquants :
(i) disque C 38 Go (auto-résolu >15) ; (ii) burst DNS yahoo-fallback isolé à 04:36
(~10 `Could not resolve host` GC=F/ES=F/^GSPC/XAUUSD=X), primaire tradingview
resté 7/7, cycles ininterrompus, à reconfirmer isolé au 13h.

---
## 2026-07-03 13h (vendredi, US Bank Holiday), ANALYST midday

**Fait du midi :** la prod a émis 1 A_SETUP GOLD LONG à 10:39 Paris (conf 8.0, aligned
5/5, entry 4169.99 stop 4153.26 tp 4195.65 RR 1.53, OTE_RETRACEMENT, TENDANCE MOYENNE) →
**EXPIRED** (prix resté >4180, repli 4169.99 jamais touché) = 0 fill / 0 P&L.

**Nuance forte au grief order-flow (contre-exemple POSITIF).** Au trigger `recent_delta
= +56 140` (acheteurs FORTS), prix 4182.5 AU VAH (4181.8, POC 4124.65, VAL 4098.68). Le
scanner a tenu NO_TRADE toute la phase à delta NÉGATIF (04:53→07:39 UTC : −16k→−54k, la
« montée sans confirmation » captée au 9h) et n'a émis l'A_SETUP LONG QU'APRÈS bascule du
delta en positif (+56k, cassure VAH). Le `orderflow_value_gate` spécifié aurait LAISSÉ
PASSER ce LONG (Volet A : delta +56k confirme LONG → pas de veto ; Volet B : cassure VAH
+ delta acheteur = vraie expansion → pas de veto). Donc le gate DISCRIMINE : veto les faux
trends 30/06→02/07 (delta contredisant) ET pass ce LONG delta-confirmé. Preuve par
l'exemple qu'un bon filtre laisse passer les bons.

**Honnêteté :** l'entrée-repli n'a ni manqué un gros gagnant ni sauvé une perte, le
momentum s'est dégonflé (delta +56k→+5k, prix 4182→4177) = NEUTRE. La journée ne tranche
PAS « breakout vs repli en régime à fort delta » (mouvement fizzled). Backlog, non jugeable
via lake.

**Santé VERTE 6/6.** resim n déc 17 (7TP/10SL) exp +0.142 % IC(−0.11,0.367) ⊃ 0, equity
x20 1094.58 € INCHANGÉ. USER n=201 WR 56.2 %. feature_store 6961/500, order-flow 12 j
(stationnaire). Caveat DNS 9h RÉSOLU : burst unique confiné 04:36 (lignes 7068-7079),
0 récurrence → 13:01, isolé non bloquant. Disque C 37 Go (>15). Telegram 4 msgs today
ok:true cohérents. 0 injection (2 sous-chaînes bénignes "Cr-edit"). **0 hyp soumise**
(matrice fermée + order-flow triplement bloqué <20 j / absent registry / lake incompatible).
Reco promo NON (lab papier 0).

---

## 2026-07-03 23h (evening), bilan de séance, jour férié US

**INCIDENT** : passage ANALYST 17h PERDU (exit 1) = quota de session Claude épuisé
(`You've hit your session limit · resets 8:20pm`), PAS un bug du bot. Watcher non affecté
(cycles continus jusqu'à 22:59, tradingview 7/7). Alerte Telegram correctement émise. Quota
réinitialisé 20:20 → session 23h OK. Gap d'audit humain 13h→23h repris ce soir.

**Prod du jour** : 1 seul signal (GOLD LONG conf 8.0 de 10:39 Paris, OTE_RETRACEMENT) =
EXPIRED/NOFILL, 0 fill/0 P&L (déjà autopsié au 13h). Rien depuis (journal figé 11:28).
GOLD en consolidation 4164-4182 SOUS le VAH toute la journée, jamais de trend-day ; US500
range 7495-7505. **Momentum n'avait rien à trader** (range férié), scanner correct à tenir
NO_TRADE. À 23h : delta +26k (acheteurs) mais prix 4174.76 collé SOUS le POC 4177.7 = aimant-POC
sans expansion → cohérent avec le grief order-flow (pas de cassure VAH = pas de trade).

**Santé** : VERTE. resim a DÉRIVÉ (17→16 déc, 7TP/10SL→6TP/10SL, exp +0.142→+0.084 %, equity
x20 1094.58→1034.59 €) sur journal INCHANGÉ (1 signal today, EXPIRED non décisif) = re-simulation
résolvant les sorties contre chandelles intraday à jour (une position TP→sortie-horizon), PAS un
fill ni une corruption ; verdict INCHANGÉ (edge non prouvé, IC (−0.153, 0.286) ⊃ 0). À reconfirmer.
feature_store 7113/500, 966 setups, 0 ERROR, order-flow 12 j (stationnaire). Caveat DNS RÉGLÉ :
burst confiné cycle 04:36-04:42 (lignes 7048-7080, fail-safe INDÉTERMINÉ à 04:42, récup 04:47),
0 récurrence → 22:59. Disque C 44.9 Go (>15). Telegram tous ok:true, l'échec 17h fidèlement signalé.
0 injection (news_cache 0 hit ; calendar_cache 1 sous-chaîne bénigne "Cr-edit").

**0 hyp soumise** (matrice fermée + order-flow triplement bloqué <20 j / absent registry / lake
incompatible). Reco promo NON (lab papier 0). Levier #1 = accumuler order-flow 12→20 j.

---

## 2026-07-03 nuit (chercheur nocturne), vendredi férié US -> samedi

**0 hyp soumise** (matrice fermée 44 KILLED, jour férié 0 trend-day, order-flow
triplement bloqué). Lab 45/44/0/0. Prod GELÉE. Reco promo NON.

**Backlog #2 RECONFIRMÉ, la dérive resim s'est ARRÊTÉE.** Mon run est byte-identique
à l'analyst 23h (16 déc, 6TP/10SL, exp +0.084 %, equity x20 1034.59 €). La dérive
17->16 déc signalée à 23h ne progresse plus -> c'était une re-simulation VIVANTE
(1 position TP -> sortie-horizon quand les chandelles intraday se sont mises à jour),
PAS une régression du pipeline. Journal figé 11:28 (1 signal today, EXPIRED, non
décisif). Verdict INCHANGÉ : edge net non prouvé (IC bootstrap-jours (-0.153, 0.286)
contient 0). USER Revolut n=201 WR 56.2 % exp -0.004 %.

**FAIT NEUF (données), la barre-FRONTIÈRE 1d est PARTIELLE (en cours), pas une OHLC
arrêtée.** Preuve par la même barre à 24 h : GC_F_1d 02/07 lu range 43.5 EN FRONTIÈRE
hier -> 78.1 FINALISÉE aujourd'hui ; ES_F_1d 02/07 35.25 -> 114.25 (!). Les 3 nuits
précédentes ont dit "frontière vraie OHLC" = vrai mais INCOMPLET (range tronqué). La
frontière n'est PAS une plate settle (bon) mais grandit jusqu'au settle -> ne doit pas
servir de référence-prix figée ; tout re-test 1d doit EXCLURE la dernière barre (en
cours) EN PLUS du filtre plates. -> nouvel item backlog #4 (filtre "frontière
partielle"), à coupler #3 (filtre plates) + #5 (fingerprint-clé).

**Question (c) du backlog 02/07 RÉSOLUE.** La frontière GC_F_1d 03/07 (vendredi, 2e
jour le plus chargé en plates 13/55) est NON-PLATE (range 74.5, cohérent avec la
volatilité GC récente 66.8/87.2/137.0/78.1) ; ES 33.0. 4e nuit consécutive confirmant
"seul un jour ABSENT du feed est backfillé plat". Dernière plate = 26/06 (Fri), à 5
barres de la frontière (intérieure). 55 plates GC (4.4 %, intérieures), 0 plate ES.
NOTE d'honnêteté : ma tentation de crier "anomalie" (CFD ~18 pts vs futur 74.5) était
FAUSSE -- instruments/sessions différents, GC=F 1d inclut le globex.

**Décision-prod 03/07 (rien à rouvrir).** Jour férié -> prod flat. 1 seul signal =
A_SETUP GOLD LONG conf 8.0 (10:39 Paris, OTE_RETRACEMENT) EXPIRED/NOFILL = 0 fill.
Contre-exemple POSITIF au grief order-flow : émis seulement après bascule delta positif
(+56k, cassure VAH) -> orderflow_value_gate l'aurait laissé passer (discrimine). GOLD
en consolidation 4164-4182 sous le VAH toute la journée, jamais de trend-day -> 0
matière momentum. Momentum dégonflé ensuite (delta +56k->+5k) = sortie neutre.

**Santé.** feature_store 7113/500, 0 ERROR, 3 MIXED exclus, 966 setups, order-flow 12 j
distincts (stationnaire, seuil 20). Incident 17h = quota de session Claude (côté Sam,
PAS un bug bot ; alerte Telegram correctement émise ; watcher non affecté). Caveat DNS
RÉGLÉ (burst confiné cycle 04:36-04:42, fail-safe INDÉTERMINÉ, 0 récurrence). Disque C
44.9 Go. Injection : news_cache 0 hit ; calendar_cache 5 sous-chaînes bénignes "Credit",
0 impératif. z_req test n+1 = 3.0654. Dedup invariant OK (hypothesis_key 7184c7acc424e5ef
-> DUPLICATE, lab byte-stable). Écrit uniquement dans research/.

---

## 2026-07-04 09h (analyst), SAMEDI, marché fermé (week-end)

**Autopsie NÉANT** : marché fermé (vendredi = US Bank Holiday, aujourd'hui samedi).
Le watcher cycle sur prix GELÉS du close vendredi (GOLD 4174.76, US500 7504.2,
delta figé), source tradingview 7/7, 99 cycles 00:05→08:59 Paris, **0 A_SETUP /
0 trigger** = correct (rien à trader). Aucune décision à confronter au réalisé.

**Santé VERTE 6/6.** resim **STABLE byte-identique au nocturne 03/07** (24 tr /
16 déc / 6TP-10SL / exp +0.084 % / IC (−0.153, 0.286) ⊃ 0 / equity 1034.59 €) →
backlog #2 reconfirmé (dérive resim arrêtée, edge non prouvé INCHANGÉ). feature_store
9232 feat / 7113 outcomes / 966 setups / order-flow 12 j (<20, modèle non autorisé).
Logs sains (prime_watcher 1.75 Mo 0 erreur ; watchdog 0 o muet-par-conception).
Disque C 42 Go. Telegram : briefing 09h `ok:true` cohérent (F&G 22, week-end signalé).
Injection RAS (news 0 item ; calendar 2× « edit » = fragments de « Credit »).

**0 hyp** (matrice fermée 44 KILLED + order-flow triplement bloqué + 0 trend-day
week-end injugeable). Reco promo NON (papier 0). Levier #1 = order-flow 12→20 j.

---
## 2026-07-04 13h (SAMEDI, marché fermé), AUTOPSIE NÉANT
Week-end : 0 signal / 0 fill / 0 décision à confronter au réalisé. Prix gelés du
close vendredi (GOLD 4174.76, US500 7504.2). Prod 0 A_SETUP = correct (rien à
trader). Santé VERTE 6/6 : resim byte-identique (exp +0.084%, IC (-0.153,0.286)⊃0,
equity 1034.59€), journal last_updated 03/07 09:28 inchangé, feature_store
9232/7113/966 order-flow 12j<20, datafeed 143/143 pure tradingview, disque 40 Go,
outbox 3/3 ok:true. Backlog #3 DNS reconfirmé réglé (burst 03/07 04:36-04:42 isolé,
0 récurrence). Injection RAS (7 news géopol Iran/pétrole = données, calendar
fragments Credit/non-farm bénins). 0 hyp (discipline : matrice fermée + order-flow
triplement bloqué + week-end injugeable). Reco promo NON.

## 2026-07-04 23h (analyst, SAMEDI marché fermé), NÉANT
Week-end : 254 cycles 254/254 NO_TRADE sur prix GELÉS du close vendredi (GOLD 4174.76,
US500 7504.2, identiques 09h/13h/17h), datafeed 1524/1524 PURE tradingview. 0 A_SETUP /
0 WATCH / 0 trigger / 0 fill : aucune décision à confronter au réalisé. Dernier événement
décisionnel = A_SETUP GOLD LONG conf 8.0 vendredi 10:39 (EXPIRED/NOFILL, déjà autopsié).
Verdict momentum du jour : injugeable (0 trend-day, 0 expansion, prix figés). Santé VERTE
6/6, resim byte-identique (24/16/6TP-10SL/exp+0.084%/IC(-0.153,0.286)⊃0), journal INCHANGÉ
(03/07 09:28). Anomalies logs confinées lignes 7049-7079 (incident DNS clos), 0 récurrence.

## 2026-07-04 nocturne (samedi->dimanche, marché FERMÉ week-end), AUTOPSIE NÉANT + fait données
Week-end : 0 signal / 0 fill / 0 décision à confronter au réalisé (journal figé au
03/07 09:28, 302 entrées, 0 trade le 04/07). Dernier événement décisionnel = A_SETUP
GOLD LONG conf 8.0 vendredi 10:39 (EXPIRED/NOFILL, déjà autopsié 13h/23h). Verdict
momentum : injugeable (0 trend-day, 0 expansion, prix gelés du close vendredi).
FAIT DE DONNÉES (résout "à autopsier (c)" d'hier) : la frontière lake reste 03/07
(Fri) pour GC ET ES, AUCUNE barre samedi 04/07. Théorie jours-manquants TRANCHÉE :
un jour de marché FERMÉ (week-end) est ABSENT du feed, PAS backfillé plat (les 55
plates GC sont 100% mid-week, Mon6/Tue14/Wed17/Thu5/Fri13, 0 samedi/dimanche).
Frontière partielle (backlog #4) confirmée puis FIGÉE : ES_F_1d 03/07 lue 33.0 hier
(barre en cours) → 41.5 finalisée ce run (settle vendredi passé, week-end sans donnée).
Santé VERTE : resim byte-identique (24/16/6TP-10SL/exp+0.084%/IC(-0.153,0.286)⊃0/
1034.59€), feature_store 9232/7113/966 order-flow 12j<20 stationnaire, watcher vivant
23:29 NO_TRADE (0 anomalie 250 dernières lignes), disque 40 Go. Injection RAS (news 0
hit, calendar 5 sous-chaînes "Credit" bénignes). 0 hyp (discipline). Reco promo NON.

## 2026-07-05 09h (DIMANCHE, marché fermé week-end)
NÉANT. 100 cycles 00:01→08:56 Paris, 100/100 NO_TRADE, prix gelés close vendredi
(GOLD 4174.76, US500 7504.2), datafeed tradingview pur. 0 signal/fill/décision à
confronter au réalisé. Dernier événement décisionnel = A_SETUP GOLD LONG conf 8.0
vendredi 10:39 (EXPIRED/NOFILL, déjà autopsié). Verdict momentum du jour : injugeable
(0 trend-day, 0 expansion, prix figés). Santé VERTE 6/6, resim stable byte-identique.


## 2026-07-05 nocturne (nuit dimanche -> lundi -- marché FERMÉ week-end)
NÉANT décisionnel. Bilan week-end COMPLET : 0 signal / 0 fill / 0 décision du samedi au
dimanche soir, watcher 256 cycles / 512-512 NO_TRADE sur prix GELÉS close vendredi
(GOLD 4174.76 / US500 7504.2, POC GOLD 4177.7 / US500 7497.01 figés). La prod n'avait
RIEN à trader = correct. Dernier événement décisionnel = A_SETUP GOLD LONG conf 8.0
vendredi 10:39 (EXPIRED/NOFILL, déjà autopsié). Verdict momentum : injugeable (0 trend-day,
0 expansion, prix figés tout le week-end).
FAIT NEUF (durcissement, code exp_2026_07_05_nocturne.py) : hier avait tranché « samedi
absent du feed » ; ce run étend au WEEK-END ENTIER, après ~2 jours (close vendredi 03/07
-> dimanche soir), le lake a ajouté ZÉRO barre, frontière GC ET ES TOUJOURS 2026-07-03
(Fri) range 74.5 / 41.5. Week-end = TROU (ni plate ni barre) ; les 55 plates GC restent
100% mid-week (Mon6/Tue14/Wed17/Thu5/Fri13, 0 week-end). Frontière partielle (backlog #4)
BOUCLÉE ET FIGÉE : ES_F_1d 33.0 (vendredi en cours) -> 41.5 (settle, nuit samedi) -> 41.5
immobile tout le dimanche = cycle complet démontré.
SANTÉ VERTE 6/6 : resim byte-identique (24/16/6TP-10SL/WR37.5%/exp+0.084%/IC(-0.153,0.286)
contient 0 / 1034.59 EUR), feature_store 9232/7113/966 order-flow 12j<20 stationnaire, journal
last_updated 03/07 09:28 INCHANGÉ (302 signaux), watcher vivant 23:28 (256 cycles, log 7945
lignes 0 traceback, 31 DNS confinées 7049-7079), watchdog 0 octet, disque C ~230 Go libres
(49% util ; correction : « 40 Go » des rapports antérieurs = erroné), outbox 11/11 ok:true.
Injection RAS (news 2 items géopol GEO_ESCALATION 0 hit impératif ; calendar seul hit =
Consumer Cr-edit bénin). Invariant dedup vérifié (cellule 22/06 re-soumise -> DUPLICATE,
lab 45/44/0/0 byte-stable, 0 effet de bord). 0 hyp (discipline). Reco promo NON. Reprise
accumulation order-flow 12->20j lundi 06/07.
