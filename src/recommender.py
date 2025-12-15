# src/recommender.py

from typing import List, Dict
import pandas as pd
import numpy as np
from sklearn.neighbors import BallTree
from src.utils import parse_time_to_slot
from src.geocode import geocoder


class Recommender:
    def __init__(self, df: pd.DataFrame, distance_weight: float = 0.7, time_weight: float = 0.3):
        """
        Weighted hybrid recommendation engine (distance + time-slot popularity).
        This version DOES NOT require Restaurant_Name in the CSV; names are obtained via reverse geocoding.
        """

        # Validate weights
        assert 0.0 <= distance_weight <= 1.0
        assert 0.0 <= time_weight <= 1.0
        assert abs(distance_weight + time_weight - 1.0) < 1e-6

        self.distance_weight = distance_weight
        self.time_weight = time_weight

        df = df.copy()

        # ============================
        # Detect usable time column
        # ============================
        time_col = None
        for col in ["Time_Orderd", "Time_Order_picked"]:
            if col in df.columns:
                time_col = col
                break

        if time_col is None:
            raise ValueError("Expected a time column ('Time_Orderd' or 'Time_Order_picked'), but none found.")

        # ============================
        # Clean dataset
        # ============================
        df = df.dropna(subset=["Restaurant_latitude", "Restaurant_longitude", time_col])
        df = df[(df["Restaurant_latitude"] != 0) & (df["Restaurant_longitude"] != 0)]

        # ============================
        # Time slot classification
        # ============================
        df["_time_slot"] = df[time_col].astype(str).apply(parse_time_to_slot)
        df = df[df["_time_slot"] != "unknown"]

        # ============================
        # Composite restaurant key
        # ============================
        df["_rest_lat"] = df["Restaurant_latitude"].round(6)
        df["_rest_lon"] = df["Restaurant_longitude"].round(6)
        df["_rest_key"] = df["_rest_lat"].astype(str) + "|" + df["_rest_lon"].astype(str)

        # If dataset contains a name column, use it; otherwise leave None and rely on geocoder later
        name_col = None
        for possible in ["Restaurant_Name", "Restaurant", "Restaurant_Name_clean"]:
            if possible in df.columns:
                name_col = possible
                break
        if name_col is not None:
            df["_maybe_name"] = df[name_col].astype(str)
        else:
            df["_maybe_name"] = None

        # ============================
        # Aggregate by restaurant
        # ============================
        rest_table = df.groupby("_rest_key").agg(
            rest_lat=("Restaurant_latitude", "first"),
            rest_lon=("Restaurant_longitude", "first"),
            rest_name=("_maybe_name", "first"),
            orders_total=("ID", "count")
        ).reset_index()

        # Time slot frequency table
        slot_counts = df.groupby(["_rest_key", "_time_slot"]).size().unstack(fill_value=0)
        for s in ["breakfast", "lunch", "evening", "night"]:
            if s not in slot_counts.columns:
                slot_counts[s] = 0
        slot_counts = slot_counts.reset_index()

        rest_table = rest_table.merge(slot_counts, on="_rest_key", how="left")

        # Normalize time popularity
        time_cols = ["breakfast", "lunch", "evening", "night"]
        rest_table["time_sum"] = rest_table[time_cols].sum(axis=1)
        for s in time_cols:
            rest_table[s + "_freq"] = rest_table.apply(
                lambda r: (r[s] / r["time_sum"]) if r["time_sum"] > 0 else 0.0,
                axis=1
            )

        self.rest_table = rest_table.reset_index(drop=True)

        # Build BallTree for fast geo search
        coords = np.radians(self.rest_table[["rest_lat", "rest_lon"]].values)
        if len(coords) == 0:
            raise ValueError("No restaurants found after preprocessing. Check dataset.")
        self.tree = BallTree(coords, metric="haversine")

    def recommend(self, user_lat: float, user_lon: float, time_str: str, k: int = 5) -> List[Dict]:
        """
        Returns top-K restaurant recommendations.
        Each output dict contains:
            - name: short name (either dataset name or geocoded POI first token)
            - full_address: full display_name from Nominatim
            - latitude, longitude, distance_km, score
        """

        slot = parse_time_to_slot(time_str)
        if slot == "unknown":
            slot = None

        user_coord = np.radians([[user_lat, user_lon]])
        k_query = min(max(k * 3, k), len(self.rest_table))

        dist_rad, idx = self.tree.query(user_coord, k=k_query)
        dist_km = dist_rad[0] * 6371.0088
        idx = idx[0]

        candidates = self.rest_table.iloc[idx].copy().reset_index(drop=True)
        candidates["distance_km"] = dist_km

        maxd = candidates["distance_km"].max() if candidates["distance_km"].max() > 0 else 1.0
        candidates["dist_norm"] = candidates["distance_km"] / maxd

        if slot is not None:
            freq_col = slot + "_freq"
            candidates["time_freq"] = candidates.get(freq_col, 0.0)
        else:
            candidates["time_freq"] = 0.0

        candidates["score"] = (
            self.distance_weight * candidates["dist_norm"]
            + self.time_weight * (1 - candidates["time_freq"])
        )

        candidates = candidates.sort_values("score").head(k)

        results = []
        for _, r in candidates.iterrows():
            lat = float(r["rest_lat"])
            lon = float(r["rest_lon"])

            # If a dataset name exists, use it; otherwise use geocoded name.
            dataset_name = r.get("rest_name", None)
            full_address = None
            geocoded_name = None
            try:
                full_address = geocoder.reverse_geocode(lat, lon)
                # pick the first segment as a short name if needed
                geocoded_name = full_address.split(",")[0] if isinstance(full_address, str) else None
            except Exception:
                full_address = "Unknown location"
                geocoded_name = None

            short_name = dataset_name if (isinstance(dataset_name, str) and dataset_name.strip() and dataset_name != "None") else (geocoded_name or "Unknown")

            results.append({
                "name": short_name,
                "full_address": full_address or "Unknown location",
                "latitude": lat,
                "longitude": lon,
                "distance_km": float(r["distance_km"]),
                "score": float(r["score"]),
                "time_slot": slot if slot else "any",
                "time_freq": float(r.get("time_freq", 0.0))
            })

        return results
