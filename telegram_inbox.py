#!/usr/bin/env python3
"""
TELEGRAM INBOX — écoute les messages de Sam pour capturer le contexte d'un trade.
═══════════════════════════════════════════════════════════════════════════════
Sam écrit au bot, au moment où il trade : « T GOLD SHORT 4150 » (T ou TRADE,
alias tolérés). Le bot apparie ce trade au contexte feature_store de l'INSTANT du
message (heure RÉELLE Telegram) via user_trade_context.capture(), puis confirme.

SÉCURITÉ : ne traite QUE les messages du TELEGRAM_CHAT_ID configuré (le chat de
Sam) ; le parsing est 100% CODE (regex), aucune entrée n'atteint un LLM -> pas
de surface d'injection. Lecture seule de la base (via user_trade_context).

Appelé une fois par cycle par prime_watcher (getUpdates court, non bloquant).
"""
import datetime as dt
import json
import os
import re
import urllib.request

import edge_zone
import notify
import user_trade_context

STATE = "/Users/sam/trading/telegram_inbox_state.json"

_ASSET = {"GOLD": "GOLD", "XAU": "GOLD", "OR": "GOLD", "GC": "GOLD",
          "US500": "US500", "SPX": "US500", "SP500": "US500", "SP": "US500", "S&P": "US500"}
_DIR = {"SHORT": "SHORT", "SELL": "SHORT", "S": "SHORT", "VENDRE": "SHORT",
        "LONG": "LONG", "BUY": "LONG", "L": "LONG", "ACHAT": "LONG", "ACHETER": "LONG"}
# « T|TRADE  <actif>  <sens>  <prix> »
_RE = re.compile(r"^\s*(?:T|TRADE)\s+([A-Za-z&]+)\s+([A-Za-z]+)\s+([\d]+[.,]?\d*)\s*$", re.I)
# « Z|ZONE  <actif>  <sens> » : verdict zone edge À LA DEMANDE (AVANT d'entrer),
# sans rien capturer — l'outil de discipline pré-trade.
_RE_ZONE = re.compile(r"^\s*(?:Z|ZONE)\s+([A-Za-z&]+)\s+([A-Za-z]+)\s*$", re.I)


def parse(text):
    """-> (asset, direction, entry) ou None. Tolérant aux alias, insensible à la casse."""
    m = _RE.match(text or "")
    if not m:
        return None
    a = _ASSET.get(m.group(1).upper())
    d = _DIR.get(m.group(2).upper())
    try:
        e = float(m.group(3).replace(",", "."))
    except ValueError:
        return None
    return (a, d, e) if (a and d and e > 0) else None


def parse_zone(text):
    """-> (asset, direction) ou None — demande de verdict sans capture."""
    m = _RE_ZONE.match(text or "")
    if not m:
        return None
    a = _ASSET.get(m.group(1).upper())
    d = _DIR.get(m.group(2).upper())
    return (a, d) if (a and d) else None


def _offset():
    try:
        return int(json.load(open(STATE)).get("offset", 0))
    except Exception:
        return 0


def _set_offset(o):
    # atomique (tmp + os.replace) : un crash mi-écriture corromprait le state,
    # _offset() retomberait à 0 et getUpdates re-livrerait -> captures DUPLIQUÉES.
    try:
        tmp = STATE + ".tmp"
        with open(tmp, "w") as f:
            json.dump({"offset": int(o)}, f)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, STATE)
    except Exception:
        pass


def poll_and_capture(timeout=8):
    """getUpdates court, capture chaque commande de trade valide du chat de Sam.
    Jamais bloquant/jamais d'exception propagée. Retourne la liste des captures."""
    token = notify._key("TELEGRAM_BOT_TOKEN")
    chat = notify._key("TELEGRAM_CHAT_ID")
    if not (token and chat):
        return []
    captured = []
    try:
        url = (f"https://api.telegram.org/bot{token}/getUpdates"
               f"?offset={_offset() + 1}&timeout=0&allowed_updates=%5B%22message%22%5D")
        with urllib.request.urlopen(url, timeout=timeout) as r:
            data = json.loads(r.read().decode())
        if not data.get("ok"):
            return []
        for upd in data.get("result", []):
            # offset avancé en FIN de traitement (finally) : plus jamais un trade
            # logué perdu EN SILENCE si capture() lève (parquet en cours d'export…).
            try:
                msg = upd.get("message") or {}
                if str((msg.get("chat") or {}).get("id")) != str(chat):
                    continue  # SÉCURITÉ : uniquement le chat de Sam
                # verdict zone À LA DEMANDE (« Z GOLD SHORT ») : répond, ne capture rien
                zq = parse_zone(msg.get("text", ""))
                if zq:
                    a, d = zq
                    ctx = edge_zone.live_context(a) or {}
                    v = edge_zone.assess(a, d, ctx)
                    notify.send(f"❓ {a} {d} — maintenant ?\n"
                                + edge_zone.format_verdict(a, d, v), silent=True)
                    continue
                parsed = parse(msg.get("text", ""))
                if not parsed:
                    continue
                a, d, e = parsed
                ts = dt.datetime.fromtimestamp(int(msg.get("date") or 0), dt.timezone.utc)
                rec = user_trade_context.capture(a, d, e, ts=ts, note="telegram")
                captured.append(rec)
                ctx = rec.get("context") or {}
                age = rec.get("context_age_min")
                if ctx and (age is not None and age <= 30):
                    txt = (
                        f"✅ Trade capturé : {a} {d} @{e}\n"
                        f"contexte t-{age}min : grade={ctx.get('grade')} conf={ctx.get('conf')} "
                        f"of_imb={ctx.get('of_imbalance')} of_poc={ctx.get('of_poc_dist')} "
                        f"session={ctx.get('session')} régime={ctx.get('regime')}")
                    try:  # verdict zone edge (discipline) — ne bloque jamais la capture
                        txt += "\n\n" + edge_zone.format_verdict(a, d, edge_zone.assess(a, d, ctx))
                    except Exception:
                        pass
                    notify.send(txt, silent=True)
                else:
                    notify.send(
                        f"⚠️ Trade {a} {d} @{e} enregistré mais contexte ABSENT/périmé "
                        f"(âge {age}min — marché fermé ou bot inactif à cet instant ?).", silent=True)
            except Exception:
                # perte non-silencieuse : Sam est prévenu et peut re-loguer
                try:
                    notify.send("⚠️ Capture échouée sur ton dernier message trade — "
                                "re-logue-le (ex : T GOLD SHORT 4150).", silent=False)
                except Exception:
                    pass
            finally:
                _set_offset(upd["update_id"])
    except Exception:
        pass
    return captured


if __name__ == "__main__":
    # PAS de poll réel ici : deux getUpdates concurrents (watcher + run manuel)
    # se volent les updates (offset) -> captures perdues/dupliquées. Le poll ne
    # doit passer QUE par prime_watcher. Ce main = auto-test du parseur.
    import sys
    if sys.argv[1:]:
        print(parse(" ".join(sys.argv[1:])))
    else:
        for t in ("T GOLD SHORT 4150", "trade xau s 4150,5", "T SP L 7450", "bonjour"):
            print(f"  {t!r:28s} -> {parse(t)}")
