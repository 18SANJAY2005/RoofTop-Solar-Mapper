"""
generate_chennai_data.py

Generates high-fidelity building footprint datasets with comprehensive solar & financial
scoring across major Chennai neighborhoods:
- Adyar (Residential & Coastal)
- Besant Nagar (Coastal Residential)
- T. Nagar (Commercial & High-Density)
- Anna Nagar (Grid Residential & Commercial)
- Mylapore (Traditional High-Density)
- OMR / Thoraipakkam (Tech Parks & Modern Apartments)
"""
import os
import json
import math
import random
from shapely.geometry import Polygon
from shapely.ops import transform
import pyproj

# UTM Zone 44N for accurate metric area in Chennai
project_to_utm = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:32644", always_xy=True).transform

USABLE_ROOF_FRACTION = 0.72
PANEL_EFFICIENCY = 0.21
PERFORMANCE_RATIO = 0.78
PANEL_AREA_M2 = 1.95
PANEL_RATED_KW = 0.45
BENCHMARK_COST_PER_KW = 55000
TANGEDCO_DOMESTIC_TARIFF = 7.00
TARIFF_ANNUAL_ESCALATION = 0.03
PANEL_DEGRADATION_RATE = 0.005
GRID_EMISSION_FACTOR_KG_KWH = 0.82
TREE_CO2_ABSORPTION_KG_YEAR = 20.0

CHENNAI_ANNUAL_IRRADIANCE = 5.38
MONTHLY_IRRADIANCE = {
    "JAN": 4.92, "FEB": 5.68, "MAR": 6.31, "APR": 6.54,
    "MAY": 6.38, "JUN": 5.42, "JUL": 5.12, "AUG": 5.34,
    "SEP": 5.46, "OCT": 4.75, "NOV": 4.22, "DEC": 4.45,
    "ANN": 5.38
}
DAYS_IN_MONTHS = {
    "JAN": 31, "FEB": 28, "MAR": 31, "APR": 30, "MAY": 31, "JUN": 30,
    "JUL": 31, "AUG": 31, "SEP": 30, "OCT": 31, "NOV": 30, "DEC": 31
}

NEIGHBORHOODS = [
    {
        "id": "adyar",
        "name": "Adyar",
        "center": [13.0065, 80.2570],
        "count": 55,
        "streets": ["1st Main Road, Kasturba Nagar", "Canal Bank Road, Gandhi Nagar", "Lattice Bridge Road", "Sardar Patel Road", "Padmanabha Nagar"],
        "types": [("house", 0.4), ("residential", 0.35), ("apartments", 0.15), ("commercial", 0.1)],
        "size_range": (80, 420),
    },
    {
        "id": "besant_nagar",
        "name": "Besant Nagar",
        "center": [12.9990, 80.2675],
        "count": 45,
        "streets": ["4th Main Road", "Beach Road", "Tiger Varadachari Road", "Customs Colony", "Elliot's Promenade"],
        "types": [("house", 0.45), ("apartments", 0.35), ("commercial", 0.2)],
        "size_range": (100, 480),
    },
    {
        "id": "t_nagar",
        "name": "T. Nagar",
        "center": [13.0415, 80.2335],
        "count": 60,
        "streets": ["Usman Road", "Pondy Bazaar", "G.N. Chetty Road", "North Usman Road", "Venkatnarayana Road", "Burkit Road"],
        "types": [("commercial", 0.55), ("apartments", 0.25), ("house", 0.2)],
        "size_range": (120, 850),
    },
    {
        "id": "anna_nagar",
        "name": "Anna Nagar",
        "center": [13.0850, 80.2100],
        "count": 55,
        "streets": ["2nd Avenue", "Shanthi Colony", "3rd Avenue", "Roundtana Circle", "12th Main Road"],
        "types": [("residential", 0.45), ("commercial", 0.3), ("apartments", 0.25)],
        "size_range": (110, 600),
    },
    {
        "id": "mylapore",
        "name": "Mylapore",
        "center": [13.0335, 80.2685],
        "count": 50,
        "streets": ["North Mada Street", "Kutchery Road", "Luz Church Road", "Royapettah High Road", "South Mada Street"],
        "types": [("house", 0.55), ("residential", 0.3), ("commercial", 0.15)],
        "size_range": (70, 320),
    },
    {
        "id": "omr",
        "name": "OMR / Thoraipakkam",
        "center": [12.9420, 80.2360],
        "count": 50,
        "streets": ["Rajiv Gandhi Salai", "Okkiyam Thoraipakkam", "Pallavaram-Thoraipakkam Radial Rd", "Chandrasekhar Avenue"],
        "types": [("apartments", 0.45), ("commercial", 0.4), ("house", 0.15)],
        "size_range": (200, 1500),
    },
]


