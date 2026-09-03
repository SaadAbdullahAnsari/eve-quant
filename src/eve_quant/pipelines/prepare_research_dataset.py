from __future__ import annotations

from pathlib import Path

import pandas as pd

INPUT = Path("data/processed/historical_features.parquet")

OUTPUT = Path("data/processed/research_dataset.parquet")


REQUIRED_FEATURES = [
    "return_1d",
    "return_7d",
    "return_30d",
    "volatility_7d",
    "volatility_30d",
    "price_deviation_30d",
    "isk_volume_ratio",
]


def main():

    df = pd.read_parquet(INPUT)

    print(f"Initial rows: {len(df):,}")

    df = df.dropna(subset=REQUIRED_FEATURES)

    print(f"After removing incomplete rows: {len(df):,}")

    print()

    print("Items remaining:")

    print(df["type_id"].nunique())

    df.to_parquet(
        OUTPUT,
        index=False,
    )

    print()

    print("Saved:")

    print(OUTPUT)


if __name__ == "__main__":
    main()
