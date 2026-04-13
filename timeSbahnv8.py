import datetime
import pandas as pd
import pytz
from mvg import MvgApi, TransportType
import asyncio
from luma.core.interface.serial import spi
from luma.oled.device import ssd1322
from luma.core.render import canvas
from PIL import ImageFont
import time
import signal
import sys

# Initialize the SPI interface
try:
    serial = spi(device=0, port=0, gpio_DC=24, gpio_RST=25, gpio_CS=8, bus_speed_hz=8000000)
    print("SPI interface initialized successfully.")
except Exception as e:
    print(f"Failed to initialize SPI: {e}")
    sys.exit(1)

# Create the SSD1322 OLED device
try:
    device = ssd1322(serial)
    print("OLED device initialized successfully.")
except Exception as e:
    print(f"Failed to initialize OLED device: {e}")
    sys.exit(1)

# Set brightness (contrast)
brightness_level = 128  # Adjust this value between 0 and 255
device.contrast(brightness_level)
print(f"Set brightness to level: {brightness_level}")

# Load fonts
font_regular = ImageFont.load_default()
font_bold = ImageFont.truetype("DejaVuSans-Bold.ttf", 14)  # Adjust the font size as needed

#font_regular = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 16)
#font_bold = ImageFont.truetype("/usr/share/fonts/truetype/msttcorefonts/Arial-Bold.ttf", 14)

# Define the Munich timezone (outside of the main function for efficiency)
munich_tz = pytz.timezone('Europe/Berlin')
print("Timezone set to Europe/Berlin.")

# Signal handler for graceful exit
def signal_handler(sig, frame):
    print("Signal received, exiting...")
    device.clear()  # Clear the display before exiting
    sys.exit(0)

# Register the signal handler
signal.signal(signal.SIGINT, signal_handler)

# Set initial brightness level
daytime_brightness = 255  # Adjust this value as needed for daytime brightness
nighttime_brightness = 5  # Adjust this value as needed for nighttime brightness

# Function to adjust brightness based on the time of day
def adjust_brightness():
    current_time = datetime.datetime.now(munich_tz)
    current_hour = current_time.hour

    if 6 <= current_hour < 22:
        device.contrast(daytime_brightness)
        print(f"Set brightness to daytime level: {daytime_brightness}")
    else:
        device.contrast(nighttime_brightness)
        print(f"Set brightness to nighttime level: {nighttime_brightness}")


async def fdeparture() -> list:
    print("Fetching departure data...")
#    station_id = 'de:09162:1910'
    station_id ='de:09162:1700'
    try:
        departures = await MvgApi.departures_async(
            station_id,
            limit=6,
            offset=1,
            transport_types=[TransportType.SBAHN]
        )
        print(f"Fetched {len(departures)} departures.")
        return departures
    except Exception as e:
        print(f"Failed to fetch departures: {e}")
        return []

async def main():
    s_bahn_data = []
    last_fetch_time = None

    while True:
        # Fetch new departure data every 30 seconds
        current_time = datetime.datetime.now()
        if last_fetch_time is None or (current_time - last_fetch_time).total_seconds() >= 30:
            departures = await fdeparture()
            departures = [departure for departure in departures if not departure['cancelled']]
            adjust_brightness()
            if not departures:
                print("No departures found.")
            else:
                # Process and filter data
                s_bahn_data = []
                for item in departures:
                    departure_time = datetime.datetime.fromtimestamp(item['time'], pytz.utc).astimezone(munich_tz)
                    s_bahn_data.append({
                        'line': item['line'],
                        'destination': item['destination'],
                        'departure_time': departure_time
                    })
                    print(f"Processed departure: {item['line']} -> {item['destination']} at {departure_time.strftime('%H:%M')}")

                last_fetch_time = current_time

        # Update display every 5 seconds based on the existing data
        if s_bahn_data:
            current_time = datetime.datetime.now(munich_tz)
            df_s_bahn = pd.DataFrame(s_bahn_data)

            # Recalculate the minutes until departure
            df_s_bahn['delta (min)'] = df_s_bahn['departure_time'].apply(
                lambda x: int((x - current_time).total_seconds() // 60)
            )

            # Format the DataFrame for aligned display
            display_texts = []
            for index, row in df_s_bahn.iterrows():
                line_text = f"{row['line']} {row['destination']}"
                minutes_text = f"{row['delta (min)']:>2}min"
                display_texts.append((line_text, minutes_text))

            # Show the train timetable on the OLED display
            try:
                with canvas(device) as draw:
                    y = 0
                    for line_text, minutes_text in display_texts:
                        # Draw the line and destination text
                        draw.text((0, y), line_text, font=font_bold, fill="white")

                        # Calculate the width of the minutes text and align it to the right
                        minutes_width = draw.textbbox((0, 0), minutes_text, font=font_bold)[2]
                        draw.text((device.width - minutes_width, y), minutes_text, font=font_bold, fill="white")

                        # Move to the next line based on the height of the bold text
                        line_height = draw.textbbox((0, 0), line_text, font=font_bold)[3]
                        y += line_height + 2
                print("Displayed timetable on OLED.")
            except Exception as e:
                print(f"Failed to display timetable on OLED: {e}")

        # Wait 5 seconds before updating the display again
        time.sleep(5)

# Run the main function
print("Starting script...")
asyncio.run(main())
print("Script finished.")