def score_to_color(score):
    if score >= 75:
        return "#10b981"  # Emerald Green (High)
    elif score >= 50:
        return "#84cc16"  # Lime Green (Good)
    elif score >= 30:
        return "#f59e0b"  # Amber (Moderate)
    else:
        return "#ef4444"  # Red (Low)


def generate_building_polygon(center_lat, center_lon, target_area_m2, angle_deg):
    """
    Generates realistic building polygon (rectangle or L-shape)
    with target ground area in square meters.
    """
    # In Chennai (~13°N): 1 deg lat ~ 110,574m, 1 deg lon ~ 108,450m
    meters_to_lat = 1.0 / 110574.0
    meters_to_lon = 1.0 / 108450.0

    # Side lengths
    aspect = random.uniform(1.1, 2.2)
    w_m = math.sqrt(target_area_m2 / aspect)
    l_m = w_m * aspect

    # 25% chance of L-shaped roof
    shape_type = "L" if random.random() < 0.25 else "rect"
    rad = math.radians(angle_deg)
    cos_a, sin_a = math.cos(rad), math.sin(rad)

    def rot(x, y):
        rx = x * cos_a - y * sin_a
        ry = x * sin_a + y * cos_a
        return rx * meters_to_lon + center_lon, ry * meters_to_lat + center_lat

    hw = w_m / 2.0
    hl = l_m / 2.0

    if shape_type == "rect":
        local_pts = [
            (-hw, -hl),
            (hw, -hl),
            (hw, hl),
            (-hw, hl),
            (-hw, -hl)
        ]
    else:
        cut_w = hw * random.uniform(0.35, 0.65)
        cut_l = hl * random.uniform(0.35, 0.65)
        local_pts = [
            (-hw, -hl),
            (hw, -hl),
            (hw, cut_l),
            (cut_w, cut_l),
            (cut_w, hl),
            (-hw, hl),
            (-hw, -hl)
        ]

    coords = [list(rot(x, y)) for x, y in local_pts]
    poly = Polygon(coords)
    if not poly.is_valid:
        poly = poly.buffer(0)
    return poly


