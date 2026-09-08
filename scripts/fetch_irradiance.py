"""
fetch_irradiance.py

Pulls average daily solar irradiance (kWh/m^2/day) from NASA POWER for a
given lat/lon point. Run on a machine with normal internet access.

NASA POWER docs: https://power.larc.nasa.gov/docs/services/api/
"""
import json
import requests

# Center point of our Adyar, Chennai bounding box
LAT, LON = 13.005, 80.255

POWER_URL = "https://power.larc.nasa.gov/api/temporal/climatology/point"

def fetch_irradiance(lat, lon):
    params = {
        "parameters": "ALLSKY_SFC_SW_DWN",  # all-sky surface shortwave downward irradiance
        "community": "RE",                  # renewable energy community
        "longitude": lon,
        "latitude": lat,
        "format": "JSON",
    }
    resp = requests.get(POWER_URL, params=params, timeout=60)
    resp.raise_for_status()
    return resp.json()


if __name__ == "__main__":
    print(f"Fetching irradiance for ({LAT}, {LON}) ...")
    data = fetch_irradiance(LAT, LON)
    monthly = data["properties"]["parameter"]["ALLSKY_SFC_SW_DWN"]
    annual_avg = monthly.get("ANN", sum(v for k, v in monthly.items() if k != "ANN") / 12)

    result = {"lat": LAT, "lon": LON, "monthly_kwh_m2_day": monthly, "annual_avg_kwh_m2_day": annual_avg}
    with open("../data/irradiance.json", "w") as f:
        json.dump(result, f, indent=2)
    print(f"Annual average irradiance: {annual_avg:.2f} kWh/m^2/day")
    print("Saved to data/irradiance.json")
