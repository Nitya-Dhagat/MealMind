# MealMind

Content-based food recommender with a Flask API and a vanilla JS UI.

## Run locally

```bash
pip install -r requirements.txt
cp .env.example .env     # fill in the key and your contact email (real .env is gitignored)
python app.py            # http://localhost:5000
```

## Config

- `OPENWEATHER_API_KEY`: weather-aware ranking. New keys can take up to a couple of hours to activate.
- `NOMINATIM_USER_AGENT`: required by the Nominatim usage policy. Use your app name and a real contact, e.g. `MealMind/0.1 (you@example.com)`. No API key needed.

## Nearby restaurants (Nominatim / OpenStreetMap)

`nominatim.py` does two things:
- **Geocoding**: a typed location ("Koramangala, Bangalore") becomes lat/lon through `/search`. The UI also supports device geolocation.
- **Nearby places**: `/search` with `q=restaurant|fast food|cafe`, a `viewbox` of about 3 km around the point, `bounded=1` and `extratags=1`. OSM's `cuisine` tag (e.g. `south_indian;dosa`) is mapped to menu cuisines in `CUISINE_MAP`. Places with no cuisine tag fall back to a guess from their type.

Recommendations are restricted to cuisines served nearby. If nothing matches, the full menu is used.

Policy built in: 1 request/second (locked and throttled), cached for 1 hour, coordinates rounded to ~100 m for cache hits, custom User-Agent. The public server is for light use only. Heavy traffic needs a self-hosted Nominatim (`NOMINATIM_URL` env var points the app at it). OSM has no ratings or menus, so dishes still come from `data/menu.csv`.

## API

- `GET /api/options`
- `POST /api/recommend`: `cuisines`, `diet` (any, vegetarian, vegan, nonveg), `gluten_free`, `max_price`, `spice` (0-3), `weather` (rain, cold, hot, clear), `lat`/`lon` or `location` (text), `hour`, `liked_ids`, `k`. Returns `results` and `nearby`.

## Scoring

TF-IDF over cuisine, diet, dish name and meal type. Cosine similarity to chosen cuisines and liked dishes is the base score, re-ranked by time-of-day, weather, spice distance and rating. Diet, gluten-free, price and nearby cuisines are hard filters.

## Free hosting

**Render (config included: `render.yaml`)**
1. Push this repo to GitHub (`.env` is gitignored).
2. Render dashboard > New > Blueprint > pick the repo.
3. Set `OPENWEATHER_API_KEY` and `NOMINATIM_USER_AGENT` when prompted.
4. Free web services sleep when idle, so the first request after a pause is slow.

Other options: PythonAnywhere, Hugging Face Spaces (Docker), Fly.io. Check current free-tier terms and outbound-network rules before choosing.

`Procfile` is kept for Heroku-style hosts.
