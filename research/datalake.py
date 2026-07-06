#!/usr/bin/env python3
"""DATA LAKE, données historiques du Research Lab (research/data/).

Sources gratuites, une source par fichier (garde anti-basis : le harness
refuse les tests mêlant des sources différentes) :
  • yfinance : 5 ans quotidien + 2 ans horaire (limite yfinance pour 60m)
    GC=F, ES=F, ^GSPC, DX-Y.NYB, ^VIX, ZN=F → parquet par ticker/timeframe
  • CFTC Socrata : 5 ans de COT hebdo GOLD/ES → parquet
  • Le tick Dukascopy XAUUSD est documenté mais NON téléchargé (plusieurs Go,
    dépendance node dédiée) : le feature store 1m qui s'accumule reste la
    source intraday fine de référence.

Usage : python3 research/datalake.py [refresh]
Le chercheur LIT ce lake ; le refresh est un job manuel/quotidien.
"""

import datetime as dt
import json
import os
import sys
import urllib.parse
import urllib.request

DATA_DIR = "/Users/sam/trading/research/data"
TICKERS = ["GC=F", "ES=F", "^GSPC", "DX-Y.NYB", "^VIX", "ZN=F"]
PLANS = [("1d", "5y"), ("1h", "730d")]
COT_WEEKS_5Y = 260
COT_MARKETS = {
    "GOLD": "GOLD - COMMODITY EXCHANGE INC.",
    "US500": "E-MINI S&P 500 - CHICAGO MERCANTILE EXCHANGE",
}


def _safe(ticker):
    return ticker.replace("=", "_").replace("^", "").replace("-", "_").replace(".", "_")


def refresh_yfinance():
    import yfinance as yf
    import pandas as pd
    os.makedirs(DATA_DIR, exist_ok=True)
    report = {}
    for ticker in TICKERS:
        for tf, period in PLANS:
            try:
                df = yf.Ticker(ticker).history(period=period,
                                               interval="1d" if tf == "1d" else "60m")
                if df is None or df.empty:
                    report[f"{ticker}:{tf}"] = "VIDE"
                    continue
                df = df.reset_index()
                ts_col = "Date" if "Date" in df.columns else "Datetime"
                out = pd.DataFrame({
                    "ts": df[ts_col].map(lambda x: x.timestamp()),
                    "open": df["Open"], "high": df["High"],
                    "low": df["Low"], "close": df["Close"],
                    "volume": df["Volume"].fillna(0),
                })
                path = os.path.join(DATA_DIR, f"{_safe(ticker)}_{tf}.parquet")
                out.to_parquet(path, index=False)
                report[f"{ticker}:{tf}"] = f"{len(out)} barres → {os.path.basename(path)}"
            except Exception as exc:
                report[f"{ticker}:{tf}"] = f"ERREUR {exc}"
    return report


def refresh_cot():
    import pandas as pd
    rows_all = []
    for asset, market in COT_MARKETS.items():
        params = urllib.parse.urlencode({
            "$select": "report_date_as_yyyy_mm_dd,noncomm_positions_long_all,"
                       "noncomm_positions_short_all,open_interest_all",
            "$where": f"market_and_exchange_names='{market}'",
            "$order": "report_date_as_yyyy_mm_dd DESC",
            "$limit": COT_WEEKS_5Y,
        })
        req = urllib.request.Request(
            f"https://publicreporting.cftc.gov/resource/6dca-aqww.json?{params}",
            headers={"User-Agent": "datalake/1.0"})
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read().decode())
        for row in data:
            try:
                rows_all.append({
                    "asset": asset,
                    "date": row["report_date_as_yyyy_mm_dd"][:10],
                    "net_specs": int(row["noncomm_positions_long_all"])
                                 - int(row["noncomm_positions_short_all"]),
                    "open_interest": int(row.get("open_interest_all") or 0),
                })
            except Exception:
                continue
    df = pd.DataFrame(rows_all)
    path = os.path.join(DATA_DIR, "cot_5y.parquet")
    df.to_parquet(path, index=False)
    return {"cot": f"{len(df)} lignes ({df['asset'].value_counts().to_dict()}) → cot_5y.parquet"}


def load_candles(ticker, tf):
    """Bougies [ts,o,h,l,c,v] + source, format harness."""
    import pandas as pd
    path = os.path.join(DATA_DIR, f"{_safe(ticker)}_{tf}.parquet")
    df = pd.read_parquet(path)
    candles = df[["ts", "open", "high", "low", "close", "volume"]].values.tolist()
    return candles, "yfinance"


def load_cot():
    import pandas as pd
    return pd.read_parquet(os.path.join(DATA_DIR, "cot_5y.parquet"))


def coverage():
    out = {}
    for f in sorted(os.listdir(DATA_DIR)) if os.path.isdir(DATA_DIR) else []:
        if f.endswith(".parquet"):
            out[f] = f"{os.path.getsize(os.path.join(DATA_DIR, f)) // 1024} Ko"
    return out


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "refresh":
        rep = refresh_yfinance()
        rep.update(refresh_cot())
        for k, v in rep.items():
            print(f"  {k:14} {v}")
    print(json.dumps(coverage(), indent=1))
