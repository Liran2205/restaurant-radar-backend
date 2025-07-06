import os, io, uuid, datetime, pathlib, requests, pandas as pd
from fastapi import FastAPI, Query
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles

GOOGLE = os.getenv("GOOGLE_API_KEY")
YELP   = os.getenv("YELP_API_KEY")

app = FastAPI()

# ---------- serve exported Excel files ----------
EXPORT_DIR = pathlib.Path("/tmp/exports")
EXPORT_DIR.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=EXPORT_DIR), name="static")

# ---------- helper functions ----------
def google_places(text):
    if not GOOGLE:
        return []
    url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    r = requests.get(url, params={"query": text, "key": GOOGLE})
    return r.json().get("results", [])

def yelp_search(text, loc="Florida"):
    if not YELP:
        return []
    url = "https://api.yelp.com/v3/businesses/search"
    hdr = {"Authorization": f"Bearer {YELP}"}
    r = requests.get(url, headers=hdr,
                     params={"term": text, "location": loc, "limit": 10})
    return r.json().get("businesses", [])

def merge_hits(g_hits, y_hits):
    merged, seen = [], set()
    for g in g_hits:
        name = g["name"]
        if name in seen:
            continue
        merged.append({
            "name": name,
            "city": g.get("formatted_address", "")[:40],
            "rating_google": g.get("rating"),
            "reviews_google": g.get("user_ratings_total")
        })
        seen.add(name)
    for y in y_hits:
        name = y["name"]
        if name in seen:
            continue
        merged.append({
            "name": name,
            "city": ", ".join(y["location"].get("display_address", [])),
            "rating_yelp": y.get("rating"),
            "reviews_yelp": y.get("review_count")
        })
        seen.add(name)
    return merged[:15]

# ---------- API routes ----------
@app.get("/search_restaurants")
def search_restaurants(occasion: str = Query(...)):
    queries = {
        "GuysNight":  "late night restaurant bar Florida",
        "DateCouple": "romantic fine dining Florida",
        "DateGroup":  "share plates upscale Florida",
        "WorkLunch":  "healthy bowl salad Florida",
        "Family":     "family friendly restaurant Florida"
    }
    text = queries.get(occasion, "best restaurant Florida")
    return merge_hits(google_places(text), yelp_search(text))

@app.post("/export_list")
def export_list():
    # demo DataFrame — replace with real favourites/visited later
    df = pd.DataFrame([{
        "name":  "Delilah Miami",
        "rating": 4.6,
        "date":   datetime.date.today()
    }])

    # save to /tmp/exports
    fname = f"favourites_{uuid.uuid4().hex}.xlsx"
    fpath = EXPORT_DIR / fname
    df.to_excel(fpath, index=False)

    # Render injects hostname into env; fall back to hard-coded domain
    host = os.getenv("RENDER_EXTERNAL_HOSTNAME") or "restaurant-radar-backend.onrender.com"
    download_url = f"https://{host}/static/{fname}"
    return {"download_url": download_url}

@app.get("/")
def root():
    return {"status": "ok"}

