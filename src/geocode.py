# src/geocode.py
import requests
import time

class GeoCoder:
    def __init__(self):
        self.cache = {}  # simple in-memory cache { "lat|lon": "address" }

    def reverse_geocode(self, lat: float, lon: float) -> str:
        key = f"{lat:.6f}|{lon:.6f}"

        # Return cached value if exists
        if key in self.cache:
            return self.cache[key]

        url = (
            f"https://nominatim.openstreetmap.org/reverse?"
            f"lat={lat}&lon={lon}&format=json&addressdetails=1"
        )
        try:
            response = requests.get(
                url,
                headers={"User-Agent": "Mozilla/5.0"}
            )
            data = response.json()
            address = data.get("display_name", "Unknown location")

        except Exception:
            address = "Unknown location"

        # Cache result
        self.cache[key] = address

        # Respect Nominatim rules: 1 request / second
        time.sleep(1)

        return address


# Global geocoder instance
geocoder = GeoCoder()