import os
from datetime import datetime, timedelta, date
from zoneinfo import ZoneInfo

import recurring_ical_events
from dotenv import load_dotenv
from icalendar import Calendar
import requests

load_dotenv()

LONDON = ZoneInfo("Europe/London")  # one explicit timezone, everywhere
today = datetime.now(LONDON).date()
timeout = 20

work_details = os.environ["GCAL_ICS_URL_WORK"]
personal_details = os.environ["GCAL_ICS_URL"]


def fetch_calendar(ics_url) -> list[str]:
    import requests
    from icalendar import Calendar

    response = requests.get(ics_url)
    response.raise_for_status()
    calendar = Calendar.from_ical(response.content)

    events = []
    now = datetime.now()
    for component in calendar.walk():
        if component.name == "VEVENT":
            start = component.get("dtstart").dt
            if (
                isinstance(start, datetime)
                and start >= now
                and start <= now + timedelta(days=3)
            ):
                summary = component.get("summary")
                events.append(f"{start.strftime('%Y-%m-%d %H:%M')}: {summary}")
    return events
