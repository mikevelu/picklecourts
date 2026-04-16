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


def date_slug(date_str):
    """Turn '2026-04-16' into 'date-2026-04-16'."""
    return f"date-{date_str}"


def format_date(date_str):
    """Turn '2026-03-02' into 'Mon 2 Mar'."""
    date = datetime.strptime(date_str, "%Y-%m-%d")
    return date.strftime("%a %-d %b")


def generate_html(data, timestamp):

    venues = []
    for label, info in data.items():
        name = venue_display_name(label)
        venues.append({
            "name": name,
            "slug": venue_slug(name),
            "dates": info.get("dates", {}),
            "price": info.get("price", ""),
            "priceDesc": info.get("priceDesc", ""),
            "duration": info.get("duration", 0),
        })
    venues.sort(key=lambda v: v["name"])

    days = {}  # date_str -> list of venue rows
    for venue in venues:
        for date_str, courts in venue["dates"].items():
            if not courts:           # skip venues with no slots on that day
                continue
            days.setdefault(date_str, []).append({
                "name": venue["name"],
                "slug": venue["slug"],
                "price": venue["price"],
                "priceDesc": venue["priceDesc"],
                "duration": venue["duration"],
                "courts": courts,
            })
    sorted_dates = sorted(days.keys())
    for d in sorted_dates:
        days[d].sort(key=lambda v: v["name"])

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
    lines.append("      z-index: 2;")
    lines.append("      background: white;")
    lines.append("      padding: 4px 0;")
    lines.append("      margin: 0;")
    lines.append("    }")
    lines.append("    h3 small {")
    lines.append("      font-weight: normal;")
    lines.append("    }")
    lines.append("    h3 {")
    lines.append("      position: sticky;")
    lines.append("      top: 1.5em;")
    lines.append("      z-index: 1;")
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

    # Date navigation
    lines.append("<ul>")
    for date_str in sorted_dates:
        lines.append(f'  <li><a href="#{date_slug(date_str)}">{format_date(date_str)}</a></li>')
    lines.append("</ul>")
    lines.append("")
    lines.append("<hr>")

    # Day-first sections
    for date_str in sorted_dates:
        date_id = date_slug(date_str)
        lines.append("")
        lines.append("<section>")
        lines.append(f'<h2 id="{date_id}">{format_date(date_str)}</h2>')
        lines.append("")

        for venue in days[date_str]:
            anchor = f'{date_id}-{venue["slug"]}'
            h3 = f'<h3 id="{anchor}">{venue["name"]}'
            if venue["price"]:
                h3 += f' <small>({venue["price"]} / {venue["duration"]} mins)</small>'
            h3 += '</h3>'
            lines.append(h3)

            lines.append('<table border="1" cellpadding="4">')
            lines.append("<tr><th>Court</th><th>Available Slots</th></tr>")
            for court, times in venue["courts"].items():
                lines.append(f"<tr><td>{court}</td><td>{', '.join(times)}</td></tr>")
            lines.append("</table>")
            lines.append("")

        lines.append('<p><a href="#top">Back to top</a></p>')
        lines.append('</section>')
        lines.append("<hr>")

    lines.append("")
    lines.append("</body>")
    lines.append("</html>")

    return "\n".join(lines)


def main():
    data = json.load(sys.stdin)
    timestamp = datetime.now(LOCAL_TZ).strftime("%-d %B %Y, %H:%M")
    print(generate_html(data, timestamp))


if __name__ == "__main__":
    main()
