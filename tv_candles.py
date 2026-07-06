#!/usr/bin/env python3
"""
TradingView WebSocket — Streaming bougies 1H + calcul TA
Bypasse totalement la REST API rate-limitée de tradingview-ta.
Même protocole WebSocket que tv_live.py, mais avec chart session.
"""

import websocket, json, random, string, threading, time, sys
import pandas as pd
import ta
import tz

TV_WS_URL  = "wss://data.tradingview.com/socket.io/websocket?from=chart%2F"
TV_WS_PATH = "/socket.io/websocket?from=chart%2F"
TV_HEADERS = {
    "Origin":     "https://www.tradingview.com",
    "User-Agent": ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                   "AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36"),
}

# Mapping timeframe → TradingView interval string
TF_MAP = {"1m":"1","5m":"5","15m":"15","30m":"30","1h":"60","4h":"240","1d":"1D"}

def rand_id(prefix="", n=12):
    return prefix + "".join(random.choices(string.ascii_lowercase, k=n))

def pack(func, params):
    msg = json.dumps({"m": func, "p": params}, separators=(",",":"))
    return f"~m~{len(msg)}~m~{msg}"

def unpack(raw):
    if isinstance(raw, bytes): raw = raw.decode("utf-8", errors="ignore")
    out, i = [], 0
    while i < len(raw):
        if not raw[i:].startswith("~m~"): break
        i += 3
        try:
            end = raw.index("~m~", i); length = int(raw[i:end]); i = end+3
            out.append(raw[i:i+length]); i += length
        except (ValueError, IndexError): break
    return out

# ── Symboles TradingView (chart session format) ───────────────────────────────
SYMBOL_MAP = {
    "GOLD":   "TVC:GOLD",
    "OIL":    "TVC:USOIL",
    "BTC":    "BINANCE:BTCUSDT",
    "ETH":    "BINANCE:ETHUSDT",
    "US500":  "CAPITALCOM:US500",
    "NAS100": "CAPITALCOM:US100",
    # Macro corrélés
    "SILVER": "TVC:SILVER",
    "DXY":    "TVC:DXY",
    "US10Y":  "TVC:US10Y",
    "VIX":    "TVC:VIX",
    # Term structure volatilité (SENTINEL-500)
    "VIX3M":  "CBOE:VIX3M",
    "VIX9D":  "CBOE:VIX9D",
    "VVIX":   "CBOE:VVIX",
    # Breadth / participation
    "RUT":    "TVC:RUT",
    "DJI":    "TVC:DJI",
    "RSP":    "AMEX:RSP",
}

