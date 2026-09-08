"""
test_solar.py

Automated test suite for Rooftop Solar Potential Mapper (Chennai):
- Verifies UTM Zone 44N metric projection & orientation calculation
- Verifies Tamil Nadu TANGEDCO tariffs and PM Surya Ghar subsidy rules
- Verifies satellite tile fetching from Esri World Imagery & U-Net inference
- Verifies home address prediction with progressive geocoding & monthly bill customization
- Verifies Flask REST API endpoints
"""
import os
import sys
import unittest
from shapely.geometry import Polygon

root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
scripts_dir = os.path.join(root_dir, "scripts")
seg_dir = os.path.join(root_dir, "segmentation")
for p in [root_dir, scripts_dir, seg_dir]:
    if p not in sys.path:
        sys.path.insert(0, p)

from address_to_solar import (
    calculate_building_geometry,
    calculate_financials,
    estimate_solar_potential,
    score_to_color,
    geocode_address
)
from infer import (
    fetch_satellite_tile,
    get_building_polygon_from_satellite_tile,
    deg2num,
    num2deg
)
import app


class TestSolarCalculator(unittest.TestCase):

    def test_geometry_and_utm44n(self):
        lat, lon = 13.0065, 80.2570
        d_lat = 15.0 / 110574.0
        d_lon = 10.0 / 108450.0

        coords = [
            [lon, lat],
            [lon + d_lon, lat],
            [lon + d_lon, lat + d_lat],
            [lon, lat + d_lat],
            [lon, lat]
        ]
        poly = Polygon(coords)
        geom = calculate_building_geometry(poly)

        self.assertAlmostEqual(geom["roof_area_m2"], 150.0, delta=10.0)
        self.assertGreater(geom["orientation_factor"], 0.90)
        self.assertIn("utm_poly", geom)

    def test_financials_pm_surya_ghar_subsidy(self):
        fin1 = calculate_financials(system_kw=1.0, annual_kwh=1500)
        self.assertEqual(fin1["subsidy_inr"], 30000.0)
        self.assertEqual(fin1["gross_capex_inr"], 55000.0)
        self.assertEqual(fin1["net_capex_inr"], 25000.0)
        self.assertGreater(fin1["annual_savings_inr"], 0)
        self.assertLess(fin1["payback_years"], 4.0)

        fin2 = calculate_financials(system_kw=2.0, annual_kwh=3000)
        self.assertEqual(fin2["subsidy_inr"], 60000.0)
        self.assertEqual(fin2["gross_capex_inr"], 110000.0)
        self.assertEqual(fin2["net_capex_inr"], 50000.0)

        fin3 = calculate_financials(system_kw=5.0, annual_kwh=7500)
        self.assertEqual(fin3["subsidy_inr"], 78000.0)
        self.assertEqual(fin3["gross_capex_inr"], 275000.0)
        self.assertEqual(fin3["net_capex_inr"], 197000.0)
        self.assertGreater(fin3["trees_equivalent"], 100)

    def test_color_coding(self):
        self.assertEqual(score_to_color(85), "#10b981")
        self.assertEqual(score_to_color(60), "#84cc16")
        self.assertEqual(score_to_color(40), "#f59e0b")
        self.assertEqual(score_to_color(20), "#ef4444")

    def test_home_address_prediction_and_bill_offset(self):
        # Test full address prediction with door number stripping and bill offset
        addr = "12 Kasturba Nagar, Adyar, Chennai"
        res = estimate_solar_potential(addr, monthly_bill=3500)
        self.assertEqual(res["address"], addr)
        self.assertIn("lat", res)
        self.assertIn("lon", res)
        self.assertGreater(res["usable_area_m2"], 20)
        self.assertGreater(res["recommended_system_size_kw"], 0.5)
        self.assertIn("financials", res)
        self.assertIn("bill_offset_pct", res["financials"])
        self.assertGreater(res["financials"]["bill_offset_pct"], 50.0)

    def test_vadapalani_street_accuracy_and_subsidies(self):
        # Test street-level precision for complex Tamil temple street addresses
        addr = "57/27, Aadhi moola perumal kovil street, vadapalani, chennai"
        res = estimate_solar_potential(addr, monthly_bill=3500)
        self.assertAlmostEqual(res["lat"], 13.05248, delta=0.001)
        self.assertAlmostEqual(res["lon"], 80.21486, delta=0.001)
        self.assertIn("Aadhi Moola Perumal", res["matched_landmark"])
        self.assertGreater(res["recommended_system_size_kw"], 2.5)
        self.assertLess(res["recommended_system_size_kw"], 10.0)
        self.assertEqual(res["financials"]["subsidy_inr"], 78000.0)
        self.assertEqual(res["financials"]["bill_offset_pct"], 100.0)


class TestSatelliteSegmentation(unittest.TestCase):

    def test_tile_math(self):
        lat, lon, zoom = 13.0065, 80.2570, 18
        x, y = deg2num(lat, lon, zoom)
        self.assertIsInstance(x, int)
        self.assertIsInstance(y, int)
        re_lat, re_lon = num2deg(x, y, zoom)
        self.assertAlmostEqual(lat, re_lat, delta=0.01)
        self.assertAlmostEqual(lon, re_lon, delta=0.01)

    def test_fetch_and_segment_tile(self):
        lat, lon = 13.0065, 80.2570
        img, bbox = fetch_satellite_tile(lat, lon, zoom=18)
        self.assertEqual(img.shape, (256, 256, 3))

        poly_res = get_building_polygon_from_satellite_tile(lat, lon, zoom=18)
        self.assertEqual(poly_res["type"], "Polygon")
        self.assertGreater(len(poly_res["coordinates"][0]), 3)


class TestFlaskAPI(unittest.TestCase):

    def setUp(self):
        self.client = app.app.test_client()

    def test_neighborhoods_endpoint(self):
        res = self.client.get("/api/neighborhoods")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("adyar", data)
        self.assertIn("t_nagar", data)

    def test_buildings_endpoint(self):
        res = self.client.get("/api/buildings?neighborhood=adyar")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["type"], "FeatureCollection")
        self.assertGreater(len(data["features"]), 0)
        first_props = data["features"][0]["properties"]
        self.assertIn("annual_kwh_potential", first_props)
        self.assertIn("financials", first_props)

    def test_estimate_home_address_endpoint(self):
        res = self.client.get("/api/estimate?address=12+Kasturba+Nagar,+Adyar,+Chennai&monthly_bill=3500")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertIn("solar_score", data)
        self.assertEqual(data["address"], "12 Kasturba Nagar, Adyar, Chennai")
        self.assertIn("bill_offset_pct", data["financials"])

    def test_stats_endpoint(self):
        res = self.client.get("/api/stats")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertGreater(data["total_buildings"], 0)


if __name__ == "__main__":
    unittest.main()
