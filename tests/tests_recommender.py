# tests/test_recommender.py
import pandas as pd
from src.recommender import Recommender

def make_sample_df():
    data = {
        'ID': [1,2,3,4],
        'Restaurant_latitude': [12.9716, 12.9750, 12.90, 12.9710],
        'Restaurant_longitude': [77.5946, 77.5910, 77.55, 77.6000],
        'Time_Orderd': ['08:30', '12:15', '20:45', '19:00']
    }
    return pd.DataFrame(data)

def test_recommend_basic():
    df = make_sample_df()
    rec = Recommender(df)
    out = rec.recommend(12.9716, 77.5946, '08:45', k=2)
    assert isinstance(out, list)
    assert len(out) == 2
    assert all('distance_km' in r and 'score' in r for r in out)
