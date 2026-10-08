"""
fetch_mensa.py
Downloads meals from selected German canteens using the OpenMensa API
and saves them as a raw CSV file in data/raw/.

Run from the project folder:  python src/fetch_mensa.py
"""

import time
import requests
import pandas as pd

# ---------------- SETTINGS ----------------
BASE_URL = "https://openmensa.org/api/v2"

CITIES = ["Heidelberg", "Berlin", "Hamburg", "München", "Leipzig",
          "Würzburg", "Nürnberg", "Dresden", "Köln", "Freiburg im Breisgau",
          "Mannheim", "Chemnitz", "Straubing", "Passau", "Regensburg",
          "Düsseldorf", "Stuttgart", "Saarbrücken / Saarland", "Dortmund / Nordrhein-Westfalen", "Jena"]

MAX_CANTEENS_PER_CITY = 2 
START_DATE = "2024-10-01"
END_DATE = "2026-10-01"

TEST_MODE = False                 # True = tiny test run, False = full download
OUTPUT_FILE = "data/raw/meals_raw.csv"


# ---------------- FUNCTIONS ----------------
def get_all_canteens():
    """Download all canteens from every page and return them as a DataFrame."""
    all_canteens = []
    page = 1
    total_pages = 1              # placeholder, updated after the first request

    while page <= total_pages:
        r = requests.get(f"{BASE_URL}/canteens", params={"page": page})
        total_pages = int(r.headers["x-total-pages"])
        all_canteens.extend(r.json())
        page = page + 1

    return pd.DataFrame(all_canteens)


def select_canteens(df_canteens):
    """Keep only canteens in our chosen cities, max N per city."""
    selected = df_canteens[df_canteens["city"].isin(CITIES)]
    selected = selected.groupby("city").head(MAX_CANTEENS_PER_CITY)

    # Check: did every city match? (spelling problems show up here)
    for city in CITIES:
        count = (selected["city"] == city).sum()
        if count == 0:
            print(f"WARNING: no canteens found for '{city}'")

    return selected


def get_meals(canteen_id, date):
    """Get the meals for one canteen on one date. Returns [] if none."""
    r = requests.get(f"{BASE_URL}/canteens/{canteen_id}/days/{date}/meals")
    if r.status_code != 200:
        return []
    return r.json()


# ---------------- MAIN PROGRAM ----------------
def main():
    print("Downloading canteen list...")
    canteens = select_canteens(get_all_canteens())

    # One date per week (every Wednesday) between start and end
    dates = pd.date_range(START_DATE, END_DATE, freq="W-WED")

    if TEST_MODE:
        canteens = canteens.head(2)
        dates = dates[:3]

    print(f"{len(canteens)} canteens x {len(dates)} dates "
          f"= {len(canteens) * len(dates)} requests")

    rows = []
    for _, canteen in canteens.iterrows():
        for date in dates:
            date_str = date.strftime("%Y-%m-%d")
            meals = get_meals(canteen["id"], date_str)

            for meal in meals:
                meal["canteen_id"] = canteen["id"]
                meal["canteen_name"] = canteen["name"]
                meal["city"] = canteen["city"]
                meal["date"] = date_str
                rows.append(meal)

            print(f"{canteen['city']} | {date_str} | {len(meals)} meals")
            time.sleep(0.5)

    df = pd.json_normalize(rows)
    df.to_csv(OUTPUT_FILE, index=False)
    print(f"Saved {len(df)} meals to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()