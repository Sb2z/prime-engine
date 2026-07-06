#!/usr/bin/env python3
"""Veille Prime Strategy.

Surveille GOLD et US500 en continu, signale les A_SETUP, et garde un historique
structuré pour mesurer combien de setups Prime apparaissent sur une semaine.
Écrit dans stdout pour le suivi humain + JSONL pour l'analyse.
"""

import datetime
import json
import os
import subprocess
import time

import journal
import notify
import prime_strategy
import tz

INTERVAL_SEC = 300
ALERT_COOLDOWN_MIN = 45
EVENTS_FILE = "/Users/sam/trading/prime_watcher_events.jsonl"


def paris_now():
    return tz.paris_now()


_events_month_checked = None


def _rotate_events():
    """Rotation mensuelle (archive prime_watcher_events_YYYY-MM.jsonl) + garde-fou
    TAILLE : archive aussi dès ~50 Mo, indépendamment du mois, pour borner la
    croissance intra-mois (audit 2026-06-18). getsize est cheap, OK à chaque append."""
    global _events_month_checked
    try:
        if os.path.getsize(EVENTS_FILE) > 50_000_000:
            stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H%M")
            os.rename(EVENTS_FILE, EVENTS_FILE.replace(".jsonl", f"_{stamp}.jsonl"))
    except FileNotFoundError:
        pass
    except Exception:
        pass
    current = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m")
    if _events_month_checked == current:
        return
    _events_month_checked = current
    try:
        with open(EVENTS_FILE) as f:
            first = json.loads(f.readline())
        month = (first.get("ts") or "")[:7]
        if month and month != current:
            os.rename(EVENTS_FILE, EVENTS_FILE.replace(".jsonl", f"_{month}.jsonl"))
    except (FileNotFoundError, json.JSONDecodeError):
        pass
    except Exception:
        pass