def compute_solar_properties(poly, neighborhood_name, street_name, building_type, osm_id):
    # Metric projection for exact surface area
    poly_utm = transform(project_to_utm, poly)
    roof_area = round(poly_utm.area, 1)
    perimeter_m = round(poly_utm.length, 1)

    usable_area = round(roof_area * USABLE_ROOF_FRACTION, 1)

    # Orientation & Aspect
    rect = poly_utm.minimum_rotated_rectangle
    rect_coords = list(rect.exterior.coords)
    orientation_deg = 0.0
    aspect_ratio = 1.0
    if len(rect_coords) >= 4:
        dx = rect_coords[1][0] - rect_coords[0][0]
        dy = rect_coords[1][1] - rect_coords[0][1]
        orientation_deg = (math.degrees(math.atan2(dy, dx)) + 360) % 180
        aspect_ratio = round(math.hypot(dx, dy) / (math.hypot(rect_coords[2][0] - rect_coords[1][0], rect_coords[2][1] - rect_coords[1][1]) or 1.0), 2)
        if aspect_ratio < 1.0:
            aspect_ratio = round(1.0 / aspect_ratio, 2)

    orientation_factor = 0.98 if (orientation_deg < 25 or orientation_deg > 155) else 0.95

    # Energy Potential
    annual_irr = CHENNAI_ANNUAL_IRRADIANCE
    daily_kwh = usable_area * annual_irr * PANEL_EFFICIENCY * PERFORMANCE_RATIO * orientation_factor
    annual_kwh = round(daily_kwh * 365, 0)

    # Monthly generation
    monthly_gen = {}
    for m, days in DAYS_IN_MONTHS.items():
        irr = MONTHLY_IRRADIANCE[m]
        monthly_gen[m] = round(usable_area * irr * PANEL_EFFICIENCY * PERFORMANCE_RATIO * orientation_factor * days, 1)

    # PV System Sizing
    panel_count = max(4, int(usable_area // PANEL_AREA_M2))
    system_kw = round(panel_count * PANEL_RATED_KW, 1)

    # Financials
    gross_capex = round(system_kw * BENCHMARK_COST_PER_KW, 0)
    if system_kw < 0.8:
        subsidy = 0.0
    elif system_kw < 1.5:
        subsidy = 30000.0
    elif system_kw < 2.5:
        subsidy = 60000.0
    else:
        subsidy = 78000.0

    net_capex = max(0.0, gross_capex - subsidy)
    tariff = 9.50 if building_type == "commercial" else TANGEDCO_DOMESTIC_TARIFF
    annual_savings = round(annual_kwh * tariff, 0)
    payback_years = round(net_capex / annual_savings, 1) if annual_savings > 0 else 0.0

    # 25-yr cumulative savings
    cumulative_savings = 0.0
    cur_tariff = tariff
    cur_gen = annual_kwh
    for _ in range(25):
        cumulative_savings += cur_gen * cur_tariff
        cur_gen *= (1.0 - PANEL_DEGRADATION_RATE)
        cur_tariff *= (1.0 + TARIFF_ANNUAL_ESCALATION)

    co2_tons = round((annual_kwh * GRID_EMISSION_FACTOR_KG_KWH) / 1000.0, 2)
    trees = int(round((annual_kwh * GRID_EMISSION_FACTOR_KG_KWH) / TREE_CO2_ABSORPTION_KG_YEAR))

    # Normalized Solar Score (0 - 100)
    area_pts = min(45.0, (usable_area / 150.0) * 45.0)
    irr_pts = min(30.0, (annual_irr / 5.5) * 25.0 + (orientation_factor / 1.0) * 5.0)
    pb_pts = max(0.0, min(25.0, (6.5 - payback_years) * 5.5)) if payback_years > 0 else 10.0
    solar_score = int(round(min(100.0, max(15.0, area_pts + irr_pts + pb_pts))))

    door_num = random.randint(1, 140)
    full_address = f"#{door_num}, {street_name}, {neighborhood_name}, Chennai"

    return {
        "osm_id": osm_id,
        "neighborhood": neighborhood_name,
        "address": full_address,
        "building_type": building_type,
        "roof_area_m2": roof_area,
        "roof_area_sqft": round(roof_area * 10.7639, 1),
        "usable_area_m2": usable_area,
        "usable_area_sqft": round(usable_area * 10.7639, 1),
        "orientation_deg": round(orientation_deg, 1),
        "aspect_ratio": aspect_ratio,
        "orientation_factor": orientation_factor,
        "annual_irradiance_kwh_m2_day": annual_irr,
        "annual_kwh_potential": annual_kwh,
        "monthly_generation_kwh": monthly_gen,
        "recommended_system_size_kw": system_kw,
        "recommended_panel_count": panel_count,
        "solar_score": solar_score,
        "fill_color": score_to_color(solar_score),
        "financials": {
            "gross_capex_inr": gross_capex,
            "subsidy_inr": subsidy,
            "net_capex_inr": net_capex,
            "annual_savings_inr": annual_savings,
            "monthly_savings_inr": round(annual_savings / 12.0, 0),
            "payback_years": payback_years,
            "lifetime_savings_25yr_inr": round(cumulative_savings, 0),
            "co2_tons_annual": co2_tons,
            "trees_equivalent": trees,
            "tariff_inr_per_kwh": tariff
        }
    }


def generate_dataset():
    random.seed(42)
    all_features = []
    building_id_counter = 10000

    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, "..", "data")
    os.makedirs(data_dir, exist_ok=True)
    nhood_dir = os.path.join(data_dir, "neighborhoods")
    os.makedirs(nhood_dir, exist_ok=True)

    summary_stats = {
        "total_buildings": 0,
        "total_solar_kw": 0.0,
        "total_annual_mwh": 0.0,
        "total_co2_offset_tons": 0.0,
        "neighborhoods": {}
    }

    for nhood in NEIGHBORHOODS:
        c_lat, c_lon = nhood["center"]
        nhood_features = []
        nh_kw = 0.0
        nh_kwh = 0.0

        # Create structured street cluster grid
        rows = int(math.ceil(math.sqrt(nhood["count"])))
        cols = rows

        idx = 0
        for r in range(rows):
            for c in range(cols):
                if idx >= nhood["count"]:
                    break
                idx += 1
                building_id_counter += 1

                # Grid offset with jitter
                lat_jitter = (r - rows / 2.0) * 0.0011 + random.uniform(-0.00025, 0.00025)
                lon_jitter = (c - cols / 2.0) * 0.0012 + random.uniform(-0.00025, 0.00025)
                b_lat = c_lat + lat_jitter
                b_lon = c_lon + lon_jitter

                # Pick building type
                b_type = random.choices([t[0] for t in nhood["types"]], weights=[t[1] for t in nhood["types"]])[0]

                # Pick size range
                s_min, s_max = nhood["size_range"]
                if b_type == "commercial":
                    target_area = random.uniform(s_min * 1.5, s_max * 1.2)
                elif b_type == "apartments":
                    target_area = random.uniform(s_min * 1.2, s_max)
                else:
                    target_area = random.uniform(s_min, s_min * 2.2)

                angle = random.choice([0, 15, 30, 45, 90, 105, 120]) + random.uniform(-5, 5)
                poly = generate_building_polygon(b_lat, b_lon, target_area, angle)

                street = random.choice(nhood["streets"])
                props = compute_solar_properties(poly, nhood["name"], street, b_type, building_id_counter)

                nh_kw += props["recommended_system_size_kw"]
                nh_kwh += props["annual_kwh_potential"]

                feature = {
                    "type": "Feature",
                    "properties": props,
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [list(poly.exterior.coords)]
                    }
                }
                nhood_features.append(feature)
                all_features.append(feature)

        # Save neighborhood specific GeoJSON
        nhood_fc = {"type": "FeatureCollection", "features": nhood_features}
        with open(os.path.join(nhood_dir, f"{nhood['id']}.geojson"), "w", encoding="utf-8") as f:
            json.dump(nhood_fc, f, indent=2)

        summary_stats["neighborhoods"][nhood["id"]] = {
            "name": nhood["name"],
            "center": nhood["center"],
            "building_count": len(nhood_features),
            "total_capacity_kw": round(nh_kw, 1),
            "total_annual_mwh": round(nh_kwh / 1000.0, 1)
        }

    # Save master scored buildings GeoJSON
    master_fc = {"type": "FeatureCollection", "features": all_features}
    master_path = os.path.join(data_dir, "scored_buildings.geojson")
    with open(master_path, "w", encoding="utf-8") as f:
        json.dump(master_fc, f, indent=2)

    # Save buildings.geojson as well for compatibility
    buildings_path = os.path.join(data_dir, "buildings.geojson")
    with open(buildings_path, "w", encoding="utf-8") as f:
        json.dump(master_fc, f, indent=2)

    total_kw = sum(f["properties"]["recommended_system_size_kw"] for f in all_features)
    total_kwh = sum(f["properties"]["annual_kwh_potential"] for f in all_features)
    total_co2 = sum(f["properties"]["financials"]["co2_tons_annual"] for f in all_features)

    summary_stats["total_buildings"] = len(all_features)
    summary_stats["total_solar_kw"] = round(total_kw, 1)
    summary_stats["total_solar_mw"] = round(total_kw / 1000.0, 2)
    summary_stats["total_annual_mwh"] = round(total_kwh / 1000.0, 1)
    summary_stats["total_annual_gwh"] = round(total_kwh / 1000000.0, 3)
    summary_stats["total_co2_offset_tons"] = round(total_co2, 1)

    stats_path = os.path.join(data_dir, "city_stats.json")
    with open(stats_path, "w", encoding="utf-8") as f:
        json.dump(summary_stats, f, indent=2)

    print(f"Generated {len(all_features)} buildings across {len(NEIGHBORHOODS)} Chennai neighborhoods.")
    print(f"Total Solar Potential: {summary_stats['total_solar_mw']} MWp ({summary_stats['total_annual_gwh']} GWh/year)")
    print(f"Total CO2 Offset: {summary_stats['total_co2_offset_tons']} metric tons/year")
    print(f"Saved to {master_path} and {stats_path}")


if __name__ == "__main__":
    generate_dataset()

