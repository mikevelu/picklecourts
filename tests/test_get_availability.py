from datetime import datetime, timezone
from get_availability import (
    all_activities,
    find_pickleball_activities,
    fourteen_day_window_utc,
    epoch_to_local,
    parse_available_slots,
    build_venue_result,
)


# --- all_activities ---

def test_all_activities_flattens_nested_payload():
    payload = {
        "types": [
            {
                "n": "Racquet Sports",
                "sites": [
                    {
                        "acts": [
                            {"n": "Badminton", "id": 1},
                            {"n": "Tennis", "id": 2},
                        ]
                    }
                ],
            },
            {
                "n": "Court Hire",
                "sites": [
                    {"acts": [{"n": "Pickleball", "id": 3}]}
                ],
            },
        ]
    }
    result = list(all_activities(payload))
    assert len(result) == 3
    assert result[0] == {"name": "Badminton", "category": "Racquet Sports", "id": 1}
    assert result[2] == {"name": "Pickleball", "category": "Court Hire", "id": 3}


def test_all_activities_empty_payload():
    assert list(all_activities({})) == []


def test_all_activities_missing_keys():
    assert list(all_activities({"types": [{}]})) == []
    assert list(all_activities({"types": [{"sites": [{}]}]})) == []


# --- find_pickleball_activities ---

def test_find_pickleball_activities_filters_correctly():
    payload = {
        "types": [
            {
                "n": "Sports",
                "sites": [
                    {
                        "acts": [
                            {"n": "Badminton", "id": 1},
                            {"n": "Pickleball Online", "id": 2},
                            {"n": "PICKLE Ball", "id": 3},
                        ]
                    }
                ],
            }
        ]
    }
    result = find_pickleball_activities(payload)
    assert len(result) == 2
    assert result[0]["name"] == "Pickleball Online"
    assert result[1]["name"] == "PICKLE Ball"


def test_find_pickleball_activities_no_matches():
    payload = {
        "types": [
            {
                "n": "Sports",
                "sites": [{"acts": [{"n": "Tennis", "id": 1}]}],
            }
        ]
    }
    assert find_pickleball_activities(payload) == []


# --- fourteen_day_window_utc ---

def test_fourteen_day_window_utc_known_datetime():
    now = datetime(2026, 3, 9, 14, 35, 22, 123456, tzinfo=timezone.utc)
    start, end = fourteen_day_window_utc(now)
    expected_start = datetime(2026, 3, 9, 14, 0, 0, tzinfo=timezone.utc)
    expected_end = datetime(2026, 3, 23, 14, 0, 0, tzinfo=timezone.utc)
    assert start == int(expected_start.timestamp())
    assert end == int(expected_end.timestamp())


def test_fourteen_day_window_utc_zeroes_minutes_seconds():
    now = datetime(2026, 1, 1, 0, 59, 59, 999999, tzinfo=timezone.utc)
    start, _ = fourteen_day_window_utc(now)
    dt = datetime.fromtimestamp(start, tz=timezone.utc)
    assert dt.minute == 0
    assert dt.second == 0
    assert dt.microsecond == 0


# --- epoch_to_local ---

def test_epoch_to_local_known_epoch():
    # 2026-03-09 14:00:00 UTC = 2026-03-09 14:00:00 GMT (no DST in March before clocks change)
    epoch = int(datetime(2026, 3, 9, 14, 0, 0, tzinfo=timezone.utc).timestamp())
    result = epoch_to_local(epoch)
    assert result.hour == 14
    assert result.day == 9

    # During BST (e.g. April): UTC+1
    epoch_bst = int(datetime(2026, 6, 15, 14, 0, 0, tzinfo=timezone.utc).timestamp())
    result_bst = epoch_to_local(epoch_bst)
    assert result_bst.hour == 15  # UTC+1


# --- parse_available_slots ---

def test_parse_available_slots_excludes_booked_and_missing():
    # Use a fixed UTC epoch: 2026-03-09 10:00:00 UTC
    epoch_10 = int(datetime(2026, 3, 9, 10, 0, 0, tzinfo=timezone.utc).timestamp())
    epoch_11 = int(datetime(2026, 3, 9, 11, 0, 0, tzinfo=timezone.utc).timestamp())

    payload = {
        "bookableItems": [
            {
                "n": "Court 1",
                "slots": [
                    {"s": 1, "sUTC": epoch_10},   # available
                    {"s": 0, "sUTC": epoch_11},   # booked (s=0)
                    {"s": 1},                      # missing sUTC
                ],
            }
        ]
    }
    result = parse_available_slots(payload)
    assert "2026-03-09" in result
    assert result["2026-03-09"]["Court 1"] == ["10:00"]


def test_parse_available_slots_groups_by_date_and_court_sorted():
    epoch_11 = int(datetime(2026, 3, 9, 11, 0, 0, tzinfo=timezone.utc).timestamp())
    epoch_10 = int(datetime(2026, 3, 9, 10, 0, 0, tzinfo=timezone.utc).timestamp())
    epoch_next = int(datetime(2026, 3, 10, 9, 0, 0, tzinfo=timezone.utc).timestamp())

    payload = {
        "bookableItems": [
            {
                "n": "Court B",
                "slots": [
                    {"s": 1, "sUTC": epoch_11},
                    {"s": 1, "sUTC": epoch_10},
                ],
            },
            {
                "n": "Court A",
                "slots": [{"s": 1, "sUTC": epoch_next}],
            },
        ]
    }
    result = parse_available_slots(payload)
    dates = list(result.keys())
    assert dates == ["2026-03-09", "2026-03-10"]

    courts_day1 = list(result["2026-03-09"].keys())
    assert courts_day1 == ["Court B"]
    assert result["2026-03-09"]["Court B"] == ["10:00", "11:00"]

    courts_day2 = list(result["2026-03-10"].keys())
    assert courts_day2 == ["Court A"]


def test_parse_available_slots_empty():
    assert parse_available_slots({}) == {}
    assert parse_available_slots({"bookableItems": []}) == {}


# --- build_venue_result ---

def test_build_venue_result_combines_fields():
    activity = {"name": "Pickleball", "category": "Court Hire", "id": 99}
    availability_payload = {"bookableItems": []}
    info_payload = {
        "activity": {
            "price": "£5.00",
            "priceDesc": "per session",
            "d": 60,
        }
    }

    label, data = build_venue_result(activity, availability_payload, info_payload)
    assert label == "Pickleball | Court Hire"
    assert data["price"] == "£5.00"
    assert data["priceDesc"] == "per session"
    assert data["duration"] == 60
    assert data["dates"] == {}


def test_build_venue_result_missing_info():
    activity = {"name": "Pickle", "category": "Sports", "id": 1}
    label, data = build_venue_result(activity, {"bookableItems": []}, {})
    assert label == "Pickle | Sports"
    assert data["price"] == ""
    assert data["duration"] == 0
