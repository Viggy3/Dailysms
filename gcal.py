import os
import requests
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo
from icalendar import Calendar
import recurring_ical_events
from dotenv import load_dotenv

load_dotenv()

LONDON = ZoneInfo("Europe/London")


def fetch_calendar() -> list[str]:
    # 1. Read GCAL_ICS_URLS from env, split by comma, skip empty strings
    urls = [u for u in os.environ.get("GCAL_ICS_URLS", "").split(",") if u.strip()]
    # 2. Get today's start (midnight London time)
    today_start = datetime.now(LONDON).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    today_end = today_start + timedelta(days=1) - timedelta(seconds=1)
    events_list = []
    for url in urls:
        try:
            response = requests.get(url, timeout=15)
            calendar = Calendar.from_ical(response.content)
            events = recurring_ical_events.of(calendar).between(today_start, today_end)
            for event in events:
                dt = event["DTSTART"].dt
                dte = event["DTEND"].dt
                summary = event.get("SUMMARY", "")
                if isinstance(dt, datetime):
                    dt = dt.astimezone(LONDON)
                    dte = dte.astimezone(LONDON)
                    events_list.append(
                        f"{dt.strftime('%H:%M')} - {dte.strftime('%H:%M')} {summary}"
                    )
                elif isinstance(dt, date):
                    events_list.append(f"{summary}")
        except Exception as e:
            print(f"Error fetching calendar from {url}: {e}")
    return sorted(events_list)
    # 3. For each URL:
    #    - requests.get() the URL (timeout=15)
    #    - Calendar.from_ical(response.content)
    #    - recurring_ical_events.of(calendar).between(today_start, today_end)
    #    - For each event, get ev["DTSTART"].dt
    #      - if it's a datetime → astimezone(LONDON) → format "HH:MM Summary"
    #      - if it's a date → just use the summary (all-day event)

    # 4. Sort by time, return list of strings


if __name__ == "__main__":
    import os

    print("URLs:", os.environ.get("GCAL_ICS_URLS", "NOT SET"))
    events = fetch_calendar()
    print("Events:", events)
