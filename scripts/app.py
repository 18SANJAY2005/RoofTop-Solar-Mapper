"""
app.py

Production-ready Flask Web API & Geospatial Dashboard server for Rooftop Solar Potential Mapper (Chennai).
Features:
- Instant address autocompletion & manual address prediction
- Full GIS map frontend serving Leaflet with Esri Satellite, Dark, and Street basemaps
- Dynamic Chennai neighborhood endpoints (Adyar, Besant Nagar, T. Nagar, Anna Nagar, Mylapore, OMR)
- Single address and coordinate real-time solar evaluation
- Support for custom manual terrace drawing and monthly bill customization
- Satellite AI rooftop segmentation endpoint (U-Net + OpenCV contour extraction)
- City-level aggregation statistics (MWp potential, GWh generation, CO2 offset)
"""
import os
import sys
import json
from flask import Flask, request, jsonify, send_from_directory

base_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(base_dir, ".."))
if base_dir not in sys.path:
    sys.path.insert(0, base_dir)
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from address_to_solar import (
    estimate_solar_potential,
    geocode_address,
    CHENNAI_LOCALITY_INDEX
)
from segmentation.infer import get_segmentation_preview

app = Flask(__name__, static_folder="static")

DATA_DIR = os.path.join(root_dir, "data")
MASTER_GEOJSON_PATH = os.path.join(DATA_DIR, "scored_buildings.geojson")
STATS_PATH = os.path.join(DATA_DIR, "city_stats.json")
NHOOD_DIR = os.path.join(DATA_DIR, "neighborhoods")


@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.route("/api/suggestions")
def api_suggestions():
    """Returns instant autocomplete suggestions for manual address typing."""
    q = request.args.get("q", "").strip().lower()
    if not q or len(q) < 2:
        return jsonify([])

    results = []
    seen = set()
    for key, (lat, lon, name) in CHENNAI_LOCALITY_INDEX.items():
        if q in key or q in name.lower():
            if name not in seen:
                seen.add(name)
                results.append({"name": name, "lat": lat, "lon": lon})
                if len(results) >= 6:
                    return jsonify(results)

    # If fewer than 5 results and query has >= 3 chars, supplement with Photon biased to Chennai
    if len(results) < 5 and len(q) >= 3:
        try:
            r = requests.get("https://photon.komoot.io/api/", params={
                "q": q,
                "lat": 13.0827,
                "lon": 80.2707,
                "limit": 5
            }, headers={"User-Agent": "Mozilla/5.0"}, timeout=1.5)
            if r.status_code == 200:
                for f in r.json().get("features", []):
                    coords = f.get("geometry", {}).get("coordinates", [])
                    if len(coords) >= 2:
                        p_lon, p_lat = float(coords[0]), float(coords[1])
                        if 12.8 <= p_lat <= 13.3 and 80.0 <= p_lon <= 80.35:
                            p_name = f.get("properties", {}).get("name", "")
                            p_street = f.get("properties", {}).get("street", "")
                            full_label = f"{p_name}, {p_street}, Chennai".replace(", ,", ",").strip(", ")
                            if full_label not in seen and p_name:
                                seen.add(full_label)
                                results.append({"name": full_label, "lat": p_lat, "lon": p_lon})
                                if len(results) >= 6:
                                    break
        except Exception:
            pass

    return jsonify(results)


@app.route("/api/neighborhoods")
def api_neighborhoods():
    """Returns metadata for all supported Chennai neighborhood presets."""
    if os.path.exists(STATS_PATH):
        with open(STATS_PATH, "r", encoding="utf-8") as f:
            stats = json.load(f)
            return jsonify(stats.get("neighborhoods", {}))

    fallback = {
        "adyar": {"name": "Adyar", "center": [13.0065, 80.2570], "building_count": 55},
        "besant_nagar": {"name": "Besant Nagar", "center": [12.9990, 80.2675], "building_count": 45},
        "t_nagar": {"name": "T. Nagar", "center": [13.0415, 80.2335], "building_count": 60},
        "anna_nagar": {"name": "Anna Nagar", "center": [13.0850, 80.2100], "building_count": 55},
        "mylapore": {"name": "Mylapore", "center": [13.0335, 80.2685], "building_count": 50},
        "omr": {"name": "OMR / Thoraipakkam", "center": [12.9420, 80.2360], "building_count": 50},
    }
    return jsonify(fallback)


