"""
score_rooftops.py

Batch scoring tool: Reads buildings GeoJSON, computes accurate UTM 44N
areas, orientations, NASA POWER solar insolation, TANGEDCO financials,
and outputs a scored GeoJSON ready for map visualization.
"""
import os
import json
from shapely.geometry import shape
from address_to_solar import (
    calculate_building_geometry,
    fetch_irradiance,
    calculate_financials,
    score_to_color,
    USABLE_ROOF_FRACTION,
    PANEL_EFFICIENCY,
    PERFORMANCE_RATIO,
    PANEL_AREA_M2,
    PANEL_RATED_KW,
    TANGEDCO_DOMESTIC_TARIFF
)


def score_feature_collection(geojson_data, center_lat=13.005, center_lon=80.255):
    monthly_irr, annual_irr = fetch_irradiance(center_lat, center_lon)

    days_in_months = {
        "JAN": 31, "FEB": 28, "MAR": 31, "APR": 30, "MAY": 31, "JUN": 30,
        "JUL": 31, "AUG": 31, "SEP": 30, "OCT": 31, "NOV": 30, "DEC": 31
    }

    scored_features = []
    for feature in geojson_data.get("features", []):
        try:
            poly = shape(feature["geometry"])
            geom = calculate_building_geometry(poly)
            roof_area = geom["roof_area_m2"]
            usable_area = round(roof_area * USABLE_ROOF_FRACTION, 1)

            daily_kwh = usable_area * annual_irr * PANEL_EFFICIENCY * PERFORMANCE_RATIO * geom["orientation_factor"]
            annual_kwh = round(daily_kwh * 365, 0)

            monthly_gen = {}
            for m, days in days_in_months.items():
                irr = monthly_irr.get(m, annual_irr)
                monthly_gen[m] = round(usable_area * irr * PANEL_EFFICIENCY * PERFORMANCE_RATIO * geom["orientation_factor"] * days, 1)

            panel_count = max(2, int(usable_area // PANEL_AREA_M2))
            system_kw = round(panel_count * PANEL_RATED_KW, 2)
            if usable_area >= 15:
                system_kw = max(1.0, system_kw)

            props = feature.get("properties", {})
            b_type = props.get("building", props.get("building_type", "residential"))
            tariff = 9.50 if b_type in ["commercial", "retail"] else TANGEDCO_DOMESTIC_TARIFF

            financials = calculate_financials(system_kw, annual_kwh, tariff_per_kwh=tariff)

            area_pts = min(45.0, (usable_area / 150.0) * 45.0)
            irr_pts = min(30.0, (annual_irr / 5.5) * 25.0 + (geom["orientation_factor"] / 1.0) * 5.0)
            pb_pts = max(0.0, min(25.0, (6.5 - financials["payback_years"]) * 5.5)) if financials["payback_years"] > 0 else 10.0
            solar_score = int(round(min(100.0, max(15.0, area_pts + irr_pts + pb_pts))))

            props.update({
                "roof_area_m2": roof_area,
                "roof_area_sqft": round(roof_area * 10.7639, 1),
                "usable_area_m2": usable_area,
                "usable_area_sqft": round(usable_area * 10.7639, 1),
                "orientation_deg": geom["orientation_deg"],
                "aspect_ratio": geom["aspect_ratio"],
                "orientation_factor": geom["orientation_factor"],
                "annual_irradiance_kwh_m2_day": annual_irr,
                "annual_kwh_potential": annual_kwh,
                "monthly_generation_kwh": monthly_gen,
                "recommended_system_size_kw": system_kw,
                "recommended_panel_count": panel_count,
                "solar_score": solar_score,
                "score_0_100": solar_score,
                "fill_color": score_to_color(solar_score),
                "financials": financials
            })

            scored_features.append(feature)
        except Exception as e:
            continue

    return {"type": "FeatureCollection", "features": scored_features}


if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.abspath(__file__))
    input_path = os.path.join(base_dir, "..", "data", "buildings.geojson")
    output_path = os.path.join(base_dir, "..", "data", "scored_buildings.geojson")

    if os.path.exists(input_path):
        with open(input_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        scored = score_feature_collection(data)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(scored, f, indent=2)
        print(f"Scored {len(scored['features'])} buildings -> {output_path}")
    else:
        print("Run generate_chennai_data.py first to create buildings dataset.")
