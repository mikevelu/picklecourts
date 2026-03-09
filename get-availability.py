import json
import os
import sys
import requests
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

LOCAL_TZ = ZoneInfo("Europe/London")


def fetch_activities(api_base, headers):
    resp = requests.get(
        f"{api_base}/activity/list?locale=en_GB", headers=headers
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


def seven_day_window_utc(now):
    start = now.replace(minute=0, second=0, microsecond=0)
    end = start + timedelta(days=7)
    return int(start.timestamp()), int(end.timestamp())


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


def fetch_availability(api_base, headers, activity_id, from_utc, to_utc):
    resp = requests.get(
        f"{api_base}/activity/availability",
        headers=headers,
        params={
            "locale": "en_GB",
            "fromUTC": from_utc,
            "toUTC": to_utc,
            "activityId": activity_id,
        },
    )
    if not resp.ok:
        sys.exit(
            f"Failed to fetch availability (HTTP {resp.status_code})"
        )
    return resp.json()


def fetch_activity_info(api_base, headers, activity_id):
    resp = requests.get(
        f"{api_base}/activity/info",
        headers=headers,
        params={"locale": "en_GB", "activityId": activity_id},
    )
    if not resp.ok:
        return {}
    return resp.json()


def build_venue_result(activity, availability_payload, info_payload):
    """Pure: transform raw API payloads into our venue data structure."""
    label = f"{activity['name']} | {activity['category']}"
    act_info = info_payload.get("activity", {})
    return label, {
        "dates": parse_available_slots(availability_payload),
        "price": act_info.get("price", ""),
        "priceDesc": act_info.get("priceDesc", ""),
        "duration": act_info.get("d", 0),
    }


def main():
    api_key = os.environ.get("PICKLECOURTS_API_KEY")
    if not api_key:
        sys.exit("Missing environment variable: PICKLECOURTS_API_KEY")
    api_base = "https://nll.leisurecloud.net/AWS/api"
    headers = {"AuthenticationKey": api_key}

    activities = find_pickleball_activities(fetch_activities(api_base, headers))

    if not activities:
        sys.exit("No pickleball activities found. The API response may have changed.")

    now = datetime.now(timezone.utc)
    from_utc, to_utc = seven_day_window_utc(now)

    results = {}
    for activity in activities:
        raw = fetch_availability(api_base, headers, activity["id"], from_utc, to_utc)
        info = fetch_activity_info(api_base, headers, activity["id"])
        label, venue_data = build_venue_result(activity, raw, info)
        results[label] = venue_data

    print(json.dumps(results, indent=4))


if __name__ == "__main__":
    main()
