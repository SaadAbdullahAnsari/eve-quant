from __future__ import annotations

from pathlib import Path

import pandas as pd

PROCESSED_DIR = Path("data/processed")


def minmax(
    series: pd.Series,
) -> pd.Series:
    """
    Scale values between 0 and 1.
    """

    minimum = series.min()
    maximum = series.max()

    if maximum == minimum:
        return pd.Series(
            1.0,
            index=series.index,
        )

    return (series - minimum) / (maximum - minimum)


def build_universe(
    features: pd.DataFrame,
    items: pd.DataFrame,
    minimum_orders: int = 20,
    minimum_volume: int = 100_000,
) -> pd.DataFrame:
    """
    Build ranked research universe.

    This does not identify profitable trades.

    It identifies markets worth researching.

    Factors:
    - liquidity
    - spread
    - order-book diversity
    - two-sided market activity
    """

    df = features.merge(
        items,
        on="type_id",
        how="inner",
    )

    # Require a functioning market

    df = df[(df["buy_order_count"] > 0) & (df["sell_order_count"] > 0)]

    df = df[df["total_orders"] >= minimum_orders]

    df = df[df["total_volume"] >= minimum_volume]

    df = df.dropna(
        subset=[
            "spread_pct",
            "buy_concentration",
            "sell_concentration",
        ]
    )

    # -----------------------------
    # Liquidity
    # -----------------------------

    volume_score = minmax(
        df["total_volume"].clip(upper=df["total_volume"].quantile(0.95))
    )

    order_score = minmax(
        df["total_orders"].clip(upper=df["total_orders"].quantile(0.95))
    )

    liquidity_score = 0.5 * volume_score + 0.5 * order_score

    # -----------------------------
    # Spread
    # Lower is better
    # -----------------------------

    spread_score = 1 - minmax(df["spread_pct"].clip(upper=50))

    # -----------------------------
    # Market concentration
    # Lower concentration is better
    # -----------------------------

    concentration = (df["buy_concentration"] + df["sell_concentration"]) / 2

    concentration_score = 1 - concentration

    # -----------------------------
    # Final quality score
    # -----------------------------

    df["market_quality_score"] = (
        0.45 * liquidity_score + 0.25 * spread_score + 0.30 * concentration_score
    )

    # -----------------------------
    # Research tiers
    # -----------------------------

    df = df.sort_values(
        "market_quality_score",
        ascending=False,
    )

    df["research_tier"] = "C"

    df.iloc[
        :200,
        df.columns.get_loc("research_tier"),
    ] = "A"

    df.iloc[
        200:1000,
        df.columns.get_loc("research_tier"),
    ] = "B"

    return df


def save_universe(
    universe: pd.DataFrame,
    path: Path | None = None,
) -> None:

    if path is None:
        path = PROCESSED_DIR / "research_universe.parquet"

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    universe.to_parquet(
        path,
        index=False,
    )
