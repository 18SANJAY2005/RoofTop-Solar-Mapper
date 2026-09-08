"""
fetch_buildings.py

Pulls building footprint polygons from OpenStreetMap via the Overpass API
for Chennai neighborhoods, and saves them as GeoJSON.
"""
import os
import json
import requests

OVERPASS_MIRRORS = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
]

# Supported neighborhood bounding boxes: (south, west, north, east)
NEIGHBORHOOD_BBOXES = {
    "adyar": (13.000, 80.250, 13.012, 80.264),
    "besant_nagar": (12.992, 80.260, 13.005, 80.273),
    "t_nagar": (13.035, 80.228, 13.048, 80.242),
    "anna_nagar": (13.080, 80.205, 13.092, 80.218),
    "mylapore": (13.028, 80.262, 13.040, 80.274),
    "omr": (12.935, 80.228, 12.950, 80.245),
}


def fetch_buildings(bbox):
    south, west, north, east = bbox
    query = f"""
    [out:json][timeout:25];
    (
      way["building"]({south},{west},{north},{east});
      relation["building"]({south},{west},{north},{east});
    );
    out body;
    >;
    out skel qt;
    """
    headers = {"User-Agent": "ChennaiSolarMapper/2.0"}
    last_err = None
    for url in OVERPASS_MIRRORS:
        try:
            resp = requests.get(url, params={"data": query}, headers=headers, timeout=30)
            if resp.status_code == 200:
                return resp.json()
        except Exception as e:
            last_err = e
            continue
    raise ConnectionError(f"All Overpass mirrors failed: {last_err}")


def osm_to_geojson(osm_data):
    """Convert Overpass JSON (nodes + ways) into GeoJSON polygons."""
    nodes = {el["id"]: (el["lon"], el["lat"])
             for el in osm_data.get("elements", []) if el["type"] == "node"}

    features = []
    for el in osm_data.get("elements", []):
        if el["type"] != "way" or "nodes" not in el:
            continue
        coords = [nodes[n] for n in el["nodes"] if n in nodes]
        if len(coords) < 3:
            continue
        if coords[0] != coords[-1]:
            coords.append(coords[0])
        features.append({
            "type": "Feature",
            "properties": {"osm_id": el["id"], **el.get("tags", {})},
            "geometry": {"type": "Polygon", "coordinates": [coords]}
        })

    return {"type": "FeatureCollection", "features": features}


if __name__ == "__main__":
    nhood_choice = "adyar"
    bbox = NEIGHBORHOOD_BBOXES[nhood_choice]
    print(f"Fetching buildings for {nhood_choice.title()} {bbox}...")
    try:
        raw = fetch_buildings(bbox)
        geojson = osm_to_geojson(raw)
        out_path = os.path.join(os.path.dirname(__file__), "..", "data", f"buildings_{nhood_choice}.geojson")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(geojson, f, indent=2)
        print(f"Saved {len(geojson['features'])} footprints to {out_path}")
    except Exception as e:
        print(f"Live fetch notice: {e}. You can use generate_chennai_data.py for offline datasets.")
