import asyncio
from datetime import datetime, timedelta, timezone
from pprint import pprint
import json
from aioambient import API
from flask import current_app

AMBIENT_ENDPOINT = 'https://api.ambientweather.net/v1'
MAC = 'C8:C9:A3:14:D7:9E'

async def fetch_first_entry() -> dict:
    """Fetch data from Ambient Weather API, filter to Costa Rica time range, and save to JSON."""
    api = API(current_app.config['AMBIENT_API_KEY'], current_app.config['AMBIENT_APPLICATION_KEY'])

    # Define today and the exact cutoff time in UTC
    today = datetime.now(timezone.utc).date()
    cutoff_datetime = datetime.combine(today, datetime.min.time(), tzinfo=timezone.utc) + timedelta(hours=6)

    # Fetch data for today and tomorrow in UTC
    data = await api.get_device_details(MAC, end_date=today + timedelta(days=1))

    # Filter data to include only entries strictly before the cutoff time
    filtered_data = [
        entry for entry in data 
        if datetime.fromtimestamp(entry['dateutc'] / 1000, tz=timezone.utc) < cutoff_datetime
    ]

    # Return the first entry if available
    return filtered_data[0] if filtered_data else None

def yesterday_rain_mm():
    first_entry = asyncio.run(fetch_first_entry())
    return round(first_entry['dailyrainin']* 25.4)
