"""Content-based recommender for MealMind (TF-IDF + cosine similarity, with context re-ranking)."""
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

DATA = Path(__file__).parent / "data" / "menu.csv"

SPICE_LABELS = {0: "mild", 1: "light", 2: "medium", 3: "hot"}


def time_to_meal(hour: int) -> str:
    if 5 <= hour < 11:
        return "breakfast"
    if 11 <= hour < 16:
        return "lunch"
    if 16 <= hour < 19:
        return "snack"
    return "dinner"


class Recommender:
    def __init__(self, path: Path = DATA):
        self.df = pd.read_csv(path)
        self.df["meal_types"] = self.df["meal_type"].str.split("|")
        self.df["doc"] = (
            self.df["cuisine"].str.replace(" ", "_") + " "
            + self.df["diet"] + " "
            + self.df["name"].str.lower() + " "
            + self.df["meal_type"].str.replace("|", " ")
        )
        self.vec = TfidfVectorizer()
        self.matrix = self.vec.fit_transform(self.df["doc"])

    def _profile_vector(self, cuisines, liked_ids):
        parts = [c.lower().replace(" ", "_") for c in cuisines]
        q = self.vec.transform([" ".join(parts)]).toarray() if parts else None
        if liked_ids:
            idx = self.df.index[self.df["id"].isin(liked_ids)].tolist()
            if idx:
                liked = np.asarray(self.matrix[idx].mean(axis=0))
                q = liked if q is None else (q * 0.6 + liked * 0.4)
        return q

    def recommend(self, cuisines=None, diet=None, gluten_free=False, max_price=None,
                  spice=None, hour=12, weather=None, liked_ids=None, exclude_ids=None, k=8,
                  allowed_cuisines=None):
        cuisines = cuisines or []
        liked_ids = liked_ids or []
        df = self.df.copy()

        # hard filters
        if diet == "vegetarian":
            df = df[df["diet"].isin(["veg", "vegan"])]
        elif diet == "vegan":
            df = df[df["diet"] == "vegan"]
        elif diet == "nonveg":
            df = df[df["diet"] == "nonveg"]
        if gluten_free:
            df = df[df["gluten_free"] == 1]
        if max_price:
            df = df[df["price"] <= max_price]
        if exclude_ids:
            df = df[~df["id"].isin(exclude_ids)]
        if allowed_cuisines:
            near = df[df["cuisine"].isin(allowed_cuisines)]
            if not near.empty:  # fall back to the full menu if nothing nearby matches
                df = near
        if df.empty:
            return []

        # content similarity
        q = self._profile_vector(cuisines, liked_ids)
        if q is None:
            sim = np.zeros(len(df))
        else:
            sim = cosine_similarity(q, self.matrix[df.index]).ravel()

        # context boosts
        meal = time_to_meal(hour)
        time_boost = df["meal_types"].apply(lambda m: 1.0 if meal in m else 0.0).to_numpy()
        weather_boost = np.zeros(len(df))
        if weather:
            w = weather.lower()
            if w in ("rain", "drizzle", "thunderstorm", "cold"):
                weather_boost = (df["temp"] == "hot").to_numpy() * 1.0
            elif w in ("hot", "clear_hot"):
                weather_boost = (df["temp"] == "cold").to_numpy() * 1.0
        spice_pen = np.zeros(len(df))
        if spice is not None:
            spice_pen = -np.abs(df["spice"].to_numpy() - spice) / 3.0
        quality = (df["rating"].to_numpy() - 3.5) / 1.5

        score = 0.45 * sim + 0.25 * time_boost + 0.12 * weather_boost + 0.08 * spice_pen + 0.10 * quality
        df = df.assign(score=score, w_boost=weather_boost)
        df = df.sort_values("score", ascending=False).head(k)

        out = []
        for _, r in df.iterrows():
            reasons = []
            if r["cuisine"] in [c.lower() for c in cuisines]:
                reasons.append(f"matches your {r['cuisine']} preference")
            if meal in r["meal_types"]:
                reasons.append(f"good for {meal}")
            if weather and r["w_boost"] > 0:
                reasons.append("suits the weather")
            if r["rating"] >= 4.4:
                reasons.append("highly rated")
            out.append({
                "id": int(r["id"]),
                "name": r["name"],
                "restaurant": r["restaurant"],
                "cuisine": r["cuisine"],
                "diet": r["diet"],
                "gluten_free": bool(r["gluten_free"]),
                "spice": SPICE_LABELS[int(r["spice"])],
                "price": int(r["price"]),
                "rating": float(r["rating"]),
                "delivery_min": int(r["delivery_min"]),
                "score": round(float(r["score"]), 3),
                "why": ", ".join(reasons) or "popular pick",
            })
        return out

    def cuisines(self):
        return sorted(self.df["cuisine"].unique().tolist())
