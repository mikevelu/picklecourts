import json
import os
import sys
import requests
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

API_BASE = "https://nll.leisurecloud.net/AWS/api"
LOCAL_TZ = ZoneInfo("Europe/London")


def require_env(name):
    value = os.environ.get(name)
    if not value:
        sys.exit(f"Missing environment variable: {name}")
    return value


API_KEY = require_env("PICKLECOURTS_API_KEY")
USERNAME = require_env("PICKLECOURTS_USERNAME")
PASSWORD = require_env("PICKLECOURTS_PASSWORD")


def auth_headers(token=None):
    headers = {
        "AuthenticationKey": API_KEY,
        "user": USERNAME,
        "pw": PASSWORD,
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def get_token():
    resp = requests.get(f"{API_BASE}/token?locale=en_GB", headers=auth_headers())
    if not resp.ok:
        sys.exit(f"Authentication failed (HTTP {resp.status_code}). Check your credentials.")

    data = resp.json()
    if "jwtToken" not in data:
        sys.exit(
            f"Authentication failed: no token in response. Check your credentials.\n"
            f"Response: {json.dumps(data, indent=2)}"
        )
    return data["jwtToken"]


def fetch_activities(token):
    resp = requests.get(
        f"{API_BASE}/activity/list?locale=en_GB", headers=auth_headers(token)
    )
    if not resp.ok:
        sys.exit(f"Failed to fetch activity list (HTTP {resp.status_code})")
    return resp.json()


def all_activities(payload):
    """Flatten the nested API response (types -> sites -> acts) into a simple list."""
    for activity_type in payload.get("types", []):
        for site in activity_type.get("sites", []):
            for activity in site.get("acts", []):
                yield {
                    "name": activity.get("n", ""),
                    "category": activity_type.get("n"),
                    "id": activity.get("id"),
                }


def find_pickleball_activities(payload):
    return [a for a in all_activities(payload) if "pickle" in a["name"].lower()]


def seven_day_window_utc():
    now = datetime.now(timezone.utc).replace(minute=0, second=0, microsecond=0)
    end = now + timedelta(days=7)
    return int(now.timestamp()), int(end.timestamp())


def epoch_to_local(epoch_seconds):
    return datetime.fromtimestamp(int(epoch_seconds), tz=timezone.utc).astimezone(
        LOCAL_TZ
    )


def parse_available_slots(payload):
    """Parse API response into {date: {court: [time, ...]}}."""
    by_date = {}
    for item in payload.get("bookableItems", []):
        court = item.get("n", "Unknown")
        for slot in item.get("slots", []):
            # s=0 means booked, non-zero means available. sUTC is the start time as epoch seconds
            if slot.get("s") == 0 or slot.get("sUTC") is None:
                continue

            local_dt = epoch_to_local(slot["sUTC"])
            date_key = local_dt.strftime("%Y-%m-%d")
            time_str = local_dt.strftime("%H:%M")
            by_date.setdefault(date_key, {}).setdefault(court, []).append(time_str)

    return {
        date: {court: sorted(times) for court, times in sorted(courts.items())}
        for date, courts in sorted(by_date.items())
    }


def fetch_availability(token, activity, from_utc, to_utc):
    resp = requests.get(
        f"{API_BASE}/activity/availability",
        headers=auth_headers(token),
        params={
            "locale": "en_GB",
            "fromUTC": from_utc,
            "toUTC": to_utc,
            "activityId": activity["id"],
        },
    )
    if not resp.ok:
        sys.exit(
            f"Failed to fetch availability for {activity['name']} (HTTP {resp.status_code})"
        )
    return resp.json()


def get_all_availability(token, activities):
    from_utc, to_utc = seven_day_window_utc()

    results = {}
    for activity in activities:
        label = f"{activity['name']} | {activity['category']}"
        raw = fetch_availability(token, activity, from_utc, to_utc)
        results[label] = parse_available_slots(raw)

    return results


def main():
    token = get_token()
    activities = find_pickleball_activities(fetch_activities(token))

    if not activities:
        sys.exit("No pickleball activities found. The API response may have changed.")

    availability = get_all_availability(token, activities)
    print(json.dumps(availability, indent=4))


if __name__ == "__main__":
    main()
