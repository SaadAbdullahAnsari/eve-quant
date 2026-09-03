from __future__ import annotations

import os

os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

DATA_PATH = Path("data/processed/research_dataset.parquet")

SDE_PATH = Path("data/sde/types_with_categories.parquet")

OUTPUT_DIR = Path("data/analysis/candidate_plots")


# Candidates from autocorrelation analysis
CANDIDATES = [
    62454,  # Compressed Bitumens
    62522,  # Compressed Scordite III-Grade
    2317,  # Oxides
    20414,  # Datacore - Quantum Physics
    16639,  # Scandium
    219,  # Thorium Charge S
    1830,  # Nova Auto-Targeting Cruise Missile I
]


def plot_market(
    df: pd.DataFrame,
    item_name: str,
    type_id: int,
):

    df = df.sort_values("date")

    fig, axes = plt.subplots(
        3,
        1,
        figsize=(12, 10),
        sharex=True,
    )

    # Price
    axes[0].plot(
        df["date"],
        df["average"],
    )

    axes[0].plot(
        df["date"],
        df["ma_30"],
    )

    axes[0].set_title(f"{item_name} price")

    axes[0].set_ylabel("ISK")

    # Deviation
    axes[1].plot(
        df["date"],
        df["price_deviation_30d"],
    )

    axes[1].axhline(0)

    axes[1].set_title("30 day price deviation")

    # Volume
    axes[2].bar(
        df["date"],
        df["isk_volume"],
    )

    axes[2].set_title("Daily ISK volume")

    axes[2].set_ylabel("ISK")

    plt.tight_layout()

    filename = OUTPUT_DIR / f"{type_id}_{item_name.replace(' ', '_')}.png"

    plt.savefig(
        filename,
        dpi=150,
    )

    plt.close()

    print(
        "Saved:",
        filename,
    )


def main():

    print("Loading data...")

    df = pd.read_parquet(DATA_PATH)

    sde = pd.read_parquet(SDE_PATH)

    df = df.merge(
        sde[
            [
                "type_id",
                "name",
            ]
        ],
        on="type_id",
        how="left",
    )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    for type_id in CANDIDATES:

        market = df[df.type_id == type_id]

        if market.empty:
            print(
                "Missing:",
                type_id,
            )
            continue

        plot_market(
            market,
            market["name"].iloc[0],
            type_id,
        )


if __name__ == "__main__":
    main()