@app.route("/api/buildings")
def api_buildings():
    """Returns scored GeoJSON for a requested neighborhood or all Chennai buildings."""
    nhood = request.args.get("neighborhood", "all").strip().lower()

    if nhood != "all":
        nhood_path = os.path.join(NHOOD_DIR, f"{nhood}.geojson")
        if os.path.exists(nhood_path):
            with open(nhood_path, "r", encoding="utf-8") as f:
                return jsonify(json.load(f))

    if os.path.exists(MASTER_GEOJSON_PATH):
        with open(MASTER_GEOJSON_PATH, "r", encoding="utf-8") as f:
            return jsonify(json.load(f))

    return jsonify({"type": "FeatureCollection", "features": []})


@app.route("/api/estimate", methods=["GET", "POST"])
def api_estimate():
    """
    Evaluates solar potential for any home address or (lat, lon) coordinates.
    Supports GET (query params) and POST (JSON body).
    """
    if request.method == "POST":
        payload = request.get_json(silent=True) or {}
        address = payload.get("address", "").strip()
        lat = payload.get("lat")
        lon = payload.get("lon")
        use_satellite = bool(payload.get("use_satellite", False))
        monthly_bill = payload.get("monthly_bill")
        roof_sqft = payload.get("roof_sqft")
        custom_coords = payload.get("custom_coords")
    else:
        address = request.args.get("address", "").strip()
        lat = request.args.get("lat", type=float)
        lon = request.args.get("lon", type=float)
        use_satellite = request.args.get("use_satellite", "false").lower() == "true"
        monthly_bill = request.args.get("monthly_bill", default=None, type=float)
        roof_sqft = request.args.get("roof_sqft", default=None, type=float)
        custom_coords = None

    try:
        if custom_coords:
            result = estimate_solar_potential(
                address_or_coords=address if address else (lat if (lat is not None and lon is not None) else (0, 0)),
                use_satellite_segmentation=False,
                monthly_bill=monthly_bill,
                custom_roof_sqft=roof_sqft,
                custom_coords=custom_coords
            )
        elif lat is not None and lon is not None:
            result = estimate_solar_potential(
                (lat, lon),
                use_satellite_segmentation=use_satellite,
                monthly_bill=monthly_bill,
                custom_roof_sqft=roof_sqft
            )
        elif address:
            result = estimate_solar_potential(
                address,
                use_satellite_segmentation=use_satellite,
                monthly_bill=monthly_bill,
                custom_roof_sqft=roof_sqft
            )
        else:
            return jsonify({"error": "Please enter an address or click a location on the map"}), 400

        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/segment_satellite")
def api_segment_satellite():
    """
    Fetches real satellite tile for (lat, lon), runs U-Net segmentation,
    and returns base64 images and detected rooftop polygon.
    """
    lat = request.args.get("lat", default=13.0065, type=float)
    lon = request.args.get("lon", default=80.2570, type=float)
    zoom = request.args.get("zoom", default=18, type=int)

    try:
        preview = get_segmentation_preview(lat, lon, zoom=zoom)
        return jsonify(preview)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/stats")
def api_stats():
    """Returns city-level aggregate solar capacity and carbon reduction metrics."""
    if os.path.exists(STATS_PATH):
        with open(STATS_PATH, "r", encoding="utf-8") as f:
            return jsonify(json.load(f))

    return jsonify({
        "total_buildings": 315,
        "total_solar_mw": 18.39,
        "total_annual_gwh": 24.71,
        "total_co2_offset_tons": 20262.9
    })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"Starting Rooftop Solar Potential Mapper (Chennai) on http://127.0.0.1:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)
