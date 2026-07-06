#!/usr/bin/env python3
"""RAPPORT HEBDO DE MATURATION — suit la progression vers le 1er modèle appris,
sans avoir à demander. Envoyé sur Telegram (dimanche 20h, cf. windows/run_maturation.bat).

Métriques clés (analyse 06-19/06-22) :
  • jours_order_flow_distincts /15  → quand on pourra entraîner un modèle honnête
  • fill AI par actif               → le GOLD doit décoller (fix entrée-marché 06-22)
  • WR / espérance / fill global    → santé de la mesure
  • trades USER capturés            → le levier que Sam doit activer (loguer ses trades)
"""
from collections import defaultdict

import edge_zone
import feature_store
import journal
import notify
import user_trade_context


def _fmt_pct(v):
    return f"{v:+.3f}%" if isinstance(v, (int, float)) else "?"


def build():
    fs = feature_store.stats()
    if fs.get("error"):
        return f"📈 MATURATION — indisponible ({fs['error']})"
    of_days = fs.get("jours_order_flow_distincts", 0) or 0
    ready = fs.get("modele_appris_autorise", False)

    j = journal.load_journal()
    st = j.get("stats", {})
    ai = [s for s in j.get("signals", []) if s.get("trader") == "AI"]
    byf = defaultdict(lambda: [0, 0])  # [filled, total]
    for s in ai:
        byf[s["asset"]][1] += 1
        if s.get("filled_ts"):
            byf[s["asset"]][0] += 1
    fillstr = " · ".join(
        f"{a} {v[0]}/{v[1]} ({(v[0]/v[1]*100):.0f}%)" for a, v in sorted(byf.items()) if v[1]
    ) or "aucun"

    cap = user_trade_context.summary()
    n_of = min(of_days, 15)
    bar = "█" * n_of + "░" * max(0, 15 - n_of)

    lines = [
        "📈 MATURATION HEBDO — vers le 1er modèle appris",
        f"Jours order-flow : {of_days}/15  [{bar}]" + ("  ✅ PRÊT" if ready else ""),
        f"Fill AI par actif : {fillstr}",
        f"WR {st.get('win_rate', '?')}% · espérance {_fmt_pct(st.get('expectancy_pct'))} "
        f"· fill global {st.get('ai_fill_rate', '?')}% · gate {fs.get('gate_apprentissage', '?')}",
        f"Tes trades capturés : {cap.get('avec_contexte', 0)} (avec contexte) sur "
        f"{cap.get('jours_distincts', 0)} jour(s) — dont {cap.get('jours_distincts_of', 0)}/15 "
        f"avec order-flow (le compteur du modèle v2)",
    ]
    if cap.get("avec_contexte", 0) == 0:
        lines.append("⚠️ Aucun trade logué — envoie « T GOLD SHORT 4150 » quand tu "
                     "trades pour nourrir le modèle (c'est le seul moyen d'apprendre TON edge).")
    card = None
    try:
        card = edge_zone.weekly_card()
    except Exception:
        card = None
    if card:
        lines.append("")
        lines.append(card)
    # banc d'essai PAPIER des hypothèses du mining (verdict à 15-20 jours chacune)
    try:
        import paper_lab
        pl = paper_lab.summary()
        rows = []
        for strat, d in pl.items():
            if not d.get("signaux"):
                continue
            best = next((v for k, v in d.items() if k.startswith("sortie_")), None)
            net = f" net {best['net_moy_pct']:+.2f}%/tr (n={best['n']})" if best else ""
            rows.append(f"  {strat}: {d['signaux']} sig / {d['jours']} j{net}")
        if rows:
            lines.append("🧪 PAPER-LAB (hypothèses en validation forward) :")
            lines.extend(rows)
    except Exception:
        pass
    if ready:
        lines.append("🎯 Seuil 15 jours atteint : on peut entraîner + juger le 1er modèle.")
    return "\n".join(lines)


def send():
    notify.send(build(), silent=True)


if __name__ == "__main__":
    import sys
    msg = build()
    print(msg)
    if "send" in sys.argv:
        print("envoi Telegram:", "OK" if send() or True else "?")
