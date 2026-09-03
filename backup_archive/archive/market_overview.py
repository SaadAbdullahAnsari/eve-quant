from __future__ import annotations

import os

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

DATA_PATH = Path("data/processed/research_dataset.parquet")

SDE_PATH = Path("data/sde/types.parquet")

OUTPUT_DIR = Path("data/analysis")


def main():

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    df = pd.read_parquet(DATA_PATH)

    print("Dataset shape:")

    print(df.shape)

    print()

    print("Number of markets:")

    print(df["type_id"].nunique())

    print()

    print("Columns:")

    print(df.columns.tolist())

    print()

    print("Sample:")

    print(df.head())

    # --------------------------
    # Liquidity ranking
    # --------------------------

    liquidity = (
        df.groupby("type_id")["isk_volume"]
        .mean()
        .sort_values(ascending=False)
        .reset_index()
    )

    items = pd.read_parquet(SDE_PATH)

    liquidity = liquidity.merge(
        items[
            [
                "type_id",
                "name",
            ]
        ],
        on="type_id",
        how="left",
    )

    print()

    print("Top 20 markets by " "average daily ISK volume:")

    print(liquidity.head(20))

    # --------------------------
    # Save liquidity plot
    # --------------------------

    top = liquidity.head(20)

    plt.figure(
        figsize=(
            12,
            6,
        )
    )

    plt.bar(
        range(len(top)),
        top["isk_volume"],
    )

    plt.xticks(
        range(len(top)),
        top["name"],
        rotation=90,
    )

    plt.ylabel("Average daily ISK volume")

    plt.title("Top 20 EVE markets by liquidity")

    plt.tight_layout()

    output = OUTPUT_DIR / "top_liquidity.png"

    plt.savefig(
        output,
        dpi=150,
    )

    plt.close()

    print()

    print("Saved plot:")

    print(output)


if __name__ == "__main__":
    main()
