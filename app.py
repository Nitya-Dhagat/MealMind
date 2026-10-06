"""MealMind Flask API. Run: python app.py"""
import os
from datetime import datetime

import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS

load_dotenv()

from nominatim import available_cuisines, geocode, nearby_restaurants  # noqa: E402
from recommender import Recommender  # noqa: E402

app = Flask(__name__, static_folder="static", static_url_path="")
CORS(app)
rec = Recommender()

OWM_KEY = os.environ.get("OPENWEATHER_API_KEY")


def fetch_weather(lat, lon):
    """Return a coarse weather tag ('rain', 'cold', 'hot', 'clear') or None."""
    if not (OWM_KEY and lat is not None and lon is not None):
        return None
    try:
        r = requests.get(
            "https://api.openweathermap.org/data/2.5/weather",
            params={"lat": lat, "lon": lon, "units": "metric", "appid": OWM_KEY},
            timeout=4,
        )
        r.raise_for_status()
        d = r.json()
        main = d["weather"][0]["main"].lower()
        temp = d["main"]["temp"]
        if main in ("rain", "drizzle", "thunderstorm"):
            return "rain"
        if temp <= 15:
            return "cold"
        if temp >= 32:
            return "hot"
        return "clear"
    except Exception:
        return None


@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.get("/api/health")
def health():
    return jsonify(status="ok", items=len(rec.df))


@app.get("/api/options")
def options():
    return jsonify(cuisines=rec.cuisines(),
                   diets=["any", "vegetarian", "vegan", "nonveg"])


@app.post("/api/recommend")
def recommend():
    p = request.get_json(silent=True) or {}
    hour = p.get("hour")
    if hour is None:
        hour = datetime.now().hour
    lat, lon = p.get("lat"), p.get("lon")
    if (lat is None or lon is None) and p.get("location"):
        coords = geocode(p["location"])  # typed place name -> coordinates
        if coords:
            lat, lon = coords
    weather = p.get("weather") or fetch_weather(lat, lon)
    diet = p.get("diet")
    if diet == "any":
        diet = None
    places = nearby_restaurants(lat, lon)
    results = rec.recommend(
        allowed_cuisines=available_cuisines(places) or None,
        cuisines=p.get("cuisines", []),
        diet=diet,
        gluten_free=bool(p.get("gluten_free")),
        max_price=p.get("max_price"),
        spice=p.get("spice"),
        hour=int(hour),
        weather=weather,
        liked_ids=p.get("liked_ids", []),
        exclude_ids=p.get("exclude_ids", []),
        k=int(p.get("k", 8)),
    )
    return jsonify(weather=weather, hour=int(hour), results=results,
                   nearby=[{"name": x["name"], "rating": x["rating"], "address": x["address"]}
                           for x in places[:10]])


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
