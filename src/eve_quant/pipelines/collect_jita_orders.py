import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import requests

HUBS = {
    "jita": ("Jita 4-4", 10000002, 60003760),
    "amarr": ("Amarr VIII (Oris)", 10000043, 60008494),
    "dodixie": ("Dodixie IX", 10000032, 60011866),
    "rens": ("Rens VI", 10000030, 60004588),
}
HUB_KEY = os.environ.get("EVE_QUANT_HUB", "jita").casefold()
if HUB_KEY not in HUBS:
    raise ValueError(f"Unknown EVE_QUANT_HUB {HUB_KEY!r}; choose from {sorted(HUBS)}")
HUB_NAME, REGION_ID, HUB_STATION_ID = HUBS[HUB_KEY]

OUTPUT_DIR = Path("data/raw")


ESI_URL = f"https://esi.evetech.net/latest/" f"markets/{REGION_ID}/orders/"


def fetch_page(page: int):

    params = {
        "order_type": "all",
        "page": page,
    }

    # A daily advisor should fail visibly rather than stall for several minutes
    # when ESI is unavailable. The caller can reuse a known snapshot with
    # --no-refresh for diagnostics, but should not treat it as live advice.
    for attempt in range(3):

        try:

            response = requests.get(
                ESI_URL,
                params=params,
                timeout=12,
            )

            if response.status_code == 420:
                print("ESI rate limit. Waiting...")

                time.sleep(5)
                continue

            response.raise_for_status()

            total_pages = int(response.headers.get("X-Pages", 1))

            return (response.json(), total_pages)

        except requests.RequestException as e:

            print(f"Request failed attempt {attempt+1}/5:", e)

            time.sleep(2)

    raise RuntimeError(f"Failed downloading page {page}")


def collect_orders():
    """Download all regional pages with a small bounded worker pool."""
    print("Downloading page 1/?")
    first_page, total_pages = fetch_page(1)
    orders = list(first_page)
    if total_pages == 1:
        return orders
    print(f"Downloading remaining {total_pages - 1} pages with 4 workers")
    with ThreadPoolExecutor(max_workers=4) as executor:
        futures = {
            executor.submit(fetch_page, page): page
            for page in range(2, total_pages + 1)
        }
        for future in as_completed(futures):
            page = futures[future]
            batch, _ = future.result()
            orders.extend(batch)
            if page % 10 == 0 or page == total_pages:
                print(f"Downloaded page {page}/{total_pages}")
    return orders


def clean_orders(df):

    print(f"Filtering {HUB_NAME}...")

    df = df[df["location_id"] == HUB_STATION_ID].copy()

    print(f"{HUB_NAME} orders:", len(df))

    columns = [
        "duration",
        "is_buy_order",
        "issued",
        "location_id",
        "min_volume",
        "order_id",
        "price",
        "range",
        "system_id",
        "type_id",
        "volume_remain",
        "volume_total",
    ]

    df = df[columns]

    return df


def main():

    print(f"Collecting {HUB_NAME} regional market orders...")

    raw_orders = collect_orders()

    print("Regional orders:", len(raw_orders))

    df = pd.DataFrame(raw_orders)

    df = clean_orders(df)

    print("Unique items:", df["type_id"].nunique())

    OUTPUT_DIR.mkdir(exist_ok=True)

    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")

    output = OUTPUT_DIR / f"{HUB_KEY}_orders_{timestamp}.parquet"

    df.to_parquet(output, index=False)

    print("\nSaved:")

    print(output)


if __name__ == "__main__":
    main()
