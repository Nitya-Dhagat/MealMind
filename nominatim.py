"""Nearby restaurants + geocoding via Nominatim (OpenStreetMap). No API key needed.

Usage policy (https://operations.osmfoundation.org/policies/nominatim/):
  - max 1 request/second, identify the app with a real User-Agent, cache results.
The public server is for light use. For production traffic, self-host Nominatim or use a provider.
"""
import math
import os
import threading
import time

import requests

BASE = os.environ.get("NOMINATIM_URL", "https://nominatim.openstreetmap.org")
CACHE_TTL = 3600
_cache = {}
_lock = threading.Lock()
_last_call = [0.0]

# OSM cuisine tag / amenity -> cuisines used in data/menu.csv
CUISINE_MAP = {
    "indian": ["north indian", "south indian", "hyderabadi", "street food", "coastal"],
    "north_indian": ["north indian"], "punjabi": ["north indian"], "mughlai": ["north indian"],
    "south_indian": ["south indian"], "udupi": ["south indian"], "dosa": ["south indian"],
    "hyderabadi": ["hyderabadi"], "biryani": ["hyderabadi"],
    "chinese": ["chinese"], "indo-chinese": ["chinese"], "asian": ["chinese", "japanese"],
    "italian": ["italian"], "pizza": ["italian"], "pasta": ["italian"],
    "burger": ["american"], "american": ["american"], "sandwich": ["american"],
    "japanese": ["japanese"], "sushi": ["japanese"], "ramen": ["japanese"],
    "seafood": ["coastal"], "fish": ["coastal"], "coastal": ["coastal"],
    "vegetarian": ["healthy", "north indian", "south indian"], "vegan": ["healthy"],
    "salad": ["healthy"], "healthy": ["healthy"],
    "street_food": ["street food"], "chaat": ["street food"],
    "coffee_shop": ["beverage"], "tea": ["beverage"], "juice": ["beverage"],
    "ice_cream": ["dessert"], "dessert": ["dessert"], "cake": ["dessert"], "sweets": ["dessert"],
}
TYPE_FALLBACK = {
    "fast_food": ["american", "street food"],
    "cafe": ["beverage", "dessert"],
    "ice_cream": ["dessert"],
    "restaurant": ["north indian", "south indian", "chinese", "italian"],  # generic guess
}


def _get(path, params):
    """Rate-limited, cached GET. Returns parsed JSON or None."""
    key = (path, tuple(sorted(params.items())))
    now = time.time()
    hit = _cache.get(key)
    if hit and now - hit[0] < CACHE_TTL:
        return hit[1]
    ua = os.environ.get("NOMINATIM_USER_AGENT", "MealMind/0.1 (set NOMINATIM_USER_AGENT)")
    with _lock:
        wait = 1.05 - (time.time() - _last_call[0])
        if wait > 0:
            time.sleep(wait)
        try:
            r = requests.get(f"{BASE}{path}", params=params, headers={"User-Agent": ua}, timeout=8)
            r.raise_for_status()
            data = r.json()
        except Exception:
            data = None
        _last_call[0] = time.time()
    if data is not None:
        _cache[key] = (now, data)
    return data


def geocode(text):
    """Free-text place ('Koramangala, Bangalore') -> (lat, lon) or None."""
    if not text or not text.strip():
        return None
    data = _get("/search", {"q": text.strip(), "format": "jsonv2", "limit": 1})
    if data:
        return float(data[0]["lat"]), float(data[0]["lon"])
    return None


def _viewbox(lat, lon, radius_km):
    dlat = radius_km / 111.0
    dlon = radius_km / (111.0 * max(math.cos(math.radians(lat)), 0.01))
    # Nominatim order: left(lon_min), top(lat_max), right(lon_max), bottom(lat_min)
    return f"{lon - dlon:.5f},{lat + dlat:.5f},{lon + dlon:.5f},{lat - dlat:.5f}"


def _cuisines_for(item):
    tags = (item.get("extratags") or {}).get("cuisine", "")
    out = set()
    for t in tags.replace(",", ";").split(";"):
        out.update(CUISINE_MAP.get(t.strip().lower().replace(" ", "_"), []))
    if not out:
        out.update(TYPE_FALLBACK.get(item.get("type", ""), []))
    return sorted(out)


def nearby_restaurants(lat, lon, radius_km=3, limit=40):
    """Restaurants, fast-food and cafes within radius_km. [] on any failure."""
    if lat is None or lon is None:
        return []
    lat, lon = round(float(lat), 3), round(float(lon), 3)  # coarse rounding improves cache hits
    seen, out = set(), []
    for term in ("restaurant", "fast food", "cafe"):
        data = _get("/search", {
            "q": term, "format": "jsonv2", "viewbox": _viewbox(lat, lon, radius_km),
            "bounded": 1, "limit": limit, "addressdetails": 0, "extratags": 1,
        })
        for it in data or []:
            pid = it.get("place_id")
            name = it.get("name") or it.get("display_name", "").split(",")[0]
            if pid in seen or not name:
                continue
            seen.add(pid)
            out.append({
                "name": name,
                "type": it.get("type", ""),
                "rating": None,  # OSM has no ratings
                "address": it.get("display_name", ""),
                "cuisines": _cuisines_for(it),
            })
    return out


def available_cuisines(places):
    s = set()
    for p in places:
        s.update(p["cuisines"])
    return s
