import json
import os
import re
import sys
from pathlib import Path
import requests

here = Path(__file__).parent
timeout = 20
Headers = {"User-Agent": "personal-job-alerts/1.0 (individual job seeker)"}


def _get(url, **kwargs):
    kwargs.setdefault("headers", Headers)
    kwargs.setdefault("timeout", timeout)

    response = requests.get(url, **kwargs)
    response.raise_for_status()
    return response


def fetch_greenhouse(company, slug):
    # Some boards live on Greenhouse's EU instance; fall back if US 404s.
    data = _get(f"https://boards-api.greenhouse.io/v1/boards/{slug}/jobs").json()

    return [
        {
            "company": company,
            "title": j.get("title", ""),
            "location": (j.get("location") or {}).get("name", ""),
            "url": j.get("absolute_url", ""),
        }
        for j in data.get("jobs", [])
    ]


def fetch_lever(company, slug):
    data = _get(f"https://api.lever.co/v0/postings/{slug}?mode=json").json()
    return [
        {
            "company": company,
            "title": j.get("text", ""),
            "location": (j.get("categories") or {}).get("location", ""),
            "url": j.get("hostedUrl", ""),
        }
        for j in data
    ]


def fetch_ashby(company, slug):
    data = _get(f"https://api.ashbyhq.com/posting-api/job-board/{slug}").json()
    return [
        {
            "company": company,
            "title": j.get("title", ""),
            "location": j.get("location", ""),
            "url": j.get("jobUrl") or j.get("applyUrl", ""),
        }
        for j in data.get("jobs", [])
    ]


def fetch_workable(company, slug):
    data = _get(f"https://apply.workable.com/api/v1/widget/accounts/{slug}").json()
    return [
        {
            "company": company,
            "title": j.get("title", ""),
            "location": (j.get("location") or {}).get("name", ""),
            "url": j.get("apply_url", ""),
        }
        for j in data.get("jobs", [])
    ]


def fetch_careers_page(company, url):
    """Generic HTML scrape. Works on plain pages; JS-rendered shells get
    flagged (find the company's ATS slug instead — view-source, search
    'greenhouse'/'lever'/'ashby')."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(_get(url).text, "html.parser")
    if len(soup.get_text(" ", strip=True)) < 500:
        print(
            f"  warning: {company} careers page is likely JS-rendered; "
            f"plain HTTP can't see it. Find their ATS endpoint instead."
        )
        return []

    jobs, seen_titles = [], set()
    for a in soup.find_all("a", href=True):
        title = a.get_text(" ", strip=True)
        if (
            5 < len(title) < 90
            and re.search(r"engineer|developer|software|graduate|junior", title, re.I)
            and title.lower() not in seen_titles
        ):
            seen_titles.add(title.lower())
            href = a["href"]
            if href.startswith("/"):
                href = url.rstrip("/") + href
            jobs.append(
                {"company": company, "title": title, "location": "", "url": href}
            )
    return jobs


def fetch_reed(query="junior software engineer", where="london"):
    api_key = os.environ.get("REED_API_KEY")
    if not api_key:
        raise ValueError("REED_API_KEY is not set in environment variables.")
    data = _get(
        "https://www.reed.co.uk/api/1.0/search",
        params={"keywords": query, "locationName": where, "resultsToTake": 50},
        auth=(api_key, ""),
    ).json()
    return [
        {
            "company": j.get("employerName", "?"),
            "title": j.get("jobTitle", ""),
            "location": j.get("locationName", ""),
            "url": j.get("jobUrl", ""),
        }
        for j in data.get("results", [])
    ]


def fetch_adzuna(query="junior software developer", where="london"):
    """Adzuna aggregates thousands of UK sources. Free keys:
    developer.adzuna.com -> ADZUNA_APP_ID / ADZUNA_APP_KEY in .env.
    max_days_old=1 keeps it to genuinely fresh postings."""
    app_id, app_key = os.getenv("ADZUNA_APP_ID"), os.getenv("ADZUNA_APP_KEY")
    if not (app_id and app_key):
        print("  Adzuna: no keys in .env — skipping breadth source")
        return []
    data = _get(
        "https://api.adzuna.com/v1/api/jobs/gb/search/1",
        params={
            "app_id": app_id,
            "app_key": app_key,
            "what": query,
            "where": where,
            "max_days_old": 1,
            "results_per_page": 100,
            "content-type": "application/json",
        },
    ).json()
    return [
        {
            "company": (j.get("company") or {}).get("display_name", "?"),
            "title": j.get("title", ""),
            "location": (j.get("location") or {}).get("display_name", ""),
            "url": j.get("redirect_url", ""),
        }
        for j in data.get("results", [])
    ]


ATS_FETCHERS = {
    "greenhouse": fetch_greenhouse,
    "lever": fetch_lever,
    "ashby": fetch_ashby,
    "careers_page": fetch_careers_page,
    "workable": fetch_workable,
}


def fetch_all():
    """Watchlist (title-filtered) + breadth searches. One broken source
    never kills the digest — each is caught, named, and skipped."""
    config = json.loads((here / "watchlist.json").read_text())
    keywords = [k.lower() for k in config["title_keywords"]]
    results = []

    for c in config["companies"]:
        try:
            postings = ATS_FETCHERS[c["type"]](c["name"], c["id"])
        except Exception as e:
            print(f"  {c['name']} failed: {e}")
            continue
        matches = [
            p for p in postings if any(k in p["title"].lower() for k in keywords)
        ]
        print(f"  {c['name']}: {len(postings)} postings, {len(matches)} junior-ish")
        results.extend(matches)

    for fetch in (fetch_adzuna, fetch_reed):
        try:
            broad = fetch()
            print(f"  {fetch.__name__}: {len(broad)} fresh postings")
            results.extend(broad)
        except Exception as e:
            print(f"  {fetch.__name__} failed: {e}")

    return results


if __name__ == "__main__":
    if "--debug" in sys.argv:
        name = sys.argv[-1]
        config = json.loads((here / "watchlist.json").read_text())
        c = next(x for x in config["companies"] if x["name"].lower() == name.lower())
        urls = {
            "greenhouse": f"https://boards-api.greenhouse.io/v1/boards/{c['id']}/jobs",
            "lever": f"https://api.lever.co/v0/postings/{c['id']}?mode=json",
            "ashby": f"https://api.ashbyhq.com/posting-api/job-board/{c['id']}",
            "careers_page": c["id"],
        }
        print(_get(urls[c["type"]]).text[:3000])
    else:
        for job in fetch_all():
            print(f"{job['company']}: {job['title']} ({job['location']}) {job['url']}")
