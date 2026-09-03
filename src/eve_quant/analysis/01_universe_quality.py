import os
from pathlib import Path

import numpy as np
import pandas as pd

HUB_KEY = os.environ.get("EVE_QUANT_HUB", "jita").casefold()
RAW = max(Path("data/raw").glob(f"{HUB_KEY}_orders_*.parquet"))


OUTPUT = "data/analysis/" "universe_quality.parquet"


def normalise(x):

    if x.max() == x.min():
        return x * 0

    return (x - x.min()) / (x.max() - x.min())


def main():

    print("Loading orders...")

    df = pd.read_parquet(RAW)

    print("Orders:", len(df))

    #
    # Aggregate by item
    #

    grouped = (
        df.groupby("type_id")
        .agg(
            observations=("order_id", "count"),
            avg_price=("price", "mean"),
            total_volume=("volume_remain", "sum"),
            buy_orders=("is_buy_order", "sum"),
        )
        .reset_index()
    )

    grouped["sell_orders"] = grouped["observations"] - grouped["buy_orders"]

    #
    # Liquidity score
    #

    grouped["liquidity_score"] = np.log1p(grouped["total_volume"]) * np.log1p(
        grouped["observations"]
    )

    grouped["tradability_score"] = normalise(grouped["liquidity_score"]) * 100

    grouped = grouped.sort_values("tradability_score", ascending=False)

    print(grouped.head(20))

    Path("data/analysis").mkdir(exist_ok=True)

    grouped.to_parquet(OUTPUT, index=False)

    print("Saved:", OUTPUT)


if __name__ == "__main__":
    main()
