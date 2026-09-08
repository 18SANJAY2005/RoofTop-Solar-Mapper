"""
build_map.py

Reads data/scored_buildings.geojson and generates a self-contained, interactive
Leaflet map in output/solar_map.html with Esri high-res satellite imagery,
color-coded rooftop choropleth, popups with TANGEDCO/PM Surya Ghar financials,
and clean energy metrics.
"""
import os
import json

base_dir = os.path.dirname(os.path.abspath(__file__))
input_path = os.path.join(base_dir, "..", "data", "scored_buildings.geojson")
output_dir = os.path.join(base_dir, "..", "output")
os.makedirs(output_dir, exist_ok=True)
output_path = os.path.join(output_dir, "solar_map.html")

if not os.path.exists(input_path):
    print("Error: data/scored_buildings.geojson not found. Run generate_chennai_data.py first.")
    exit(1)

with open(input_path, "r", encoding="utf-8") as f:
    geojson_data = json.load(f)

# Total stats
total_buildings = len(geojson_data["features"])
total_kw = sum(f["properties"].get("recommended_system_size_kw", 0) for f in geojson_data["features"])
total_kwh = sum(f["properties"].get("annual_kwh_potential", 0) for f in geojson_data["features"])
total_co2 = sum(f["properties"].get("financials", {}).get("co2_tons_annual", 0) for f in geojson_data["features"])

geojson_str = json.dumps(geojson_data)

