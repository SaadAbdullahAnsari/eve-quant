from __future__ import annotations

import pandas as pd
from eve_quant.history import (
    collect_history,
    save_history,
)


def main():

    universe = pd.read_parquet("data/processed/research_universe.parquet")

    # Start with Tier A only.
    # Avoid hammering ESI with 2000 requests.
    candidates = universe[universe["research_tier"] == "A"]["type_id"].tolist()

    print(f"Collecting history for " f"{len(candidates)} items")

    history = collect_history(candidates)

    print()

    print(f"Downloaded {len(history):,} rows")

    print(history.head())

    path = save_history(history)

    print()

    print("Saved:")

    print(path)


if __name__ == "__main__":
    main()
