from __future__ import annotations

import os

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

from pathlib import Path

import pandas as pd

FEATURE_PATH = Path("data/processed/research_dataset.parquet")

MARKET_FEATURE_PATH = Path("data/processed/market_features.parquet")

SDE_PATH = Path("data/sde/types.parquet")

OUTPUT_PATH = Path("data/analysis/market_characteristics.parquet")


def main():

    print("Loading data...")

    history = pd.read_parquet(FEATURE_PATH)

    market = pd.read_parquet(MARKET_FEATURE_PATH)

    sde = pd.read_parquet(SDE_PATH)

    # -----------------------------
    # Historical behaviour
    # -----------------------------

    historical = history.groupby("type_id").agg(
        avg_daily_isk_volume=(
            "isk_volume",
            "mean",
        ),
        daily_return_volatility=(
            "return_1d",
            "std",
        ),
        avg_return_30d=(
            "return_30d",
            "mean",
        ),
        avg_volume_ratio=(
            "volume_ratio",
            "mean",
        ),
    )

    # -----------------------------
    # Current market structure
    # -----------------------------

    structure = market[
        [
            "type_id",
            "total_orders",
            "total_volume",
            "spread_pct",
            "buy_concentration",
            "sell_concentration",
        ]
    ].set_index("type_id")

    # -----------------------------
    # Combine
    # -----------------------------

    result = historical.join(
        structure,
        how="inner",
    ).reset_index()

    result = result.merge(
        sde[
            [
                "type_id",
                "name",
            ]
        ],
        on="type_id",
        how="left",
    )

    # -----------------------------
    # Tradability score
    # -----------------------------
    #
    # NOT a trading signal.
    # Just ranks markets.
    #

    result["tradability_score"] = (
        result["avg_daily_isk_volume"].rank(pct=True)
        + result["total_orders"].rank(pct=True)
        - result["spread_pct"].rank(pct=True)
        - result["sell_concentration"].rank(pct=True)
        - result["daily_return_volatility"].rank(pct=True)
    )

    result = result.sort_values(
        "tradability_score",
        ascending=False,
    )

    print()

    print("Top 30 tradable markets:")

    print(
        result[
            [
                "name",
                "avg_daily_isk_volume",
                "daily_return_volatility",
                "spread_pct",
                "total_orders",
                "sell_concentration",
                "tradability_score",
            ]
        ].head(30)
    )

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    result.to_parquet(
        OUTPUT_PATH,
        index=False,
    )

    print()

    print("Saved:")

    print(OUTPUT_PATH)


if __name__ == "__main__":
    main()
