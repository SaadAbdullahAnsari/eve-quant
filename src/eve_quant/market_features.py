from __future__ import annotations

from pathlib import Path

import pandas as pd

JITA_SYSTEM_ID = 30000142
JITA_LOCATION_ID = 60003760

PERIMETER_SYSTEM_ID = 30000144


PROCESSED_DIR = Path("data/processed")


def build_market_features(
    orders: pd.DataFrame,
) -> pd.DataFrame:
    """
    Build trading features from raw market orders.

    Market definition:
    Jita ecosystem:
        - Jita IV-4
        - Perimeter

    Designed for a trader who is willing
    to travel one jump but not haul around
    the galaxy.
    """

    df = orders.copy()

    # -------------------------------------------------
    # Define ecosystem
    # -------------------------------------------------

    ecosystem = df[
        df["system_id"].isin(
            [
                JITA_SYSTEM_ID,
                PERIMETER_SYSTEM_ID,
            ]
        )
    ]

    if ecosystem.empty:
        raise ValueError("No Jita ecosystem orders found.")

    # -------------------------------------------------
    # Split buy/sell sides
    # -------------------------------------------------

    buys = ecosystem[ecosystem["is_buy_order"]]

    sells = ecosystem[~ecosystem["is_buy_order"]]

    # -------------------------------------------------
    # Price features
    # -------------------------------------------------

    features = ecosystem.groupby("type_id").agg(
        total_orders=(
            "order_id",
            "count",
        ),
        total_volume=(
            "volume_remain",
            "sum",
        ),
    )

    best_bid = buys.groupby("type_id")["price"].max().rename("ecosystem_best_bid")

    best_ask = sells.groupby("type_id")["price"].min().rename("ecosystem_best_ask")

    features = features.join(best_bid)

    features = features.join(best_ask)

    # -------------------------------------------------
    # Order counts
    # -------------------------------------------------

    features["buy_order_count"] = buys.groupby("type_id")["order_id"].count()

    features["sell_order_count"] = sells.groupby("type_id")["order_id"].count()

    # -------------------------------------------------
    # Volume imbalance
    # -------------------------------------------------

    features["buy_volume"] = buys.groupby("type_id")["volume_remain"].sum()

    features["sell_volume"] = sells.groupby("type_id")["volume_remain"].sum()

    features = features.fillna(0)

    # -------------------------------------------------
    # Spread
    # -------------------------------------------------

    features["mid"] = (
        features["ecosystem_best_bid"] + features["ecosystem_best_ask"]
    ) / 2

    features["spread_pct"] = (
        (features["ecosystem_best_ask"] - features["ecosystem_best_bid"])
        / features["mid"]
        * 100
    )

    # -------------------------------------------------
    # Concentration
    # -------------------------------------------------

    largest_buy = (
        buys.groupby("type_id")["volume_remain"].max().rename("largest_buy_order")
    )

    largest_sell = (
        sells.groupby("type_id")["volume_remain"].max().rename("largest_sell_order")
    )

    features = features.join(largest_buy)

    features = features.join(largest_sell)

    features = features.fillna(0)

    features["buy_concentration"] = (
        features["largest_buy_order"] / features["buy_volume"]
    )

    features["sell_concentration"] = (
        features["largest_sell_order"] / features["sell_volume"]
    )

    features = features.replace(
        [float("inf")],
        0,
    )

    return features.reset_index()


def save_market_features(
    features: pd.DataFrame,
    path: Path | None = None,
) -> None:

    if path is None:
        path = PROCESSED_DIR / "market_features.parquet"

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    features.to_parquet(
        path,
        index=False,
    )
