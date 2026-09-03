"""Rank only books that can plausibly support a passive Jita trade."""

from pathlib import Path

import numpy as np
import pandas as pd

ANALYSIS = Path("data/analysis")
OUTPUT = ANALYSIS / "candidate_markets.parquet"


def normalise(series: pd.Series) -> pd.Series:
    series = series.astype(float).replace([np.inf, -np.inf], np.nan).fillna(0)
    span = series.max() - series.min()
    return (
        pd.Series(1.0, index=series.index)
        if span == 0
        else (series - series.min()) / span
    )


def main() -> None:
    universe = pd.read_parquet(ANALYSIS / "universe_quality.parquet")
    structure = pd.read_parquet(ANALYSIS / "market_structure.parquet")
    signals = pd.read_parquet(ANALYSIS / "signal_features.parquet")
    alpha = pd.read_parquet(ANALYSIS / "alpha_constraints.parquet").iloc[0]

    latest_signals = (
        signals.sort_values("date").groupby("type_id", as_index=False).tail(1)
    )
    signal_columns = [
        "type_id",
        "signal_quality",
        "volatility",
        "isk_volume_ma_7",
        "isk_volume_ma_30",
        "volume_ma_30",
    ]
    df = structure.merge(
        universe[["type_id", "tradability_score"]], on="type_id", how="inner"
    )
    df = df.merge(latest_signals[signal_columns], on="type_id", how="left")
    df["signal_quality"] = df["signal_quality"].fillna(0)
    df["history_available"] = df["isk_volume_ma_7"].notna().astype(int)
    df["isk_volume_ma_7"] = df["isk_volume_ma_7"].fillna(0)
    df["volatility"] = df["volatility"].fillna(df["volatility"].median()).fillna(0)

    total_fee_rate = 2 * float(alpha["broker_fee"]) + float(alpha["sales_tax"])
    df["fee_adjusted_edge"] = df["gross_spread_pct"] - total_fee_rate
    min_depth = float(alpha["minimum_depth_isk"])
    eligible = (
        (df["fee_adjusted_edge"] >= float(alpha["minimum_net_return_pct"]))
        & (df["two_sided_depth_1pct_isk"] >= min_depth)
        & (df["buy_order_count"] >= 2)
        & (df["sell_order_count"] >= 2)
        & (df["buy_concentration"] <= 0.90)
        & (df["sell_concentration"] <= 0.90)
    )
    result = df.loc[eligible].copy()
    if result.empty:
        raise RuntimeError("No markets pass the passive-trading eligibility gates.")

    result["candidate_score"] = (
        0.30 * normalise(result["tradability_score"])
        + 0.25 * normalise(result["two_sided_depth_1pct_isk"])
        + 0.20 * normalise(result["fee_adjusted_edge"])
        + 0.15 * normalise(result["signal_quality"])
        + 0.10 * (1 - normalise(result["volatility"]))
    )
    result["risk_flags"] = ""
    columns = [
        "type_id",
        "venue",
        "snapshot_path",
        "best_bid",
        "best_ask",
        "midpoint",
        "gross_spread_pct",
        "fee_adjusted_edge",
        "two_sided_depth_1pct_isk",
        "buy_depth_units_1pct",
        "sell_depth_units_1pct",
        "top_buy_queue_units",
        "top_sell_queue_units",
        "tradability_score",
        "signal_quality",
        "volatility",
        "isk_volume_ma_7",
        "history_available",
        "candidate_score",
        "risk_flags",
    ]
    result = result[columns].sort_values("candidate_score", ascending=False)
    result.to_parquet(OUTPUT, index=False)
    print(f"Eligible candidates: {len(result)} of {len(df)} live books")
    print(result.head(20).to_string(index=False))
    print(f"Saved: {OUTPUT}")


if __name__ == "__main__":
    main()
