"""
Generates realistic SAMPLE data shaped exactly like what fetch_buildings.py
and fetch_irradiance.py would produce, so we can test the rest of the
pipeline without live network access. Replace data/buildings.geojson and
data/irradiance.json with real fetched data when you run those scripts
on your own machine.
"""
import json
import random

random.seed(42)

# --- Sample buildings.geojson (mimics OSM Overpass output for Adyar) ---
center_lat, center_lon = 13.005, 80.255
features = []
for i in range(40):
    # random small building footprint near the center point
    lat = center_lat + random.uniform(-0.004, 0.004)
    lon = center_lon + random.uniform(-0.004, 0.004)
    size = random.uniform(0.00006, 0.00025)  # roughly 6m-25m across
    coords = [
        [lon, lat],
        [lon + size, lat],
        [lon + size, lat + size],
        [lon, lat + size],
        [lon, lat],
    ]
    features.append({
        "type": "Feature",
        "properties": {"osm_id": 1000 + i, "building": random.choice(["yes", "residential", "house", "apartments"])},
        "geometry": {"type": "Polygon", "coordinates": [coords]}
    })

buildings = {"type": "FeatureCollection", "features": features}
with open("data/buildings.geojson", "w") as f:
    json.dump(buildings, f)
print(f"Generated {len(features)} sample buildings -> data/buildings.geojson")

# --- Sample irradiance.json (mimics NASA POWER output for Chennai) ---
# Chennai's real annual average is roughly 5.2-5.5 kWh/m^2/day - using a
# realistic value, not a random one.
irradiance = {
    "lat": center_lat,
    "lon": center_lon,
    "monthly_kwh_m2_day": {
        "JAN": 4.9, "FEB": 5.6, "MAR": 6.2, "APR": 6.5, "MAY": 6.3, "JUN": 5.4,
        "JUL": 5.1, "AUG": 5.3, "SEP": 5.4, "OCT": 4.7, "NOV": 4.2, "DEC": 4.4,
        "ANN": 5.33
    },
    "annual_avg_kwh_m2_day": 5.33
}
with open("data/irradiance.json", "w") as f:
    json.dump(irradiance, f, indent=2)
print("Generated sample irradiance -> data/irradiance.json (Chennai annual avg: 5.33 kWh/m^2/day)")
