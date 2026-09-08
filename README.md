# ☀️ Rooftop Solar Potential Mapper (Chennai)

A high-resolution geospatial intelligence system for estimating rooftop photovoltaic (PV) solar potential, sizing recommendations, and financial payback across Chennai, Tamil Nadu.

The system combines satellite/aerial imagery, building footprint polygons, NASA POWER solar irradiance climatology, Tamil Nadu TANGEDCO tiered tariffs, and India's **PM Surya Ghar: Muft Bijli Yojana** subsidies. It also integrates a deep learning **U-Net segmentation** pipeline for extracting building boundaries directly from high-resolution satellite tiles.

---

## 🚀 Key Features

- **Interactive GIS Map Dashboard**:
  - Full-screen Leaflet visualization with **Esri High-Resolution World Imagery** (0.3–0.5m/px aerial view), **Dark GIS Canvas**, and **OpenStreetMap Street basemap**.
  - 300+ rooftop polygons mapped across 6 key Chennai hubs: **Adyar**, **Besant Nagar**, **T. Nagar**, **Anna Nagar**, **Mylapore**, and **OMR / Thoraipakkam**.
  - Color-coded solar choropleth:
    - 🟢 **High Potential** (Score 75–100)
    - 🟡 **Good Potential** (Score 50–74)
    - 🟠 **Moderate Potential** (Score 30–49)
    - 🔴 **Low Potential** (&lt; 30)

- **Photovoltaic & Physical Modeling**:
  - **Metric UTM Zone 44N Projection (`EPSG:32644`)**: Accurate true-to-life surface area in square meters.
  - **Usable Area & Shading Buffer**: Automatically accounts for overhead water tanks (RCC/Sintex), staircase mumties, and parapet shadow margins (~72% net usable area).
  - **Roof Orientation & Azimuth**: Extracted using the minimum rotated bounding box.
  - **NASA POWER Solar Irradiance**: Daily and monthly climatology (annual Chennai average ~5.38 kWh/m²/day).

- **Tamil Nadu TANGEDCO & PM Surya Ghar Financial Engine**:
  - Turnkey solar installation CAPEX (~₹55,000 / kWp benchmark).
  - Central Financial Assistance (CFA) via PM Surya Ghar:
    - 1 kW: ₹30,000
    - 2 kW: ₹60,000
    - 3 kW+: ₹78,000 max
  - Net CapEx, annual electricity bill savings, and simple payback period (typically 3.5 to 5.5 years in Chennai).
  - 25-year lifetime return factoring in 0.5% panel degradation and 3% tariff inflation.
  - Environmental benefits: Annual CO₂ avoided (metric tons) & equivalent trees planted.

- **Deep Learning Satellite Segmentation (U-Net)**:
  - Built-in PyTorch U-Net semantic segmentation network with skip connections.
  - Fetches 256×256 real-world satellite tiles on the fly via Esri World Imagery.
  - Converts predicted rooftop pixel masks into georeferenced WGS84 GeoJSON polygons with OpenCV contour detection.
  - Visual inspector modal to compare raw satellite imagery against segmented rooftop masks.

- **Standalone Offline Map**:
  - `output/solar_map.html` is a self-contained HTML file viewable directly in any browser without needing a web server.

---

## 🛠️ Quick Start

### 1. Install Dependencies
```bash
pip install flask requests shapely pyproj torch torchvision opencv-python-headless
```

### 2. Start the Interactive Web Dashboard
```bash
python scripts/app.py
```
Open **[http://localhost:5000](http://localhost:5000)** in your browser.

### 3. Generate or Regenerate Neighborhood Data
```bash
python scripts/generate_chennai_data.py
python scripts/build_map.py
```
This updates `data/scored_buildings.geojson` and creates `output/solar_map.html`.

### 4. Run Automated Test Suite
```bash
python tests/test_solar.py
```

---

## 📁 Repository Structure

```
rooftop-solar-estimator/
├── data/
│   ├── buildings.geojson           # OSM building footprints
│   ├── scored_buildings.geojson    # Scored GeoJSON with solar & financial attributes
│   ├── city_stats.json             # Aggregate Chennai capacity & carbon metrics
│   └── neighborhoods/              # Neighborhood-specific GeoJSON files
├── output/
│   └── solar_map.html              # Standalone interactive Leaflet HTML map
├── scripts/
│   ├── app.py                      # Flask REST API & GIS dashboard server
│   ├── address_to_solar.py         # Core calculation engine & Nominatim/Overpass/NASA pipeline
│   ├── generate_chennai_data.py    # Multi-neighborhood synthetic & OSM dataset generator
│   ├── build_map.py                # Standalone HTML map builder
│   ├── fetch_buildings.py          # Overpass API live fetcher
│   ├── fetch_irradiance.py         # NASA POWER API client
│   ├── score_rooftops.py           # Batch GeoJSON scoring utility
│   └── static/
│       └── index.html              # Modern dark-mode GIS web interface (Leaflet + Chart.js)
├── segmentation/
│   ├── model.py                    # PyTorch U-Net architecture
│   ├── infer.py                    # Satellite tile fetching, segmentation & polygon extraction
│   ├── dataset.py                  # PyTorch image/mask dataset loader
│   └── train.py                    # Model training loop (Dice + BCE loss)
└── tests/
    └── test_solar.py               # Unit & integration test suite (9 automated tests)
```

---

## 📊 Methodology & Formulas

1. **Usable Area Calculation**:
   $$\text{Usable Area } (m^2) = \text{Roof Area } (m^2) \times 0.72$$
2. **Annual Solar Output**:
   $$\text{Annual Energy } (kWh) = \text{Usable Area} \times \text{Irradiance } (kWh/m^2/day) \times \eta_{\text{panel}} \times PR \times \text{Orientation Factor} \times 365$$
   - $\eta_{\text{panel}} = 0.21$ (21% mono-PERC efficiency)
   - $PR = 0.78$ (Performance ratio: wiring, inverter, dust, temperature losses)
3. **Financial Payback**:
   $$\text{Net CAPEX} = \text{System Size } (kWp) \times ₹55,000 - \text{PM Surya Ghar Subsidy}$$
   $$\text{Payback Period } (years) = \frac{\text{Net CAPEX}}{\text{Annual TANGEDCO Bill Savings}}$$
4. **Carbon Abatement**:
   $$\text{CO}_2 \text{ Avoided } (t/yr) = \frac{\text{Annual Energy } (kWh) \times 0.82 \text{ kg CO}_2/kWh}{1000}$$
