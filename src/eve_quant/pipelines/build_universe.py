from __future__ import annotations

import pandas as pd
from eve_quant.universe import (
    build_universe,
    save_universe,
)


def main() -> None:

    features = pd.read_parquet("data/processed/market_features.parquet")

    items = pd.read_parquet("data/sde/types.parquet")

    universe = build_universe(
        features,
        items,
    )

    print(f"Research universe size: {len(universe)}")

    print()

    print(
        universe[
            [
                "name",
                "market_quality_score",
                "research_tier",
                "total_orders",
                "spread_pct",
                "buy_concentration",
                "sell_concentration",
            ]
        ].head(50)
    )

    print()

    print(universe["research_tier"].value_counts())

    save_universe(universe)

    print()

    print("Saved:")

    print("data/processed/research_universe.parquet")


if __name__ == "__main__":
    main()