# ── Client WebSocket candles ───────────────────────────────────────────────────
class TVCandleClient:
    def __init__(self, symbols=None, timeframe="1h", n_bars=100, timeout=35):
        self.symbols   = symbols or list(SYMBOL_MAP.keys())
        self.tf        = TF_MAP.get(timeframe, "60")
        self.n_bars    = n_bars
        self.timeout   = timeout
        # Une chart session PAR symbole (limite TradingView free = 1 série/session)
        self._sessions = {}   # cs_id → name
        self._candles  = {}   # name  → list of [ts, o, h, l, c, v]
        self._ready    = {}   # name  → bool
        self._done     = threading.Event()
        self._ws       = None
        self._ws_url   = TV_WS_URL
        self._redirect = None

    # ── Setup ─────────────────────────────────────────────────────────────────
    def _on_open(self, ws):
        ws.send(pack("set_auth_token", ["unauthorized_user_token"]))
        for name in self.symbols:
            tv_sym = SYMBOL_MAP.get(name, name)
            cs_id  = "cs_" + rand_id()
            self._sessions[cs_id] = name
            self._ready[name]     = False
            ws.send(pack("chart_create_session", [cs_id, ""]))
            time.sleep(0.15)
            ws.send(pack("resolve_symbol", [cs_id, "sym1",
                         f'={{"symbol":"{tv_sym}","adjustment":"splits"}}']))
            time.sleep(0.1)
            ws.send(pack("create_series", [cs_id, "s1", "s1", "sym1",
                         self.tf, self.n_bars]))

    def _on_message(self, ws, message):
        if isinstance(message, bytes):
            message = message.decode("utf-8", errors="ignore")
        if message.startswith("~h~"):
            ws.send(f"~m~{len(message)}~m~{message}")
            return

        # Redirect TradingView (serveur régional)
        for pkt in unpack(message):
            try:
                obj = json.loads(pkt)
                if isinstance(obj, dict) and obj.get("redirect"):
                    self._redirect = f"wss://{obj['redirect']}{TV_WS_PATH}"
                    ws.close()
                    return
            except Exception:
                pass

        for pkt in unpack(message):
            try:
                obj = json.loads(pkt)
            except Exception:
                continue
            if not isinstance(obj, dict): continue
            m = obj.get("m","")

            # ── Bougies historiques ────────────────────────────────────────
            if m == "timescale_update":
                p = obj.get("p", [])
                if len(p) < 2: continue
                cs_id = p[0]
                name  = self._sessions.get(cs_id)
                if not name: continue
                bars = p[1].get("s1", {}).get("s", [])
                if bars:
                    self._candles[name] = [b["v"] for b in bars if "v" in b]
                    self._ready[name]   = True

            # ── Tick temps réel ───────────────────────────────────────────
            if m == "du":
                p = obj.get("p", [])
                if len(p) < 2: continue
                cs_id = p[0]
                name  = self._sessions.get(cs_id)
                if not name or name not in self._candles: continue
                bars = p[1].get("s1", {}).get("s", [])
                if bars:
                    last = bars[-1]["v"]
                    if self._candles[name][-1][0] == last[0]:
                        self._candles[name][-1] = last
                    else:
                        self._candles[name].append(last)

            # Vérifie si tout est prêt
            if all(self._ready.get(s, False) for s in self.symbols):
                self._done.set()

    def _on_error(self, ws, e): pass
    def _on_close(self, ws, *a): self._done.set()

    # ── TA Calculation ────────────────────────────────────────────────────────
    def _calc_ta(self, candles):
        return compute_ta(candles)


    # ── Public API ─────────────────────────────────────────────────────────────
    def _stream(self):
        """Connecte au WebSocket, gère le redirect régional, remplit self._candles."""
        for attempt in range(3):
            self._redirect = None
            self._done.clear()
            self._sessions = {}
            self._candles  = {}
            self._ready    = {}
            url = self._ws_url

            self._ws = websocket.WebSocketApp(
                url, header=TV_HEADERS,
                on_open=self._on_open, on_message=self._on_message,
                on_error=self._on_error, on_close=self._on_close,
            )
            t = threading.Thread(
                target=self._ws.run_forever,
                kwargs={"skip_utf8_validation": True},
                daemon=True
            )
            t.start()
            self._done.wait(timeout=self.timeout)
            self._ws.close()
            t.join(timeout=2)

            # Si au moins un symbole a des données → succès
            if any(self._candles.get(n) for n in self.symbols):
                break

            # Redirect reçu → réessayer sur le nouveau serveur
            if self._redirect:
                self._ws_url = self._redirect
                continue

            break

    def fetch_ta(self) -> dict:
        """Stream les bougies puis calcule les indicateurs TA."""
        self._stream()
        results = {}
        for name in self.symbols:
            candles = self._candles.get(name, [])
            if candles:
                ta_data = self._calc_ta(candles)
                if ta_data:
                    results[name] = ta_data
                else:
                    results[name] = {"error": "not_enough_data"}
            else:
                results[name] = {"error": "no_candles"}
        return results

    def fetch_candles(self) -> dict:
        """Stream et retourne les bougies brutes [ts, o, h, l, c, v] par actif."""
        self._stream()
        return {name: list(self._candles.get(name, [])) for name in self.symbols}


