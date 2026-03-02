"""
Reads court availability JSON from stdin and writes index.html to stdout.

Usage:
    python3 get-availability.py | python3 generate-html.py > index.html
"""

import json
import sys
from datetime import datetime
from zoneinfo import ZoneInfo

LOCAL_TZ = ZoneInfo("Europe/London")

VENUE_NAMES = {
    "Airdrie L.C Pickleball": "Airdrie Leisure Centre",
    "Broadwood Pickle Ball": "Broadwood",
    "Iain Nicholson Pickleball": "Iain Nicholson",
    "Sir Matt Busby Pickleball": "Sir Matt Busby",
    "Time Capsule  Pickleball": "Time Capsule",
    "Townhead  Pickleball": "Townhead",
    "Wishaw Pickleball": "Wishaw",
    "Pickleball Online": "Ravenscraig",
    "Tryst Pickleball": "Tryst",
}


def venue_display_name(label):
    """Turn 'Airdrie L.C Pickleball | Raquet Sports Court Hire' into 'Airdrie Leisure Centre'."""
    activity_name = label.split(" | ")[0]
    return VENUE_NAMES.get(activity_name, activity_name)


def venue_slug(name):
    return name.lower().replace(" ", "-")


def format_date(date_str):
    """Turn '2026-03-02' into 'Mon 2 Mar'."""
    date = datetime.strptime(date_str, "%Y-%m-%d")
    return date.strftime("%a %-d %b")


def generate_html(data):
    now = datetime.now(LOCAL_TZ)
    timestamp = now.strftime("%-d %B %Y, %H:%M")

    venues = []
    for label, dates in data.items():
        name = venue_display_name(label)
        venues.append({"name": name, "slug": venue_slug(name), "dates": dates})
    venues.sort(key=lambda v: v["name"])

    lines = []

    # Head
    lines.append("<!DOCTYPE html>")
    lines.append('<html lang="en">')
    lines.append("<head>")
    lines.append('  <meta charset="utf-8">')
    lines.append('  <meta name="viewport" content="width=device-width, initial-scale=1">')
    lines.append("  <title>PickleCourts - North Lanarkshire Court Availability</title>")
    lines.append("  <style>")
    lines.append("    h2 {")
    lines.append("      position: sticky;")
    lines.append("      top: 0;")
    lines.append("      background: white;")
    lines.append("      padding: 4px 0;")
    lines.append("      margin: 0;")
    lines.append("    }")
    lines.append("    h3 {")
    lines.append("      position: sticky;")
    lines.append("      top: 1.5em;")
    lines.append("      background: white;")
    lines.append("      padding: 4px 0;")
    lines.append("      margin: 0;")
    lines.append("    }")
    lines.append("  </style>")
    lines.append("</head>")
    lines.append('<body id="top">')
    lines.append("")

    # Header
    lines.append("<h1>PickleCourts</h1>")
    lines.append("<p>Pickleball court availability in North Lanarkshire</p>")
    lines.append(f"<p><small>Last updated: {timestamp}</small></p>")
    lines.append("")
    lines.append("<hr>")
    lines.append("")

    # Venue navigation
    lines.append("<ul>")
    for venue in venues:
        lines.append(f'  <li><a href="#{venue["slug"]}">{venue["name"]}</a></li>')
    lines.append("</ul>")
    lines.append("")
    lines.append("<hr>")

    # Venue sections
    for venue in venues:
        lines.append("")
        lines.append(f'<h2 id="{venue["slug"]}">{venue["name"]}</h2>')
        lines.append("")

        for date_str, courts in venue["dates"].items():
            lines.append(f"<h3>{format_date(date_str)}</h3>")
            lines.append('<table border="1" cellpadding="4">')
            lines.append("<tr><th>Court</th><th>Available Slots</th></tr>")

            for court, times in courts.items():
                lines.append(f"<tr><td>{court}</td><td>{', '.join(times)}</td></tr>")

            lines.append("</table>")
            lines.append("")

        lines.append('<p><a href="#top">Back to top</a></p>')
        lines.append("<hr>")

    lines.append("")
    lines.append("</body>")
    lines.append("</html>")

    return "\n".join(lines)


def main():
    data = json.load(sys.stdin)
    print(generate_html(data))


if __name__ == "__main__":
    main()
