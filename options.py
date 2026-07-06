#!/usr/bin/env python3
"""
OPTIONS, Positionnement options (CBOE, gratuit) → aimants & murs du cours
══════════════════════════════════════════════════════════════════
Données CBOE (la bourse d'options source, meilleur que TradingView pour ça) :
  • MAX PAIN : le strike où le max d'options expire sans valeur = AIMANT (les MM
    poussent le cours vers là à l'expiration)
  • MURS D'OPEN INTEREST : call wall = résistance · put wall = support (défendus par dealers)
  • PUT/CALL ratio : sentiment (peur vs greed)
  • GEX (gamma exposure) : dealers long gamma = cours ÉPINGLÉ/mean-revert ;
    short gamma = mouvements AMPLIFIÉS (volatilité)
  • IV : prix de la peur

GLD = proxy or (converti en prix or via le ratio live). SPX = S&P direct.
"""
import urllib.request, json, datetime, re

CBOE = "https://cdn.cboe.com/api/global/delayed_quotes/options/{}.json"


def _get(url, timeout=12):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return json.loads(urllib.request.urlopen(req, timeout=timeout).read().decode())


def _parse(sym):
    """GLD260605C00404000 → (expiry date, 'C'/'P', strike float)."""
    m = re.match(r"^[A-Z]+(\d{6})([CP])(\d{8})$", sym)
    if not m:
        return None
    exp = "20" + m.group(1)[:2] + "-" + m.group(1)[2:4] + "-" + m.group(1)[4:6]
    return exp, m.group(2), int(m.group(3)) / 1000


def fetch(symbol):
    d = _get(CBOE.format(symbol))
    data = d["data"]
    spot = data.get("current_price")
    opts = []
    for o in data["options"]:
        p = _parse(o["option"])
        if not p:
            continue
        exp, typ, strike = p
        opts.append({"exp": exp, "type": typ, "strike": strike,
                     "oi": o.get("open_interest", 0) or 0, "vol": o.get("volume", 0) or 0,
                     "iv": o.get("iv", 0) or 0, "gamma": o.get("gamma", 0) or 0})
    return spot, opts


def max_pain(opts):
    """Strike qui minimise la valeur payée par les writers = aimant."""
    strikes = sorted(set(o["strike"] for o in opts if o["oi"] > 0))
    if not strikes:
        return None
    best, best_pain = None, None
    for S in strikes:
        pain = 0
        for o in opts:
            if o["type"] == "C" and S > o["strike"]:
                pain += o["oi"] * (S - o["strike"])
            elif o["type"] == "P" and S < o["strike"]:
                pain += o["oi"] * (o["strike"] - S)
        if best_pain is None or pain < best_pain:
            best_pain, best = pain, S
    return best


def analyze(symbol, to_underlying=1.0, near_only=True, prefetched=None):
    """
    Analyse le positionnement options. to_underlying = facteur conversion strike→prix
    sous-jacent (ex GLD→or). Retourne aimants/murs/sentiment. prefetched=(spot, opts)
    évite un 2e fetch réseau quand l'appelant a déjà la chaîne (cf. gold_options).
    """
    spot, opts = prefetched if prefetched is not None else fetch(symbol)
    if not opts:
        return None
    today = datetime.date.today().isoformat()
    future = [o for o in opts if o["exp"] >= today]
    exps = sorted(set(o["exp"] for o in future))
    # Expiration de référence : la prochaine avec OI significatif
    near = exps[0] if exps else None
    if near_only and near:
        # agrège les 2 prochaines expirations (front weeklies)
        keep = exps[:2]
        future = [o for o in future if o["exp"] in keep]

    calls = [o for o in future if o["type"] == "C"]
    puts = [o for o in future if o["type"] == "P"]
    tot_call_oi = sum(o["oi"] for o in calls)
    tot_put_oi = sum(o["oi"] for o in puts)
    pcr = round(tot_put_oi / tot_call_oi, 2) if tot_call_oi else None

    mp = max_pain(future)
    # Murs (plus gros OI)
    call_wall = max(calls, key=lambda o: o["oi"], default=None)
    put_wall = max(puts, key=lambda o: o["oi"], default=None)

    # GEX net (signe : call +, put -) → régime
    gex = sum(o["gamma"] * o["oi"] * (1 if o["type"] == "C" else -1) for o in future)

    # IV moyenne (proche de la monnaie)
    atm = [o for o in future if abs(o["strike"] - spot) / spot < 0.03 and o["iv"] > 0]
    iv = round(sum(o["iv"] for o in atm) / len(atm) * 100, 1) if atm else None

    def conv(x):
        return round(x * to_underlying, 1) if x else None

    return {
        "symbol": symbol, "spot": spot, "spot_underlying": conv(spot),
        "expiries": exps[:3], "factor": to_underlying,
        "max_pain": mp, "max_pain_u": conv(mp),
        "call_wall": call_wall["strike"] if call_wall else None,
        "call_wall_u": conv(call_wall["strike"]) if call_wall else None,
        "call_wall_oi": call_wall["oi"] if call_wall else None,
        "put_wall": put_wall["strike"] if put_wall else None,
        "put_wall_u": conv(put_wall["strike"]) if put_wall else None,
        "put_wall_oi": put_wall["oi"] if put_wall else None,
        "pcr": pcr, "iv": iv, "gex": round(gex, 1),
        "gex_regime": "ÉPINGLÉ (dealers long gamma, mean-revert)" if gex > 0
                      else "AMPLIFIÉ (short gamma, volatilité)",
    }


def gold_options(gold_price=None):
    """Options or via GLD, converties en prix or."""
    spot, opts = fetch("GLD")
    factor = (gold_price / spot) if (gold_price and spot) else 10.86
    return analyze("GLD", to_underlying=factor, prefetched=(spot, opts))


def spx_options():
    return analyze("_SPX", to_underlying=1.0)


if __name__ == "__main__":
    print("═══ OPTIONS OR (via GLD) ═══")
    g = gold_options(4305)
    if g:
        print(f"  Spot or ~${g['spot_underlying']} (GLD {g['spot']}) · facteur {g['factor']:.2f}")
        print(f"  🎯 MAX PAIN : ${g['max_pain_u']} (aimant à l'expiration)")
        print(f"  🟥 CALL WALL (résistance) : ${g['call_wall_u']} (OI {g['call_wall_oi']})")
        print(f"  🟩 PUT WALL (support) : ${g['put_wall_u']} (OI {g['put_wall_oi']})")
        print(f"  Put/Call OI : {g['pcr']} · IV {g['iv']}% · GEX {g['gex']} → {g['gex_regime']}")
    print("\n═══ OPTIONS S&P (SPX) ═══")
    s = spx_options()
    if s:
        print(f"  Spot {s['spot']}")
        print(f"  🎯 MAX PAIN : {s['max_pain']} · 🟥 CALL WALL {s['call_wall']} · 🟩 PUT WALL {s['put_wall']}")
        print(f"  Put/Call OI : {s['pcr']} · IV {s['iv']}% · {s['gex_regime']}")
