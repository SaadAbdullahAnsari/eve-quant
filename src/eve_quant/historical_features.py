from __future__ import annotations

from pathlib import Path

import pandas as pd

PROCESSED_DIR = Path("data/processed")


def build_historical_features(
    history: pd.DataFrame,
    minimum_history_days: int = 60,
) -> pd.DataFrame:
    """
    Create time-series features from
    daily EVE market history.

    Only keeps items with enough historical
    observations to support rolling features.
    """

    df = history.copy()

    df["date"] = pd.to_datetime(df["date"])

    df = df.sort_values(
        [
            "type_id",
            "date",
        ]
    )

    # ---------------------------------
    # Remove markets with insufficient data
    # ---------------------------------

    history_counts = df.groupby("type_id").size()

    valid_items = history_counts[history_counts >= minimum_history_days].index

    df = df[df["type_id"].isin(valid_items)].copy()

    grouped = df.groupby(
        "type_id",
        group_keys=False,
    )

    # ---------------------------------
    # Returns
    # ---------------------------------

    df["return_1d"] = grouped["average"].pct_change(1)

    df["return_7d"] = grouped["average"].pct_change(7)

    df["return_30d"] = grouped["average"].pct_change(30)

    # ---------------------------------
    # Volatility
    # ---------------------------------

    df["volatility_7d"] = (
        grouped["return_1d"]
        .rolling(7)
        .std()
        .reset_index(
            level=0,
            drop=True,
        )
    )

    df["volatility_30d"] = (
        grouped["return_1d"]
        .rolling(30)
        .std()
        .reset_index(
            level=0,
            drop=True,
        )
    )

    # ---------------------------------
    # Moving averages
    # ---------------------------------

    df["ma_30"] = (
        grouped["average"]
        .rolling(30)
        .mean()
        .reset_index(
            level=0,
            drop=True,
        )
    )

    df["price_deviation_30d"] = (df["average"] - df["ma_30"]) / df["ma_30"]

    # ---------------------------------
    # Volume features
    # ---------------------------------

    df["isk_volume"] = df["volume"] * df["average"]

    df["isk_volume_ma_7"] = (
        grouped["isk_volume"]
        .rolling(7)
        .mean()
        .reset_index(
            level=0,
            drop=True,
        )
    )

    df["isk_volume_ma_30"] = (
        grouped["isk_volume"]
        .rolling(30)
        .mean()
        .reset_index(
            level=0,
            drop=True,
        )
    )

    df["isk_volume_ratio"] = df["isk_volume"] / df["isk_volume_ma_30"]

    # ---------------------------------
    # Raw volume behaviour
    # ---------------------------------

    df["volume_ma_30"] = (
        grouped["volume"]
        .rolling(30)
        .mean()
        .reset_index(
            level=0,
            drop=True,
        )
    )

    df["volume_ratio"] = df["volume"] / df["volume_ma_30"]

    return df


def save_features(
    df: pd.DataFrame,
    path: Path | None = None,
):

    if path is None:
        path = PROCESSED_DIR / "historical_features.parquet"

    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    df.to_parquet(
        path,
        index=False,
    )
