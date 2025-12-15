# src/app.py
import os
from pathlib import Path
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd

from src.recommender import Recommender

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Project root (two levels up from this file)
PROJECT_ROOT = Path(__file__).resolve().parents[1]
CSV_PATH = PROJECT_ROOT / "data" / "zomato_bangalore.csv"

if not CSV_PATH.exists():
    raise FileNotFoundError(f"Place your CSV at: {CSV_PATH}")

logger.info("Loading dataset (this may take a few seconds)...")
df = pd.read_csv(CSV_PATH)
logger.info("Initializing recommender...")
rec = Recommender(df)
logger.info("Recommender ready.")

@app.route("/recommend", methods=["GET"])
def recommend_api():
    lat = request.args.get("lat", type=float)
    lon = request.args.get("lon", type=float)
    time_str = request.args.get("time", default="12:00", type=str)
    k = request.args.get("k", default=5, type=int)

    if lat is None or lon is None:
        return jsonify({"error": "Provide lat and lon query params (e.g. ?lat=12.97&lon=77.59)"}), 400

    try:
        results = rec.recommend(lat, lon, time_str, k=k)
        return jsonify(results)
    except Exception as e:
        logger.exception("Error in recommendation")
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    # Run so that local preview tools (localhost, 127.0.0.1) can access it.
    app.run(host="0.0.0.0", port=5000, debug=True)
