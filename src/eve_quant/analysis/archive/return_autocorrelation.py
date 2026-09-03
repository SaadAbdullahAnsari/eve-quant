from __future__ import annotations

import os

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

from pathlib import Path

import pandas as pd

DATA_PATH = Path("data/processed/research_dataset.parquet")

SDE_PATH = Path("data/sde/types_with_categories.parquet")

OUTPUT_PATH = Path("data/analysis/return_autocorrelation.parquet")


def calculate_autocorrelation(
    series: pd.Series,
    lag: int,
) -> float:

    return series.corr(series.shift(lag))


def main():

    print("Loading data...")

    df = pd.read_parquet(DATA_PATH)

    sde = pd.read_parquet(SDE_PATH)

    df = df.merge(
        sde[
            [
                "type_id",
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

        results.append(
            {
                "type_id": type_id,
                "category": group["category_name"].iloc[0],
                "lag_1": calculate_autocorrelation(
                    returns,
                    1,
                ),
                "lag_7": calculate_autocorrelation(
                    returns,
                    7,
                ),
                "lag_30": calculate_autocorrelation(
                    returns,
                    30,
                ),
                "observations": len(returns),
            }
        )

    result = pd.DataFrame(results)

    print()

    print("Strongest positive lag-1 momentum:")

    print(
        result.sort_values(
            "lag_1",
            ascending=False,
        ).head(20)
    )

    print()

    print("Strongest negative lag-1 mean reversion:")

    print(
        result.sort_values(
            "lag_1",
            ascending=True,
        ).head(20)
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
