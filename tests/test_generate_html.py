from generate_html import venue_display_name, venue_slug, format_date, generate_html


# --- venue_display_name ---

def test_venue_display_name_known_mapping():
    assert venue_display_name("Airdrie L.C Pickleball | Racquet Sports") == "Airdrie Leisure Centre"
    assert venue_display_name("Time Capsule  Pickleball | Court Hire") == "Time Capsule"
    assert venue_display_name("Pickleball Online | Something") == "Ravenscraig"


def test_venue_display_name_unknown_passthrough():
    assert venue_display_name("New Venue | Category") == "New Venue"
    assert venue_display_name("Standalone") == "Standalone"


# --- venue_slug ---

def test_venue_slug():
    assert venue_slug("Airdrie Leisure Centre") == "airdrie-leisure-centre"
    assert venue_slug("Time Capsule") == "time-capsule"
    assert venue_slug("Wishaw") == "wishaw"


# --- format_date ---

def test_format_date():
    assert format_date("2026-03-02") == "Mon 2 Mar"
    assert format_date("2026-12-25") == "Fri 25 Dec"
    assert format_date("2026-01-01") == "Thu 1 Jan"


# --- generate_html ---

def test_generate_html_contains_timestamp():
    html = generate_html({}, "9 March 2026, 14:00")
    assert "9 March 2026, 14:00" in html


def test_generate_html_contains_venue_names_and_slots():
    data = {
        "Wishaw Pickleball | Court Hire": {
            "dates": {
                "2026-03-09": {
                    "Court 1": ["10:00", "11:00"],
                }
            },
            "price": "£5.00",
            "priceDesc": "per session",
            "duration": 60,
        },
        "Airdrie L.C Pickleball | Racquet Sports": {
            "dates": {
                "2026-03-09": {
                    "Court A": ["09:00"],
                }
            },
            "price": "£6.00",
            "priceDesc": "",
            "duration": 45,
        },
    }
    html = generate_html(data, "9 March 2026, 14:00")

    # Venue display names appear
    assert "Wishaw" in html
    assert "Airdrie Leisure Centre" in html

    # Slots appear
    assert "10:00" in html
    assert "11:00" in html
    assert "09:00" in html

    # Court names appear
    assert "Court 1" in html
    assert "Court A" in html


def test_generate_html_venues_sorted_alphabetically():
    data = {
        "Wishaw Pickleball | Court Hire": {
            "dates": {},
            "price": "",
            "priceDesc": "",
            "duration": 0,
        },
        "Airdrie L.C Pickleball | Racquet Sports": {
            "dates": {},
            "price": "",
            "priceDesc": "",
            "duration": 0,
        },
    }
    html = generate_html(data, "now")
    airdrie_pos = html.index("Airdrie Leisure Centre")
    wishaw_pos = html.index("Wishaw")
    assert airdrie_pos < wishaw_pos


def test_generate_html_empty_data():
    html = generate_html({}, "now")
    assert "PickleCourts" in html
    assert "<html" in html
    assert "</html>" in html
