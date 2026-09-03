from __future__ import annotations

import os

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

from pathlib import Path

import pandas as pd

HISTORY_PATH = Path("data/analysis/clean_return_characteristics.parquet")

FEATURE_PATH = Path("data/processed/market_features.parquet")

SDE_PATH = Path("data/sde/types_with_categories.parquet")

OUTPUT_PATH = Path("data/analysis/category_characteristics.parquet")


def main():

    print("Loading datasets...")

    returns = pd.read_parquet(HISTORY_PATH)

    market = pd.read_parquet(FEATURE_PATH)

    sde = pd.read_parquet(SDE_PATH)

    # -----------------------------
    # Combine item information
    # -----------------------------

    df = (
        returns.reset_index()
        .merge(
            market,
            on="type_id",
            how="inner",
        )
        .merge(
            sde[
                [
                    "type_id",
                    "category_name",
                    "group_name",
                    "name",
                ]
            ],
            on="type_id",
            how="left",
        )
    )

    # -----------------------------
    # Aggregate by category
    # -----------------------------

    category = (
        df.groupby("category_name")
        .agg(
            number_of_items=(
                "type_id",
                "nunique",
            ),
            avg_daily_isk_volume=(
                "avg_daily_volume",
                "mean",
            ),
            avg_volatility=(
                "daily_volatility",
                "mean",
            ),
            avg_return=(
                "avg_daily_return",
                "mean",
            ),
            avg_abs_return=(
                "avg_abs_return",
                "mean",
            ),
            avg_spread=(
                "spread_pct",
                "mean",
            ),
            avg_orders=(
                "total_orders",
                "mean",
            ),
            avg_concentration=(
                "sell_concentration",
                "mean",
            ),
        )
        .sort_values(
            "avg_daily_isk_volume",
            ascending=False,
        )
    )

    print()

    print("Category characteristics:")

    print(category.head(30))

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    category.to_parquet(OUTPUT_PATH)

    print()

    print("Saved:")

    print(OUTPUT_PATH)


if __name__ == "__main__":
    main()
