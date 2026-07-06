#!/usr/bin/env python3
"""TEST tz — la preuve DST : Paris = UTC+1 en hiver (CET), UTC+2 en été (CEST).
C'est exactement ce que le hack `+2h` fixe ratait en hiver."""
import datetime
import tz

FAIL = []


def chk(n, ok, d=""):
    print(f"  {'PASS' if ok else 'FAIL'}  {n}" + (f" — {d}" if d else ""))
    if not ok:
        FAIL.append(n)


utc = datetime.timezone.utc
jan = datetime.datetime(2026, 1, 15, 12, 0, tzinfo=utc)   # hiver
jul = datetime.datetime(2026, 7, 15, 12, 0, tzinfo=utc)   # été

chk("hiver : UTC 12:00 -> Paris 13:00 (CET, +1)", tz.to_paris(jan).hour == 13, str(tz.to_paris(jan)))
chk("été : UTC 12:00 -> Paris 14:00 (CEST, +2)", tz.to_paris(jul).hour == 14, str(tz.to_paris(jul)))
chk("datetime naïf supposé UTC", tz.to_paris(datetime.datetime(2026, 7, 15, 12, 0)).hour == 14)
chk("to_paris préserve l'INSTANT (même epoch)", tz.to_paris(jan).timestamp() == jan.timestamp())
chk("paris_now() est aware", tz.paris_now().tzinfo is not None)
# l'epoch de minuit-Paris (usage market_brief) est correct via .timestamp()
midnight = tz.to_paris(jul).replace(hour=0, minute=0, second=0, microsecond=0)
chk("minuit-Paris été -> 22:00 UTC la veille", datetime.datetime.fromtimestamp(midnight.timestamp(), utc).hour == 22,
    str(datetime.datetime.fromtimestamp(midnight.timestamp(), utc)))
midnight_w = tz.to_paris(jan).replace(hour=0, minute=0, second=0, microsecond=0)
chk("minuit-Paris hiver -> 23:00 UTC la veille", datetime.datetime.fromtimestamp(midnight_w.timestamp(), utc).hour == 23,
    str(datetime.datetime.fromtimestamp(midnight_w.timestamp(), utc)))

print()
if FAIL:
    print(f"X ÉCHEC(S): {FAIL}")
    raise SystemExit(1)
print("OK — tz.py DST-correct (hiver CET / été CEST).")
