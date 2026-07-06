#!/usr/bin/env python3
"""TZ — heure de Paris DST-correcte, CENTRALISÉE.

Remplace le hack `datetime.now(utc) + timedelta(hours=2)` éparpillé dans le projet :
correct SEULEMENT en heure d'été (CEST = UTC+2), mais FAUX d'1 h en heure d'hiver
(CET = UTC+1), dès le dernier dimanche d'octobre. zoneinfo gère CET/CEST tout seul.

Deux primitives :
  • paris_now()  -> maintenant, en heure murale de Paris (aware).
  • to_paris(d)  -> convertit un datetime (aware, ou naïf supposé UTC) en heure de Paris.

Fallback +2h fixe si la base tz IANA est absente (ne devrait pas arriver : tzdata
présent sur ce poste) — uniquement pour ne jamais crasher.
"""
import datetime

try:
    from zoneinfo import ZoneInfo
    PARIS = ZoneInfo("Europe/Paris")
except Exception:  # pragma: no cover - tzdata absent
    PARIS = None


def paris_now():
    """Maintenant, en heure murale de Paris (aware), DST-correcte."""
    if PARIS is not None:
        return datetime.datetime.now(PARIS)
    return datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=2)


def to_paris(d):
    """Convertit un datetime en heure de Paris. Un datetime naïf est supposé UTC
    (convention du projet). Retourne un datetime aware en Europe/Paris."""
    if d.tzinfo is None:
        d = d.replace(tzinfo=datetime.timezone.utc)
    if PARIS is not None:
        return d.astimezone(PARIS)
    return d.astimezone(datetime.timezone.utc) + datetime.timedelta(hours=2)
