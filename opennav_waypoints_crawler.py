import os
import json
import re
import requests
import pandas as pd
import time
from bs4 import BeautifulSoup
from collections import deque

SAVE_PATH_JSONL = "opennav_waypoints_graphcrawl.jsonl"
START_SEED = "SFO"
MAX_WAYPOINTS = 500
SLEEP_SECONDS = 1

# Load existing data
waypoints = []
visited = set()
if os.path.exists(SAVE_PATH_JSONL):
    with open(SAVE_PATH_JSONL, "r") as f:
        for line in f:
            try:
                wp = json.loads(line)
                waypoints.append(wp)
                visited.add(wp["ident"])
            except json.JSONDecodeError:
                continue
    print(f"Loaded {len(waypoints)} waypoints from {SAVE_PATH_JSONL}")

queue = deque([START_SEED]) if START_SEED not in visited else deque()

headers = {"User-Agent": "Mozilla/5.0"}

def dms_to_dd(deg, min, sec, direction):
    dd = int(deg) + int(min) / 60 + float(sec) / 3600
    return -dd if direction in ["S", "W"] else dd

def extract_coords(text):
    lat_match = re.search(r"Latitude:\s+(\d+)[° ]+(\d+)[\' ]+([\d.]+)[\" ]+([NS])", text)
    lon_match = re.search(r"Longitude:\s+(\d+)[° ]+(\d+)[\' ]+([\d.]+)[\" ]+([EW])", text)
    if lat_match and lon_match:
        lat = dms_to_dd(*lat_match.groups())
        lon = dms_to_dd(*lon_match.groups())
        return lat, lon
    return None, None

def scrape_waypoint(fix_id):
    url = f"https://opennav.com/fix/{fix_id}"
    try:
        response = requests.get(url, headers=headers)
    except requests.RequestException:
        return None, [], []

    if response.status_code != 200:
        return None, [], []

    soup = BeautifulSoup(response.text, "html.parser")
    text = soup.get_text()

    # Extract main waypoint coordinates
    lat, lon = extract_coords(text)
    if lat is None or lon is None:
        return None, [], []

    data = {
        "ident": fix_id,
        "latitude_deg": lat,
        "longitude_deg": lon,
        "source": "OpenNav"
    }

    # Extract neighbors from embedded JavaScript
    neighbor_waypoints = []
    neighbor_names = []
    marker_pattern = re.compile(
        r'LatLng\((-?\d+\.\d+),\s*(-?\d+\.\d+)\).*?title:\s*"(\w+)"',
        re.DOTALL
    )

    for script in soup.find_all("script"):
        script_text = script.string
        if script_text and "google.maps.Marker" in script_text:
            for match in marker_pattern.finditer(script_text):
                nlat, nlon, nname = match.groups()
                neighbor_waypoints.append({
                    "ident": nname,
                    "latitude_deg": float(nlat),
                    "longitude_deg": float(nlon),
                    "source": "OpenNav-neighbor"
                })
                neighbor_names.append(nname)

    return data, neighbor_names, neighbor_waypoints

# Main crawler
while queue and len(visited) < MAX_WAYPOINTS:
    fix_id = queue.popleft()
    if fix_id in visited:
        continue

    data, neighbor_names, neighbor_waypoints = scrape_waypoint(fix_id)
    visited.add(fix_id)

    if data:
        print(f"Scraped: {fix_id} ({len(visited)}/{MAX_WAYPOINTS})")
        waypoints.append(data)
        with open(SAVE_PATH_JSONL, "a") as f:
            f.write(json.dumps(data) + "\n")

        for neighbor in neighbor_waypoints:
            nid = neighbor["ident"]
            if nid not in visited:
                waypoints.append(neighbor)
                visited.add(nid)
                with open(SAVE_PATH_JSONL, "a") as f:
                    f.write(json.dumps(neighbor) + "\n")

        for nid in neighbor_names:
            if nid not in visited:
                queue.append(nid)
    else:
        print(f"Skipped or failed: {fix_id}")

    time.sleep(SLEEP_SECONDS)

# Final export
df = pd.DataFrame(waypoints)
df.to_csv("opennav_waypoints_graphcrawl.csv", index=False)
print("Final CSV saved to opennav_waypoints_graphcrawl.csv")
