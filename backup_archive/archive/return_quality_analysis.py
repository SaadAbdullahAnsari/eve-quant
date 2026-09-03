from __future__ import annotations

import os

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

from pathlib import Path

import pandas as pd

DATA_PATH = Path("data/processed/research_dataset.parquet")

SDE_PATH = Path("data/sde/types_with_categories.parquet")

OUTPUT_PATH = Path("data/analysis/return_quality_analysis.parquet")


def main():

    print("Loading data...")

    df = pd.read_parquet(DATA_PATH)

    sde = pd.read_parquet(SDE_PATH)

    df = df.merge(
        sde[
            [
                "type_id",
                "name",
                "category_name",
            ]
        ],
        on="type_id",
        how="left",
    )

    results = []

    for type_id, group in df.groupby("type_id"):

        group = group.sort_values("date")

        returns = group["return_1d"].clip(
            -0.5,
            0.5,
        )

        # Large price moves
        large_moves = group[returns.abs() > 0.05]

        results.append(
            {
                "type_id": type_id,
                "name": group["name"].iloc[0],
                "category": group["category_name"].iloc[0],
                "observations": len(group),
                "lag_1_autocorrelation": returns.corr(returns.shift(1)),
                "avg_abs_return": returns.abs().mean(),
                "large_move_frequency": (returns.abs() > 0.05).mean(),
                "avg_volume": group["isk_volume"].mean(),
                "large_move_volume": (
                    large_moves["isk_volume"].mean() if len(large_moves) > 0 else 0
                ),
                "avg_order_count": group["order_count"].mean(),
                "large_move_order_count": (
                    large_moves["order_count"].mean() if len(large_moves) > 0 else 0
                ),
            }
        )

    result = pd.DataFrame(results)

    print()

    print("Strong mean reversion with meaningful volume:")

    print(
        result[result.large_move_volume > result.avg_volume * 0.5]
        .sort_values("lag_1_autocorrelation")
        .head(20)
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
