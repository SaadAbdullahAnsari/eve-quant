from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
from eve_quant.esi import (
    THE_FORGE_REGION_ID,
    ESIClient,
)

RAW_DIR = Path("data/raw")


def clean_market_orders(
    df: pd.DataFrame,
) -> pd.DataFrame:
    """
    Basic cleaning of ESI market orders.

    Removes:
    - invalid prices
    - zero volume orders
    - non-market junk
    """

    df = df.copy()

    # Remove impossible values
    df = df[df["price"] > 0]

    df = df[df["volume_remain"] > 0]

    # Keep only sensible order ranges
    valid_ranges = {
        "station",
        "solarsystem",
        "region",
        "1",
        "2",
        "3",
        "4",
        "5",
        "6",
        "7",
        "8",
        "9",
        "10",
        "20",
        "30",
    }

    df = df[df["range"].isin(valid_ranges)]

    return df


def save_snapshot(
    df: pd.DataFrame,
) -> Path:

    RAW_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    timestamp = datetime.now(UTC)

    filename = RAW_DIR / (
        "the_forge_orders_" f"{timestamp.strftime('%Y%m%dT%H%M%SZ')}" ".parquet"
    )

    df.to_parquet(
        filename,
        index=False,
    )

    return filename


def main() -> None:

    print("Downloading The Forge market orders...")

    client = ESIClient()

    orders = client.get_region_orders(
        region_id=THE_FORGE_REGION_ID,
        order_type="all",
    )

    print(f"Downloaded {len(orders):,} regional orders.")

    df = pd.DataFrame(orders)

    print(f"Before cleaning: {len(df):,}")

    df = clean_market_orders(df)

    print(f"After cleaning: {len(df):,}")

    filename = save_snapshot(df)

    print()

    print("Saved snapshot:")

    print(filename)

    print()

    print("Unique market items:")

    print(df["type_id"].nunique())


if __name__ == "__main__":
    main()
