from pathlib import Path

import pandas as pd

from eve_quant.market_features import (
    build_market_features,
    save_market_features,
)

RAW_DIR = Path("data/raw")


def latest_snapshot():

    files = sorted(RAW_DIR.glob("the_forge_orders_*.parquet"))

    if not files:
        raise FileNotFoundError("No market snapshot found.")

    return files[-1]


def main():

    snapshot = latest_snapshot()

    print("Loading:")
    print(snapshot)

    orders = pd.read_parquet(snapshot)

    features = build_market_features(orders)

    print()

    print(f"Generated features for {len(features)} items")

    print()

    print(
        features.sort_values(
            "total_volume",
            ascending=False,
        ).head(20)
    )

    save_market_features(features)

    print()

    print("Saved:")
    print("data/processed/market_features.parquet")


if __name__ == "__main__":
    main()
