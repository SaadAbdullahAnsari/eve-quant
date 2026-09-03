from __future__ import annotations

import os

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

from pathlib import Path

import pandas as pd

DATA_PATH = Path("data/processed/research_dataset.parquet")


OUTPUT = Path("data/analysis/return_characteristics.parquet")


def main():

    df = pd.read_parquet(DATA_PATH)

    stats = df.groupby("type_id").agg(
        avg_daily_return=(
            "return_1d",
            "mean",
        ),
        daily_volatility=(
            "return_1d",
            "std",
        ),
        avg_abs_return=(
            "return_1d",
            lambda x: x.abs().mean(),
        ),
        positive_days=(
            "return_1d",
            lambda x: (x > 0).mean(),
        ),
        avg_return_30d=(
            "return_30d",
            "mean",
        ),
    )

    print("Highest volatility markets:")

    print(
        stats.sort_values(
            "daily_volatility",
            ascending=False,
        ).head(20)
    )

    stats.to_parquet(OUTPUT)

    print()

    print("Saved:")

    print(OUTPUT)


if __name__ == "__main__":
    main()
