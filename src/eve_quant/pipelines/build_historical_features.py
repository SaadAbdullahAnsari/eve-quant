import pandas as pd

from eve_quant.historical_features import (
    build_historical_features,
    save_features,
)


def main():

    history = pd.read_parquet("data/raw/market_history_20260831T194207Z.parquet")

    features = build_historical_features(
        history,
        minimum_history_days=60,
    )

    print(f"Generated {len(features):,} rows")

    print()

    print(features.head(10))

    print()

    print("Items remaining:")

    print(features["type_id"].nunique())

    save_features(features)

    print()

    print("Saved:")

    print("data/processed/historical_features.parquet")


if __name__ == "__main__":
    main()
