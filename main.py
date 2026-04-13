import datetime
import asyncio
import pytz
from mvg import MvgApi, TransportType
from pathlib import Path

# Timezone
munich_tz = pytz.timezone("Europe/Berlin")

# Output file
OUTPUT_HTML = Path("index.html")

# Station config
STATION_ID = "de:09162:1700"
STATION_NAME = "My Station"

# Refresh settings
FETCH_INTERVAL_SECONDS = 30


async def fetch_departures() -> list:
    try:
        departures = await MvgApi.departures_async(
            STATION_ID,
            limit=6,
            offset=1,
            transport_types=[TransportType.SBAHN]
        )
        return departures
    except Exception as e:
        print(f"Failed to fetch departures: {e}")
        return []


def process_departures(departures: list) -> list:
    now = datetime.datetime.now(munich_tz)
    processed = []

    for item in departures:
        if item.get("cancelled"):
            continue

        try:
            departure_time = datetime.datetime.fromtimestamp(
                item["time"], pytz.utc
            ).astimezone(munich_tz)

            delta_min = int((departure_time - now).total_seconds() // 60)

            processed.append({
                "line": item.get("line", ""),
                "destination": item.get("destination", ""),
                "departure_time": departure_time,
                "departure_time_str": departure_time.strftime("%H:%M"),
                "delta_min": delta_min
            })
        except Exception as e:
            print(f"Failed to process departure item: {e}")

    return processed


def generate_html(rows: list) -> str:
    now_str = datetime.datetime.now(munich_tz).strftime("%d.%m.%Y %H:%M:%S")

    departures_html = ""
    if rows:
        for row in rows:
            line_destination = f"{row['line']} {row['destination']}".strip()
            minutes_text = f"{row['delta_min']} min"

            departures_html += f"""
            <div class="departure-row">
                <div class="left">
                    <div class="line-destination">{line_destination}</div>
                    <div class="time">{row['departure_time_str']}</div>
                </div>
                <div class="right">{minutes_text}</div>
            </div>
            """
    else:
        departures_html = """
        <div class="no-data">
            No departures available
        </div>
        """

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Train Dashboard</title>
    <meta http-equiv="refresh" content="15">
    <style>
        body {{
            margin: 0;
            padding: 0;
            background: #111;
            color: #fff;
            font-family: Arial, Helvetica, sans-serif;
        }}

        .container {{
            max-width: 700px;
            margin: 0 auto;
            padding: 16px;
        }}

        .panel {{
            background: #1b1b1b;
            border-radius: 16px;
            padding: 16px;
            box-shadow: 0 4px 16px rgba(0,0,0,0.35);
        }}

        .header {{
            display: flex;
            justify-content: space-between;
            align-items: baseline;
            gap: 12px;
            margin-bottom: 12px;
            border-bottom: 1px solid #333;
            padding-bottom: 10px;
        }}

        .title {{
            font-size: 1.4rem;
            font-weight: 700;
        }}

        .updated {{
            font-size: 0.85rem;
            color: #aaa;
        }}

        .departure-row {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 12px;
            padding: 12px 0;
            border-bottom: 1px solid #2e2e2e;
        }}

        .departure-row:last-child {{
            border-bottom: none;
        }}

        .left {{
            min-width: 0;
            flex: 1;
        }}

        .line-destination {{
            font-size: 1.05rem;
            font-weight: 700;
            line-height: 1.2;
            word-break: break-word;
        }}

        .time {{
            margin-top: 4px;
            font-size: 0.9rem;
            color: #aaa;
        }}

        .right {{
            font-size: 1.15rem;
            font-weight: 700;
            white-space: nowrap;
            color: #f5f5f5;
        }}

        .no-data {{
            padding: 24px 0;
            text-align: center;
            color: #bbb;
            font-size: 1rem;
        }}

        @media (max-width: 480px) {{
            .title {{
                font-size: 1.2rem;
            }}

            .line-destination {{
                font-size: 0.98rem;
            }}

            .right {{
                font-size: 1rem;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="panel">
            <div class="header">
                <div class="title">{STATION_NAME}</div>
                <div class="updated">Updated: {now_str}</div>
            </div>
            {departures_html}
        </div>
    </div>
</body>
</html>
"""
    return html


def write_html_file(html: str) -> None:
    OUTPUT_HTML.write_text(html, encoding="utf-8")


async def main():
    while True:
        print("Fetching departures...")
        departures = await fetch_departures()
        rows = process_departures(departures)
        html = generate_html(rows)
        write_html_file(html)
        print(f"Updated {OUTPUT_HTML.resolve()}")
        await asyncio.sleep(FETCH_INTERVAL_SECONDS)


if __name__ == "__main__":
    asyncio.run(main())