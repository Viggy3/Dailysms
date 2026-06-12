"""
daily_digest.py — fetch postings from the watchlist, keep only ones we
haven't seen before, have Claude score them against MY profile, text me
the good ones.

Pipeline:
  job_sources.fetch_all() -> new_only() -> claude_fit_filter() -> send()

State: seen.json remembers every job URL already reported, so the 7am
text only ever contains NEW postings. Delete seen.json to reset.

Run manually:  python daily_digest.py          (sends SMS)
               python daily_digest.py --dry    (prints, doesn't send)
"""

import json
import sys
from pathlib import Path

from anthropic import Anthropic
from dotenv import load_dotenv

from job_sources import fetch_all
from send_sms import send

load_dotenv()

HERE = Path(__file__).parent
SEEN_FILE = HERE / "seen.json"

# The fit-filter is only as good as this profile. Update it as you grow.
PROFILE = """\
Junior software developer, UK (London), no visa sponsorship needed.
Strong: Python, FastAPI, React. Shipped a production web app with real
users (API design, validation, presigned-URL uploads). NumPy/data
pipelines from final-year project. Wants: junior/graduate backend or
full-stack roles, London or remote UK. Not a fit: senior roles, pure
C++/Java roles, roles requiring 3+ years experience."""


def new_only(jobs):
    """Drop anything we've already reported. URL = identity of a posting."""
    seen = set(json.loads(SEEN_FILE.read_text())) if SEEN_FILE.exists() else set()
    fresh = [j for j in jobs if j["url"] and j["url"] not in seen]
    # Record them as seen NOW, so even a failed SMS won't re-report forever
    SEEN_FILE.write_text(json.dumps(sorted(seen | {j["url"] for j in fresh})))
    return fresh


def claude_fit_filter(jobs):
    """One Claude call: score all new jobs against my profile, draft the SMS."""
    client = Anthropic()
    response = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=300,
        system=(
            "You filter job postings for this candidate:\n" + PROFILE + "\n\n"
            "Score each posting 1-10 for fit. Output an SMS digest, max 320 "
            "characters: only postings scoring 7+, best first, format "
            "'Company: Title (score/10)'. One short overall line at the end. "
            "If nothing scores 7+, output exactly: NO_GOOD_MATCHES"
        ),
        messages=[{"role": "user", "content": json.dumps(jobs)}],
    )
    return response.content[0].text.strip()


if __name__ == "__main__":
    dry = "--dry" in sys.argv

    print("fetching watchlist...")
    new_jobs = new_only(fetch_all())
    print(f"{len(new_jobs)} new postings since last run")

    # --- compose ---
    parts = []
    if new_jobs:
        digest = claude_fit_filter(new_jobs)
        if digest == "NO_GOOD_MATCHES":
            parts.append(f"{len(new_jobs)} new postings, none a good fit today.")
        else:
            parts.append(digest)
    else:
        parts.append("No new postings today.")

    tasks_file = HERE / "tasks.txt"
    if tasks_file.exists() and tasks_file.read_text().strip():
        parts.append("Today: " + tasks_file.read_text().strip())

    message = "\n".join(parts)
    print(f"--- message ---\n{message}\n---------------")

    # --- deliver (the only send decision in the file) ---
    if dry:
        print("(dry run — not sending)")
    else:
        send(message)
