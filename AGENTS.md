# Les agents du système

Un agent = une entrée dans ce fichier : ce qu'il fait, ce qui le déclenche, ce qu'il consomme et produit, et les garde-fous qui le bornent. La règle maison est simple — pas d'entrée ici, pas d'agent en production.

| Agent | Rôle | Déclencheur | Entrées | Sorties | Garde-fous |
|---|---|---|---|---|---|
| **prime_watcher** | Orchestrateur : enchaîne scan → gradation → juge → capture → notifications | Tâche ONSTART + boucle ~5 min | Flux TradingView, news, calendrier macro | Événements JSONL, lignes DuckDB, alertes Telegram | Verrou single-instance ; chaque étape sous try/except loggué ; arrêt propre par fichier `STOP_WATCHER` |
| **scanner / prime_strategy** | Détection des setups et gradation (A_SETUP / WATCH / NO_TRADE) | Chaque cycle | Prix, confluence, régime, order-flow | Setups gradés avec entrée/stop/TP/RR | Caps de distance en ATR, fenêtre horaire pour l'entrée-marché, vetos (news, fenêtres de volatilité mortes, anti-chasse au-dessus de la value area), garde-fou d'espérance historique |
| **journal (le juge)** | Vérité du système : fills réels sur bougies 1 min, TP/SL intrabar, expiration, statistiques | Chaque cycle | Signaux en attente, bougies, prix | Statuts, win rate / espérance / fill rate | Anti cross-source (jamais juger un fill sur une autre référence de prix), état NO_DATA quand rien n'a été observé, stats séparées IA / humain, fantômes week-end exclus |
| **feature_store** | Mémoire : une ligne de contexte par actif et par cycle | Chaque cycle | Sortie complète du cycle | Table DuckDB + Parquet | Anti-lookahead, pas de lignes marché fermé, export atomique, base mono-écrivain |
| **telegram_inbox** | Interface entrante : journal de trade (`T …`) et verdict pré-trade (`Z …`) | Message Telegram | Messages du chat autorisé uniquement | Capture horodatée + verdict `edge_zone` | Parsing 100 % code (aucune entrée utilisateur ne touche un LLM), offset consommé après traitement, état atomique, échec de capture notifié |
| **edge_zone** | Discipline : juge chaque trade contre les statistiques personnelles apprises | Sur log / à la demande | Contexte de marché + historique des trades réels | Verdict chiffré (zone / marginal / dérive) | Purement advisory ; tables recalculées des données (aucune règle codée en dur) |
| **swing_book** | Book actions : règles de sortie + rotation momentum sur ~77 titres | Lundi 14 h (tâche) | Données yfinance daily + fondamentaux | Message « ACHÈTE / VENDS », grand livre, suivi vs QQQ et vs univers équipondéré | État commité seulement si la notification est partie ; panne de données affichée, jamais silencieuse ; benchmark anti-biais (équipondéré du propre univers) |
| **paper_lab** | Validation forward : hypothèses du mining jouées en papier | Chaque cycle | Règles figées à l'avance, prix | Signaux + sorties journalisés, bilan net de coûts | Zéro capital ; règles définies avant les données ; verdict à échéance fixée |
| **Analyste (LLM)** | Analyse de contexte 4×/jour, propositions d'amélioration | Tâches 9 h / 13 h / 17 h / 23 h | Journal, événements, macro | Rapport versionné + résumé Telegram | Session CLI à permissions bornées (deny-list), écrit uniquement dans `research/`, timeout, échec notifié |
| **Chercheur nocturne (LLM)** | Mining d'hypothèses sous protocole | Tâche 23 h 30 | Historique complet | Verdicts et registre d'hypothèses | Même bac à sable ; déflation des tests multiples ; le juge tranche ; l'humain promeut |
| **watchdog** | Auto-réparation : détecte mort, gel ou crash-loop | Tâche 15 min | Fraîcheur du dernier cycle réel, process, disque | Relance automatique + alertes | Distingue « pas de setup » de « système en panne » ; anti-spam ; alerte disque |
| **maturation_report** | Suivi de la progression vers le prochain modèle | Dimanche 20 h | Compteurs feature store + captures + paper-lab | Briefing Telegram | Compteurs honnêtes (jours réellement utilisables, exclusions qualité affichées) |
| **claudeverstradingview (MCP)** | Pont TradingView Desktop : data window, scan multi-symboles, parité Pine | À la demande (CLI / client MCP) | Session TradingView via Chrome DevTools Protocol | Lectures structurées pour agents et scripts | Lecture seule de la plateforme ; voir `tools/claudeverstradingview/SECURITY.md` |

## Cycle de vie d'un agent

1. **Proposition** — une hypothèse ou un besoin, formalisé dans `research/`.
2. **Validation** — backtest honnête (déflation, coûts, jours distincts) puis validation forward en papier.
3. **Déploiement** — tâche planifiée + entrée dans ce registre + garde-fous explicites.
4. **Mesure** — chaque agent notifie ses échecs ; les métriques passent dans les rapports hebdomadaires.
5. **Révision** — un agent dont l'hypothèse est réfutée est dégradé en informatif ou retiré (voir l'historique du premier modèle, rejeté par son propre protocole).
