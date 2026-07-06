#!/usr/bin/env python3
"""
TradingView WebSocket Client — Prix T0 via le même flux que ton navigateur
Usage : python3 tv_live.py [--symbols NASDAQ:AVGO,NASDAQ:TSLA] [--timeout 12] [--json]
"""

import websocket
import json
import random
import string
import threading
import time
import sys
import argparse
import datetime
import tz

# ── Config ─────────────────────────────────────────────────────────────────────
TV_WS_URL  = "wss://data.tradingview.com/socket.io/websocket?from=chart%2F"
TV_WS_PATH = "/socket.io/websocket?from=chart%2F"
TV_HEADERS = {
    "Origin":     "https://www.tradingview.com",
    "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) "
                   "Chrome/124.0.0.0 Safari/537.36"),
}

DEFAULT_SYMBOLS = [
    "NASDAQ:AVGO", "NASDAQ:TSLA", "NASDAQ:NVDA",
    "NASDAQ:AAPL", "NASDAQ:META", "NASDAQ:AMD",
    "NASDAQ:MU",   "AMEX:SPY",   "NASDAQ:QQQ",
]

PRICE_FIELDS = {"lp", "ch", "chp", "volume",
                "high_price", "low_price", "open_price",
                "prev_close_price", "bid", "ask"}

# ── Protocole TradingView ──────────────────────────────────────────────────────
def rand_session(prefix="qs_"):
    return prefix + "".join(random.choices(string.ascii_lowercase, k=12))

def pack(func, params):
    msg = json.dumps({"m": func, "p": params}, separators=(",", ":"))
    return f"~m~{len(msg)}~m~{msg}"

def unpack(raw):
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", errors="ignore")
    packets, i = [], 0
    while i < len(raw):
        if not raw[i:].startswith("~m~"):
            break
        i += 3
        try:
            end    = raw.index("~m~", i)
            length = int(raw[i:end])
            i      = end + 3
            packets.append(raw[i:i + length])
            i += length
        except (ValueError, IndexError):
            break
    return packets

# ── Client ─────────────────────────────────────────────────────────────────────
class TVLiveClient:
    def __init__(self, symbols=None, timeout=12):
        self.symbols   = symbols or DEFAULT_SYMBOLS
        self.timeout   = timeout
        self.session   = rand_session()
        self.prices    = {}          # "AVGO" → {lp, chp, ch, ...}
        self._done     = threading.Event()
        self._ws       = None
        self._ws_url   = TV_WS_URL   # peut être mis à jour par redirect
        self._redirect = None

    def _expected(self):
        return {s.split(":")[-1] for s in self.symbols}

    def _complete(self):
        """Retourne True quand tous les symboles ont reçu un prix (lp != None)"""
        exp = self._expected()
        return all(
            self.prices.get(sym, {}).get("lp") is not None
            for sym in exp
        )

    # ── Callbacks ─────────────────────────────────────────────────────────────
    def _on_open(self, ws):
        ws.send(pack("set_auth_token",     ["unauthorized_user_token"]))
        ws.send(pack("quote_create_session", [self.session]))
        for sym in self.symbols:
            ws.send(pack("quote_add_symbols", [self.session, sym]))

    def _on_message(self, ws, message):
        if isinstance(message, bytes):
            message = message.decode("utf-8", errors="ignore")

        # Heartbeat TradingView
        if message.startswith("~h~"):
            ws.send(f"~m~{len(message)}~m~{message}")
            return

        # Redirect TradingView (serveur régional)
        for pkt in unpack(message):
            try:
                obj = json.loads(pkt)
                if isinstance(obj, dict) and obj.get("redirect"):
                    host = obj["redirect"]
                    self._redirect = f"wss://{host}{TV_WS_PATH}"
                    ws.close()
                    return
            except Exception:
                pass

        for pkt in unpack(message):
            try:
                obj = json.loads(pkt)
            except (json.JSONDecodeError, TypeError):
                continue

            if not isinstance(obj, dict) or obj.get("m") != "qsd":
                continue

            p = obj.get("p", [])
            if len(p) < 2:
                continue

            raw_sym = p[1].get("n", "")           # "NASDAQ:AVGO"
            sym_key = raw_sym.split(":")[-1]       # "AVGO"
            v       = p[1].get("v", {})

            # Merge les champs reçus dans self.prices[sym_key]
            if sym_key not in self.prices:
                self.prices[sym_key] = {}
            for field in PRICE_FIELDS:
                if field in v and v[field] is not None:
                    self.prices[sym_key][field] = v[field]

            if self._complete():
                self._done.set()

    def _on_error(self, ws, error):
        pass  # Erreurs WebSocket silencieuses (fermetures propres)

    def _on_close(self, ws, *a):
        self._done.set()

    # ── API publique ───────────────────────────────────────────────────────────
    def fetch(self) -> dict:
        """
        Se connecte au WebSocket TradingView, gère le redirect régional,
        collecte les prix T0, puis ferme proprement.
        """
        for attempt in range(3):
            self._redirect = None
            self._done.clear()
            url = self._ws_url
            self._ws = websocket.WebSocketApp(
                url,
                header       = TV_HEADERS,
                on_open      = self._on_open,
                on_message   = self._on_message,
                on_error     = self._on_error,
                on_close     = self._on_close,
            )
            t = threading.Thread(
                target = self._ws.run_forever,
                kwargs = {"skip_utf8_validation": True},
                daemon = True,
            )
            t.start()
            self._done.wait(timeout=self.timeout)
            self._ws.close()
            t.join(timeout=2)

            if self.prices:
                return self.prices   # succès

            # Redirect reçu → réessayer sur le nouveau serveur
            if self._redirect:
                self._ws_url = self._redirect
                self.session = rand_session()   # nouvelle session
                continue

            break   # pas de redirect, pas de données → abandon

        return self.prices