html_template = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Chennai Rooftop Solar Potential — Standalone Map</title>
  <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css" />
  <script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js"></script>
  <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;600;700;800&family=JetBrains+Mono:wght@600&display=swap" rel="stylesheet">
  <style>
    body { margin: 0; padding: 0; font-family: 'Plus Jakarta Sans', sans-serif; background: #0b0f19; color: #fff; }
    #map { height: 100vh; width: 100vw; }
    .header-bar {
      position: absolute; top: 16px; left: 20px; z-index: 1000;
      background: rgba(17, 24, 39, 0.92); backdrop-filter: blur(14px);
      border: 1px solid rgba(255, 255, 255, 0.12); border-radius: 12px;
      padding: 12px 20px; box-shadow: 0 8px 30px rgba(0,0,0,0.5);
      display: flex; align-items: center; gap: 20px;
    }
    .brand-title { font-size: 15px; font-weight: 800; background: linear-gradient(90deg, #f59e0b, #38bdf8); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
    .brand-sub { font-size: 11px; color: #9ca3af; }
    .stat-pill { display: flex; flex-direction: column; border-left: 1px solid rgba(255,255,255,0.1); padding-left: 14px; }
    .stat-pill .lbl { font-size: 9px; text-transform: uppercase; color: #6b7280; font-weight: 700; }
    .stat-pill .val { font-size: 13px; font-weight: 800; color: #fff; }
    .legend {
      position: absolute; bottom: 24px; left: 20px; z-index: 1000;
      background: rgba(17, 24, 39, 0.92); backdrop-filter: blur(14px);
      border: 1px solid rgba(255, 255, 255, 0.12); border-radius: 12px;
      padding: 12px 16px; font-size: 11px; box-shadow: 0 8px 30px rgba(0,0,0,0.5);
    }}
    .legend-title { font-weight: 700; color: #9ca3af; margin-bottom: 6px; text-transform: uppercase; letter-spacing: 0.05em; }
    .legend-row { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; font-weight: 600; }
    .swatch { width: 12px; height: 12px; border-radius: 3px; }
    .leaflet-popup-content-wrapper {
      background: rgba(17, 24, 39, 0.95) !important;
      backdrop-filter: blur(16px);
      border: 1px solid rgba(255, 255, 255, 0.15) !important;
      color: #fff !important;
      border-radius: 12px !important;
      box-shadow: 0 10px 40px rgba(0,0,0,0.6) !important;
    }
    .leaflet-popup-tip { background: rgba(17, 24, 39, 0.95) !important; }
    .popup-content h4 { font-size: 14px; font-weight: 800; margin: 0 0 4px; color: #38bdf8; }
    .popup-content p { font-size: 11px; color: #9ca3af; margin: 0 0 10px; }
    .popup-stat { display: flex; justify-content: space-between; font-size: 12px; padding: 4px 0; border-bottom: 1px solid rgba(255,255,255,0.06); }
    .popup-stat .lbl { color: #9ca3af; }
    .popup-stat .val { font-weight: 700; color: #fff; font-family: 'JetBrains Mono', monospace; }
    .popup-stat .val.gold { color: #f59e0b; }
    .popup-stat .val.green { color: #10b981; }
  </style>
</head>
<body>
  <div class="header-bar">
    <div>
      <div class="brand-title">☀️ CHENNAI SOLAR POTENTIAL MAPPER</div>
      <div class="brand-sub">OpenStreetMap Footprints • NASA POWER • TANGEDCO & PM Surya Ghar</div>
    </div>
    <div class="stat-pill">
      <span class="lbl">Buildings</span>
      <span class="val">__TOTAL_BUILDINGS__</span>
    </div>
    <div class="stat-pill">
      <span class="lbl">PV Capacity</span>
      <span class="val">__TOTAL_MW__ MWp</span>
    </div>
    <div class="stat-pill">
      <span class="lbl">Annual Output</span>
      <span class="val">__TOTAL_GWH__ GWh</span>
    </div>
    <div class="stat-pill">
      <span class="lbl">CO₂ Offset</span>
      <span class="val">__TOTAL_CO2__ t/yr</span>
    </div>
  </div>

  <div id="map"></div>

  <div class="legend">
    <div class="legend-title">Solar Potential Index</div>
    <div class="legend-row"><span class="swatch" style="background:#10b981"></span> High Potential (75-100)</div>
    <div class="legend-row"><span class="swatch" style="background:#84cc16"></span> Good Potential (50-74)</div>
    <div class="legend-row"><span class="swatch" style="background:#f59e0b"></span> Moderate Potential (30-49)</div>
    <div class="legend-row"><span class="swatch" style="background:#ef4444"></span> Low Potential (&lt; 30)</div>
  </div>

  <script>
    const map = L.map('map').setView([13.0065, 80.2570], 16);

    const satellite = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
      attribution: 'Esri, Maxar, Earthstar Geographics',
      maxZoom: 19
    }).addTo(map);

    const street = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; OpenStreetMap'
    });

    L.control.layers({
      "🛰️ High-Res Satellite": satellite,
      "🗺️ Street Map": street
    }, null, { position: 'topright' }).addTo(map);

    const data = __GEOJSON_DATA__;

    L.geoJSON(data, {
      style: (feature) => ({
        fillColor: feature.properties.fill_color || '#10b981',
        weight: 1.5,
        opacity: 0.9,
        color: '#ffffff',
        fillOpacity: 0.78
      }),
      onEachFeature: (feature, layer) => {
        const p = feature.properties;
        const fin = p.financials || {};
        layer.bindPopup(`
          <div class="popup-content">
            <h4>${p.address || 'Chennai Rooftop'}</h4>
            <p>${p.neighborhood || 'Chennai'} • ${p.building_type || 'Residential'} • Solar Score: <b style="color:#10b981">${p.solar_score || p.score_0_100}/100</b></p>
            <div class="popup-stat"><span class="lbl">Roof Area:</span><span class="val">${p.roof_area_m2} m² (${p.usable_area_m2} m² usable)</span></div>
            <div class="popup-stat"><span class="lbl">System Sizing:</span><span class="val gold">${p.recommended_system_size_kw} kWp (${p.recommended_panel_count} panels)</span></div>
            <div class="popup-stat"><span class="lbl">Annual Generation:</span><span class="val">${(p.annual_kwh_potential || 0).toLocaleString()} kWh/yr</span></div>
            <div class="popup-stat"><span class="lbl">PM Surya Ghar Subsidy:</span><span class="val green">₹ ${(fin.subsidy_inr || 0).toLocaleString()}</span></div>
            <div class="popup-stat"><span class="lbl">Net CAPEX:</span><span class="val">₹ ${(fin.net_capex_inr || 0).toLocaleString()}</span></div>
            <div class="popup-stat"><span class="lbl">Annual Bill Savings:</span><span class="val green">₹ ${(fin.annual_savings_inr || 0).toLocaleString()}/yr</span></div>
            <div class="popup-stat"><span class="lbl">Payback Period:</span><span class="val gold">${fin.payback_years || 4.5} Years</span></div>
            <div class="popup-stat"><span class="lbl">CO₂ Reduction:</span><span class="val">${fin.co2_tons_annual || 0} tons/yr</span></div>
          </div>
        `, { maxWidth: 320 });
      }
    }).addTo(map);
  </script>
</body>
</html>
"""

html_rendered = (
    html_template
    .replace("__TOTAL_BUILDINGS__", str(total_buildings))
    .replace("__TOTAL_MW__", f"{total_kw / 1000.0:.1f}")
    .replace("__TOTAL_GWH__", f"{total_kwh / 1000000.0:.2f}")
    .replace("__TOTAL_CO2__", f"{total_co2:,.0f}")
    .replace("__GEOJSON_DATA__", geojson_str)
)

with open(output_path, "w", encoding="utf-8") as f:
    f.write(html_rendered)

print(f"Standalone interactive solar map saved to {output_path}")