def append_event(event):
    _rotate_events()
    event = dict(event)
    event["ts"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    event["paris"] = paris_now().strftime("%Y-%m-%d %H:%M")
    with open(EVENTS_FILE, "a") as f:
        f.write(json.dumps(event, ensure_ascii=False, separators=(",", ":")) + "\n")


def notify_macos(title, message):
    """Notification macOS best effort. Le log reste la source fiable."""
    safe_title = title.replace('"', "'")
    safe_message = message.replace('"', "'")
    script = f'display notification "{safe_message}" with title "{safe_title}" sound name "Glass"'
    try:
        subprocess.run(["osascript", "-e", script], timeout=4, check=False)
    except Exception:
        pass


def setup_key(decision):
    setup = decision.get("setup") or {}
    def bucket(value):
        try:
            return round(float(value), 1)
        except Exception:
            return value
    return "|".join(str(x) for x in (
        decision.get("asset"),
        setup.get("direction"),
        bucket(setup.get("entry")),
        bucket(setup.get("stop")),
        bucket(setup.get("tp")),
    ))


def fmt_pct(value):
    if value is None:
        return "?"
    return f"{value:+.1f}%"


def _single_instance_lock():
    """Anti double-instance (audit 07-02) : un 2e prime_watcher lancé à la main
    ne meurt PAS sur le verrou DuckDB (tout est sous except) mais pollerait
    getUpdates en concurrence -> captures de trades perdues/dupliquées. Verrou
    d'1 octet tenu à vie du process ; Windows le libère à la mort (même kill)."""
    import msvcrt
    f = open("/Users/sam/trading/watcher.lock", "a")
    f.seek(0)  # toujours verrouiller l'octet 0 (en 'a' la position est à EOF)
    try:
        msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
    except OSError:
        raise SystemExit("prime_watcher DÉJÀ en cours (watcher.lock), refus de doubler.")
    return f


def main():
    _lock = _single_instance_lock()  # tenu jusqu'à la mort du process
    alerted = {}
    trend_alerted = {}      # (asset, direction, date) → déjà alerté
    pre_event_alerted = {}  # detail → date
    summary_sent = None     # date du dernier résumé quotidien
    print(f"START @ {paris_now().strftime('%Y-%m-%d %H:%M')} Paris | Prime watcher continu", flush=True)
    while True:
        p = paris_now()
        # Redémarrage propre SANS admin : la tâche tourne en SYSTEM, impossible à
        # arrêter depuis une console non élevée. Déposer un fichier STOP_WATCHER
        # -> sortie propre ici, et le superviseur (start_watcher.bat) relance en
        # 30 s avec le code frais. On supprime le fichier AVANT de sortir (sinon
        # boucle d'arrêts).
        _stop = "/Users/sam/trading/STOP_WATCHER"
        if os.path.exists(_stop):
            try:
                os.remove(_stop)
            except Exception:
                pass
            print(f"{p.strftime('%H:%M')} STOP_WATCHER détecté -> sortie propre, "
                  f"le superviseur relance avec le code frais", flush=True)
            raise SystemExit(0)
        try:
            # Écoute Telegram : capture le contexte des trades que Sam signale
            # (« T GOLD SHORT 4150 ») à l'instant exact -> dataset pour modéliser l'edge.
            try:
                import telegram_inbox
                telegram_inbox.poll_and_capture()
            except Exception as exc:
                print(f"{p.strftime('%H:%M')} erreur telegram inbox: {exc}", flush=True)
            # Banc d'essai PAPIER des hypothèses du mining (gold_ny_fade,
            # us500_value_reversion), validation forward, zéro argent réel.
            try:
                import paper_lab
                paper_lab.tick()
            except Exception as exc:
                print(f"{p.strftime('%H:%M')} erreur paper lab: {exc}", flush=True)
            # Évaluation des signaux ouverts du journal avec fills intrabar 1m
            try:
                import datafeed
                closed = journal.evaluate_open_live()
                sources = datafeed.last_sources()
                if sources:
                    append_event({"type": "datafeed_sources", "sources": sources})
                    degraded = {k: v for k, v in sources.items() if v != "tradingview"}
                    if degraded:
                        print(f"{p.strftime('%H:%M')} datafeed dégradé: {degraded}", flush=True)
                for s in closed:
                    print(
                        f"{p.strftime('%H:%M')} CLOSE {s['asset']} {s['direction']} "
                        f"@{s['entry']} → {s['result']} ({s['pnl_pct']:+.2f}%)",
                        flush=True,
                    )
                    append_event({"type": "journal_close", "signal_id": s["id"],
                                  "result": s["result"], "pnl_pct": s["pnl_pct"],
                                  "fill_quality": s.get("fill_quality")})
            except Exception as exc:
                print(f"{p.strftime('%H:%M')} erreur évaluation journal: {exc}", flush=True)

            cyc_t0 = time.time()
            data = prime_strategy.evaluate()
            triggers = [d for d in data["decisions"] if d.get("grade") == "A_SETUP"]
            radar = data["radar"]
            append_event({
                "type": "cycle",
                "radar": radar,
                "decisions": data["decisions"],
                "duration_s": round(time.time() - cyc_t0, 1),
            })

            # Feature store : une ligne par actif + backfill des outcomes
            try:
                import feature_store
                feature_store.record_cycle(data)
                feature_store.backfill_outcomes(max_rows=400)
                # Export parquet à chaque cycle : la base est verrouillée par
                # ce process, les lecteurs externes lisent l'export.
                feature_store.export_parquet()
            except Exception as exc:
                print(f"{p.strftime('%H:%M')} erreur feature store: {exc}", flush=True)
            # Outcomes des trades capturés de Sam (user_trade_context) : fonction
            # DIFFÉRENTE du backfill feature_store ci-dessus, audit 07-02 : elle
            # n'était branchée nulle part, le dataset du 1er modèle cessait de
            # mûrir en silence dès qu'on ne la lançait plus à la main.
            try:
                import user_trade_context
                user_trade_context.backfill_outcomes()
            except Exception as exc:
                print(f"{p.strftime('%H:%M')} erreur backfill captures: {exc}", flush=True)
            if triggers:
                printed_header = False
                for d in triggers:
                    s = d["setup"]
                    line = (
                        f"{d['asset']} {s['direction']} | conf {s['conf']}/10 | "
                        f"entry {s['entry']} stop {s['stop']} tp {s['tp']} RR {s['rr']}:1 | "
                        f"forecast {d['forecast_direction']} | regime {d.get('regime')}"
                    )
                    mgmt = d.get("management") or {}
                    if mgmt:
                        lp = mgmt.get("leverage_profile") or {}
                        sz = mgmt.get("sizing") or {}
                        line += (
                            f" | gestion {mgmt.get('mode')} "
                            f"entry_valid {mgmt.get('entry_valid_minutes')}m "
                            f"review {mgmt.get('review_after_hours')}h "
                            f"max {mgmt.get('max_hold_hours')}h"
                        )
                        if lp:
                            line += (
                                f" | target {mgmt.get('target_policy')} x{lp.get('leverage')} "
                                f"TP {fmt_pct(lp.get('tp_x20_pct'))} SL {fmt_pct(lp.get('sl_x20_pct'))}"
                            )
                        if sz:
                            line += (
                                f" | size<={sz.get('max_margin_pct_of_account')}% cap "
                                f"risk {sz.get('max_account_risk_pct')}%"
                            )
                    edge = d.get("adaptive_edge") or {}
                    if edge.get("mode") == "ACTIVE_FILTER":
                        line += (
                            f" | edge {edge.get('policy_label')} "
                            f"{edge.get('final_equity')}€ vs {edge.get('baseline_final_equity')}€"
                        )

                    key = setup_key(d)
                    last = alerted.get(key, 0)
                    now = time.time()
                    if now - last >= ALERT_COOLDOWN_MIN * 60:
                        alerted[key] = now
                        if not printed_header:
                            print(f"TRIGGER @ {p.strftime('%Y-%m-%d %H:%M')} Paris", flush=True)
                            printed_header = True
                        print(line, flush=True)
                        append_event({"type": "trigger", "decision": d})
                        notify.send(f"🎯 Prime A_SETUP\n{line}")
                        # Auto-journalisation EN ATTENTE (audit 2026-06-17) : on
                        # mesure le VRAI trade, remplissage de l'entrée annoncée
                        # puis TP/SL. evaluate_open_live le suit intrabar.
                        try:
                            journal.log_pending_setup(
                                d["asset"], s["direction"], s["entry"], s["stop"],
                                s["tp"], score=s.get("conf"), strategy=s.get("strategy"),
                                valid_minutes=int(mgmt.get("entry_valid_minutes") or 45),
                                price_source=d.get("price_source"), rr=s.get("rr"),
                                entry_mode=s.get("entry_mode"))
                        except Exception as exc:
                            print(f"{p.strftime('%H:%M')} erreur journal pending: {exc}",
                                  flush=True)
                        lp = mgmt.get("leverage_profile") or {}
                        sz = mgmt.get("sizing") or {}
                        edge = d.get("adaptive_edge") or {}
                        notify_macos(
                            f"Prime A_SETUP {d['asset']} {s['direction']}",
                            (
                                f"Entry {s['entry']} Stop {s['stop']} TP {s['tp']} RR {s['rr']}:1 | "
                                f"{mgmt.get('target_policy', mgmt.get('mode', ''))} | "
                                f"x20 TP {fmt_pct(lp.get('tp_x20_pct'))} SL {fmt_pct(lp.get('sl_x20_pct'))} | "
                                f"size<={sz.get('max_margin_pct_of_account')}% | "
                                f"edge {edge.get('policy_label', 'BASELINE')}"
                            ),
                        )

            # Fenêtre pré-event macro → alerte Telegram (une fois par fenêtre)
            if radar["alert"].startswith("🔴 PRÉ-EVENT"):
                key = radar.get("message") or "pre-event"
                if pre_event_alerted.get(key) != p.date():
                    pre_event_alerted[key] = p.date()
                    notify.send(f"⏳ {radar['alert']}, {radar.get('message')}")

            # Job quotidien d'enrichissement des actuals (no-op sinon)
            try:
                import calendar_feed
                job = calendar_feed.daily_actuals_job()
                if job.get("status") == "ok":
                    print(f"{p.strftime('%H:%M')} actuals enrichis: {job}", flush=True)
                    append_event({"type": "actuals_job", **job})
            except Exception as exc:
                print(f"{p.strftime('%H:%M')} erreur job actuals: {exc}", flush=True)

            # Shadow PAPER du Research Lab (zéro alerte, journalisation seule)
            try:
                import paper_shadow
                entries = paper_shadow.run_shadow()
                for e in entries:
                    print(f"{p.strftime('%H:%M')} PAPER {e['strategy']} "
                          f"{e['asset']} {e['direction']}", flush=True)
                    append_event({"type": "paper_entry", **e})
            except Exception as exc:
                print(f"{p.strftime('%H:%M')} erreur paper shadow: {exc}", flush=True)

            # Mode scalp-tendance (additif, ne touche pas aux décisions Prime)
            try:
                import trend_day_trigger
                for s in trend_day_trigger.check_all():
                    if not s.get("armed"):
                        continue
                    key = (s["asset"], s["direction"], p.date())
                    if key in trend_alerted:
                        continue
                    trend_alerted[key] = True
                    print(f"{p.strftime('%H:%M')} TREND DAY {s['asset']} {s['direction']} "
                          f"ADX {s['adx_15m']} ER {s['er']}", flush=True)
                    append_event({"type": "trend_day", "state": {
                        k: s[k] for k in ("asset", "direction", "adx_15m", "er",
                                          "regime", "event_day", "zones_rebond", "price")}})
                    # Silencieux la nuit : l'armement reste loggé/envoyé mais
                    # ne réveille pas (le 1er trigger réel est parti à 01:20)
                    notify.send(s["message"], silent=not (8 <= p.hour < 22))
                    notify_macos("Trend day armé", s["message"].split("\n")[0])
            except Exception as exc:
                print(f"{p.strftime('%H:%M')} erreur trend day: {exc}", flush=True)

            # Résumé quotidien (23h Paris) : stats effectives + gate feature store
            if p.hour >= 23 and summary_sent != p.date():
                summary_sent = p.date()
                try:
                    import feature_store
                    _, st = prime_strategy.should_replace_user_strategy()
                    ai, fs = st["ai"], feature_store.stats()
                    # Parité Pine : on LIT le fichier écrit par
                    # compare_pine_parity.py, jamais de CDP/MCP ici
                    # (découplage : TradingView fermé ne casse rien).
                    parite = "inconnu (jamais lancé)"
                    try:
                        with open("/Users/sam/trading/pine_parity_status.json") as pf:
                            ps = json.load(pf)
                        age_h = (datetime.datetime.now(datetime.timezone.utc)
                                 - datetime.datetime.fromisoformat(ps["ts"])).total_seconds() / 3600
                        parite = f"{ps.get('status', '?')} (il y a {age_h:.0f}h)"
                    except FileNotFoundError:
                        pass
                    except Exception:
                        parite = "fichier illisible"
                    # Research Lab : rétrogradation auto + compteurs
                    lab_line = ""
                    try:
                        import harness
                        demoted = harness.check_demotions(journal.load_journal())
                        c = harness.lab_counters()
                        lab_line = (f"Lab: {c['testees']} testées / {c['tuees']} tuées / "
                                    f"{c['papier']} papier / {c['promues']} promues"
                                    + (f" · rétrogradées: {demoted}" if demoted else "") + "\n")
                    except Exception:
                        pass
                    notify.send(
                        f"📊 Résumé quotidien Prime\n"
                        f"IA: WR {ai['wr']}% (n_tp_sl {ai['n_tp_sl']}, effectif {ai['n']}) "
                        f"exp {ai['expectancy']:+.3f}%\n"
                        f"Feature store: {fs.get('features')} lignes, gate "
                        f"{fs.get('gate_apprentissage')} (MIXED exclus: "
                        f"{fs.get('outcomes_mixed_exclus')})\n"
                        f"Pine parité: {parite}\n"
                        f"{lab_line}"
                        f"Gate 1 forward-test en cours, seuils gelés.",
                        silent=True,
                    )
                except Exception as exc:
                    print(f"{p.strftime('%H:%M')} erreur résumé: {exc}", flush=True)

            states = []
            for d in data["decisions"]:
                reason = d.get("reason") or "; ".join(d.get("vetoes") or [])
                states.append(
                    f"{d['asset']}={d['grade']} forecast={d.get('forecast_direction')} "
                    f"regime={d.get('regime')} ({reason})"
                )
            print(
                f"{p.strftime('%H:%M')} {'A_SETUP détecté' if triggers else 'pas de A_SETUP'} | {radar['alert']} | "
                + " | ".join(states),
                flush=True,
            )
        except Exception as exc:
            print(f"{p.strftime('%H:%M')} erreur veille Prime: {exc}", flush=True)
            append_event({"type": "error", "message": str(exc)})

        time.sleep(INTERVAL_SEC)


if __name__ == "__main__":
    main()
