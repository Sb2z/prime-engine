#!/usr/bin/env python3
"""Migration one-shot : marque les doublons IA existants dans journal.json.

Backup horodaté avant écriture. Persiste duplicate_of ; les doublons encore
OPEN passent en status DUPLICATE (ils ne seront plus évalués, la racine l'est).
Les signaux CLOSED gardent leur status, duplicate_of suffit à les exclure.
"""

import datetime
import json
import shutil

import clusters

JOURNAL_FILE = clusters.JOURNAL_FILE


def main():
    backup = JOURNAL_FILE.replace(
        ".json", f".pre_dedup.{datetime.datetime.now():%Y%m%d_%H%M%S}.json"
    )
    shutil.copy2(JOURNAL_FILE, backup)
    print(f"Backup: {backup}")

    with open(JOURNAL_FILE) as f:
        j = json.load(f)

    before = clusters.effective_trades(json.loads(json.dumps(j)))
    clusters.annotate(j)

    n_dup, n_open_dup = 0, 0
    for t in j.get("signals", []):
        if t.get("duplicate_of"):
            n_dup += 1
            if t.get("status") == "OPEN":
                t["status"] = "DUPLICATE"
                n_open_dup += 1

    with open(JOURNAL_FILE, "w") as f:
        json.dump(j, f, indent=2)

    eff = clusters.effective_trades(j)
    eff_ai = [t for t in eff if clusters.is_ai(t)]
    raw_ai = [
        t for t in j["signals"]
        if clusters.is_ai(t) and t.get("result") in clusters.DECISIVE
    ]
    ote_raw = [t for t in raw_ai if t.get("strategy") == "OTE_RETRACEMENT"]
    ote_eff = [t for t in eff_ai if t.get("strategy") == "OTE_RETRACEMENT"]
    print(f"Doublons marqués: {n_dup} (dont {n_open_dup} OPEN → DUPLICATE)")
    print(f"IA décisifs : brut {len(raw_ai)} → effectif {len(eff_ai)}")
    print(f"OTE         : brut {len(ote_raw)} → effectif {len(ote_eff)}")


if __name__ == "__main__":
    main()
