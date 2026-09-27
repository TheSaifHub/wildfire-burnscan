"""
Pulls NASA FIRMS fire-detection points around the Camp Fire's known location
and date, as an independent cross-check against the MTBS record.

Requires a FIRMS_API_KEY environment variable (see .env).
"""

import os
import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()

FIRMS_API_KEY = os.environ["FIRMS_API_KEY"]

# Bounding box roughly around Butte County / Paradise, CA (west, south, east, north)
BBOX = "-121.75,39.60,-121.35,39.95"

# VIIRS 375m data, standard (archival) processing -- required for a date this far back
SOURCE = "VIIRS_SNPP_SP"
DATE = "2018-11-06"  # a couple days before ignition, to catch the earliest detections
DAY_RANGE = 5         # FIRMS API max is 5; pulls DATE through DATE + DAY_RANGE

url = (
    f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/"
    f"{FIRMS_API_KEY}/{SOURCE}/{BBOX}/{DAY_RANGE}/{DATE}"
)

response = requests.get(url, timeout=30)
response.raise_for_status()

out_path = "data/raw/firms/camp_fire_detections.csv"
with open(out_path, "w", newline="") as f:
    f.write(response.text)

df = pd.read_csv(out_path)
print(f"Pulled {len(df)} detection points -> {out_path}")
print(df[["latitude", "longitude", "acq_date", "acq_time", "confidence", "bright_ti4"]].head(20))
