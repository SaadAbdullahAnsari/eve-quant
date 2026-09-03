from __future__ import annotations

import os

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

from pathlib import Path

import pandas as pd

DATA_PATH = Path("data/processed/research_dataset.parquet")

OUTPUT_PATH = Path("data/analysis/clean_return_characteristics.parquet")


# Minimum requirements
MIN_HISTORY_DAYS = 60
MIN_DAILY_VOLUME = 1000
MIN_ORDER_COUNT = 10


def main():

    print("Loading dataset...")

    df = pd.read_parquet(DATA_PATH)

    print()

    print("Initial rows:")

    print(len(df))

    # -----------------------------
    # Market quality filters
    # -----------------------------

    filtered = df[
        (df["volume"] >= MIN_DAILY_VOLUME) & (df["order_count"] >= MIN_ORDER_COUNT)
    ].copy()

    print()

    print("After liquidity filters:")

    print(len(filtered))

    # -----------------------------
    # Remove extreme return artefacts
    # -----------------------------

    filtered["clean_return_1d"] = filtered["return_1d"].clip(
        lower=-0.5,
        upper=0.5,
    )

    # -----------------------------
    # Aggregate market behaviour
    # -----------------------------

    stats = filtered.groupby("type_id").agg(
        observations=(
            "clean_return_1d",
            "count",
        ),
        avg_daily_return=(
            "clean_return_1d",
            "mean",
        ),
        daily_volatility=(
            "clean_return_1d",
            "std",
        ),
        avg_abs_return=(
            "clean_return_1d",
            lambda x: x.abs().mean(),
        ),
        positive_days=(
            "clean_return_1d",
            lambda x: (x > 0).mean(),
        ),
        avg_daily_volume=(
            "isk_volume",
            "mean",
        ),
    )

    # Require enough observations

    stats = stats[stats["observations"] >= MIN_HISTORY_DAYS]

    print()

    print("Most volatile realistic markets:")

    print(
        stats.sort_values(
            "daily_volatility",
            ascending=False,
        ).head(30)
    )

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    stats.to_parquet(OUTPUT_PATH)

    print()

    print("Saved:")

    print(OUTPUT_PATH)


if __name__ == "__main__":
    main()
