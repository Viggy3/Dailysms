# calendar_playground.py
from datetime import datetime, timedelta
import os
from zoneinfo import ZoneInfo
from googleapiclient.discovery import build
from auth import get_credentials

TZ = ZoneInfo("Europe/London")
CALENDAR_IDS = ["primary", os.environ.get("WORK_CALENDAR_ID")]


def fetch_events(calendar_id, days_ahead=1, max_results=20):
    """Fetch events from ONE calendar."""
    service = build("calendar", "v3", credentials=get_credentials())
    now = datetime.now(TZ)
    end = now + timedelta(days=days_ahead)

    response = (
        service.events()
        .list(
            calendarId=calendar_id,
            timeMin=now.isoformat(),
            timeMax=end.isoformat(),
            maxResults=max_results,
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )
    return response.get("items", [])


def fetch_all_events(days_ahead=1):
    """Fetch from every calendar and merge, sorted by start time."""
    all_events = []
    for cal_id in CALENDAR_IDS:
        if cal_id:  # skips None if env var isn't set
            all_events += fetch_events(cal_id, days_ahead)

    # Merge is just concatenation + re-sort; each list was sorted,
    # but the combined one isn't until we sort globally.
    all_events.sort(key=lambda e: e["start"].get("dateTime", e["start"].get("date")))
    return all_events


def parse_event(event):
    start = event["start"].get("dateTime", event["start"].get("date"))
    end = event["end"].get("dateTime", event["end"].get("date"))

    return {
        "title": event.get("summary", "(no title)"),
        "start": start,
        "end": end,
        "location": event.get("location"),
        "all_day": "dateTime" not in event["start"],
    }


if __name__ == "__main__":
    events = fetch_all_events(days_ahead=7)

    if not events:
        print("No events found")

    for e in events:
        p = parse_event(e)
        prefix = "All day" if p["all_day"] else p["start"][11:16]
        suffix = " " if p["all_day"] else f" — {p['end'][11:16]}"
        print(
            f"{prefix} — {p['title']}{suffix}"
            + (f" @ {p['location']}" if p["location"] else "")
        )
