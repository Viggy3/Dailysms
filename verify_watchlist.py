"""
verify_watchlist.py — test every candidate against the REAL fetchers,
prune failures, write survivors to watchlist.json.
"""

import json
import time
from pathlib import Path

from job_sources import ATS_FETCHERS

HERE = Path(__file__).parent

KEYWORDS = [
    "junior",
    "graduate",
    "entry level",
    "entry-level",
    "associate software",
    "early career",
]


def check(company):
    """Return (ok, n_postings, note). Never raises — this script's job
    is converting failures into a report."""
    if company["type"] not in ATS_FETCHERS:
        return False, 0, f"unknown type {company['type']}"
    try:
        jobs = ATS_FETCHERS[company["type"]](company["name"], company["id"])
        return True, len(jobs), ""
    except Exception as e:
        return False, 0, str(e)[:80]


if __name__ == "__main__":
    candidates = json.loads((HERE / "watchlist_candidates.json").read_text())[
        "companies"
    ]
    good, bad = [], []

    print(f"verifying {len(candidates)} candidates...\n")
    for c in candidates:
        ok, n, note = check(c)
        if ok:
            print(f"  OK    {c['name']:24s} {n} postings parsed")
            good.append(c)
        else:
            print(f"  FAIL  {c['name']:24s} {note}")
            bad.append(c)
        time.sleep(0.3)  # polite: ~3 req/sec across other people's APIs

    (HERE / "watchlist.json").write_text(
        json.dumps(
            {
                "_comment": "Verified by verify_watchlist.py. Add candidates to "
                "watchlist_candidates.json and re-run.",
                "companies": good,
                "title_keywords": KEYWORDS,
            },
            indent=2,
        )
    )

    print(f"\n{len(good)} verified -> watchlist.json | {len(bad)} pruned")
    if bad:
        print("pruned (fix slug or drop):", ", ".join(c["name"] for c in bad))