# ── Affichage ──────────────────────────────────────────────────────────────────
def paris_now():
    return tz.paris_now().strftime("%H:%M:%S")

def print_prices(prices: dict):
    ts = paris_now()
    print(f"\n{'─'*62}")
    print(f"  📡 TRADINGVIEW WebSocket T0 — {ts} Paris (UTC+2)")
    print(f"{'─'*62}")
    print(f"  {'SYM':<7} {'PRIX':>9}  {'CHG':>8}  {'CHG%':>7}  {'VOL':>10}  {'HIGH':>9}  {'LOW':>9}")
    print(f"  {'─'*58}")

    for sym in sorted(prices.keys()):
        d     = prices[sym]
        price = d.get("lp")
        ch    = d.get("ch")
        chp   = d.get("chp")
        vol   = d.get("volume")
        high  = d.get("high_price")
        low   = d.get("low_price")

        if price is None:
            print(f"  {sym:<7} {'N/A':>9}")
            continue

        chp_s = f"{chp:+.2f}%" if chp is not None else "  ---  "
        ch_s  = f"{ch:+.2f}"  if ch  is not None else "  ---"
        vol_s = f"{vol/1e6:.1f}M" if vol else "  ---"
        hi_s  = f"${high:.2f}" if high else " ---"
        lo_s  = f"${low:.2f}"  if low  else " ---"

        emoji = "🟢" if (chp or 0) > 0.2 else ("🔴" if (chp or 0) < -0.2 else "⚪")
        print(f"  {emoji} {sym:<5} ${price:>8.2f}  {ch_s:>8}  {chp_s:>7}  {vol_s:>10}  {hi_s:>9}  {lo_s:>9}")

    if prices:
        valid = {k: v for k, v in prices.items() if v.get("chp") is not None}
        if valid:
            top = max(valid.items(), key=lambda x: x[1]["chp"])
            bot = min(valid.items(), key=lambda x: x[1]["chp"])
            print(f"\n  🏆 Top gainer : {top[0]} {top[1]['chp']:+.2f}%  ${top[1].get('lp',0):.2f}")
            print(f"  📉 Top loser  : {bot[0]} {bot[1]['chp']:+.2f}%  ${bot[1].get('lp',0):.2f}")
    print(f"{'─'*62}\n")


# ── CLI ────────────────────────────────────────────────────────────────────────
def main():
    ap = argparse.ArgumentParser(description="TradingView WebSocket live feed")
    ap.add_argument("--symbols", default="",
                    help="Ex: NASDAQ:AVGO,NASDAQ:TSLA (défaut: 9 actifs Revolut)")
    ap.add_argument("--timeout", type=int, default=12)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    symbols = [s.strip() for s in args.symbols.split(",") if s.strip()] or DEFAULT_SYMBOLS
    prices  = TVLiveClient(symbols=symbols, timeout=args.timeout).fetch()

    if not prices:
        print("⚠️  Aucune donnée — vérifie ta connexion.", file=sys.stderr)
        sys.exit(1)

    if args.json:
        print(json.dumps(prices, indent=2))
    else:
        print_prices(prices)


if __name__ == "__main__":
    main()