def compute_ta(candles):
    """Calcule les indicateurs TA sur une liste de bougies OHLCV."""
    if len(candles) < 30:
        return None
    cols = ["ts","open","high","low","close","volume"]
    df = pd.DataFrame(candles, columns=cols[:len(candles[0])])
    df = df.sort_values("ts").reset_index(drop=True)
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    df["high"]  = pd.to_numeric(df["high"],  errors="coerce")
    df["low"]   = pd.to_numeric(df["low"],   errors="coerce")
    df["volume"]= pd.to_numeric(df["volume"],errors="coerce").fillna(0)
    df = df.dropna(subset=["close","high","low"])
    if len(df) < 20: return None

    close = df["close"]
    high  = df["high"]
    low   = df["low"]
    vol   = df["volume"]

    # RSI(14)
    rsi = ta.momentum.RSIIndicator(close, window=14).rsi().iloc[-1]

    # ADX(14) + DI+/-
    adx_ind   = ta.trend.ADXIndicator(high, low, close, window=14)
    adx       = adx_ind.adx().iloc[-1]
    di_plus   = adx_ind.adx_pos().iloc[-1]
    di_minus  = adx_ind.adx_neg().iloc[-1]

    # EMA 20/50
    ema20 = ta.trend.EMAIndicator(close, window=20).ema_indicator().iloc[-1]
    ema50 = ta.trend.EMAIndicator(close, window=50).ema_indicator().iloc[-1]

    # MACD(12,26,9)
    macd_ind  = ta.trend.MACD(close, window_slow=26, window_fast=12, window_sign=9)
    macd      = macd_ind.macd().iloc[-1]
    macd_sig  = macd_ind.macd_signal().iloc[-1]

    # Stochastic(14,3)
    stoch     = ta.momentum.StochasticOscillator(high, low, close, window=14, smooth_window=3)
    stoch_k   = stoch.stoch().iloc[-1]
    stoch_d   = stoch.stoch_signal().iloc[-1]

    # Signal composite (imite tradingview-ta)
    buy = sell = neutral = 0
    # RSI
    if rsi > 70: sell += 1
    elif rsi < 30: buy += 1
    else: neutral += 1
    # MACD
    if macd > macd_sig: buy += 2
    else: sell += 2
    # ADX + DI
    if adx > 20:
        if di_plus > di_minus: buy += 2
        else: sell += 2
    else: neutral += 2
    # EMA
    lp = close.iloc[-1]
    if lp > ema20: buy += 1
    else: sell += 1
    if lp > ema50: buy += 1
    else: sell += 1
    # Stoch
    if stoch_k > 80: sell += 1
    elif stoch_k < 20: buy += 1
    else: neutral += 1

    total = buy + sell + neutral
    if buy > sell * 1.5:   rec = "STRONG_BUY" if buy > 10 else "BUY"
    elif sell > buy * 1.5: rec = "STRONG_SELL" if sell > 10 else "SELL"
    else:                  rec = "NEUTRAL"

    return {
        "rec":      rec,
        "buy":      buy, "sell": sell, "neutral": neutral,
        "close":    round(float(lp), 4),
        "rsi":      round(float(rsi), 1),
        "adx":      round(float(adx), 1),
        "di_plus":  round(float(di_plus), 1),
        "di_minus": round(float(di_minus), 1),
        "stoch_k":  round(float(stoch_k), 1),
        "stoch_d":  round(float(stoch_d), 1),
        "ema20":    round(float(ema20), 4),
        "ema50":    round(float(ema50), 4),
        "macd":     round(float(macd), 4),
        "macd_sig": round(float(macd_sig), 4),
        "n_bars":   len(df),
        "from_cache": False,
    }


# ── Test direct ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import datetime
    paris = tz.paris_now()
    print(f"\n📊 TA via WebSocket TradingView — {paris.strftime('%H:%M:%S')} Paris\n")

    client  = TVCandleClient(timeout=25)
    results = client.fetch_ta()

    for name, d in results.items():
        if "error" in d:
            print(f"  {name:8}: ⚠️  {d['error']}")
        else:
            bar = "█" * int(d['rsi']/10) + "░" * (10 - int(d['rsi']/10))
            ob  = " ⚠️OB" if d['stoch_k']>80 else (" ⚠️OS" if d['stoch_k']<20 else "")
            print(f"  {name:8} {d['rec']:12} RSI={d['rsi']:5.1f} [{bar}] "
                  f"ADX={d['adx']:5.1f} StochK={d['stoch_k']:5.1f}{ob} "
                  f"MACD={'▲' if d['macd']>d['macd_sig'] else '▼'} "
                  f"({d['n_bars']} bougies)")
