"""Rank passive-order candidates by expected value and explicit downside."""

from pathlib import Path

import numpy as np
import pandas as pd

ANALYSIS = Path("data/analysis")
OUTPUT = ANALYSIS / "risk_adjusted_results.parquet"


def normalise(series: pd.Series) -> pd.Series:
    series = series.astype(float).replace([np.inf, -np.inf], np.nan).fillna(0)
    span = series.max() - series.min()
    return (
        pd.Series(1.0, index=series.index)
        if span == 0
        else (series - series.min()) / span
    )


def main() -> None:
    df = pd.read_parquet(ANALYSIS / "execution_results.parquet")
    required = {
        "expected_return_pct",
        "immediate_liquidation_return_pct",
        "cycle_fill_probability",
        "inventory_risk",
        "candidate_score",
    }
    missing = required - set(df.columns)
    if missing:
        raise ValueError(
            f"Execution results use an incompatible schema: {sorted(missing)}"
        )

    # A high score requires positive expected return, fill opportunity, and a
    # comparatively survivable immediate liquidation.
    df["risk_adjusted_score"] = (
        0.40 * normalise(df["expected_return_pct"])
        + 0.25 * normalise(df["immediate_liquidation_return_pct"])
        + 0.20 * normalise(df["cycle_fill_probability"])
        + 0.10 * (1 - normalise(df["inventory_risk"]))
        + 0.05 * normalise(df["candidate_score"])
    )
    result = df.sort_values("risk_adjusted_score", ascending=False)
    result.to_parquet(OUTPUT, index=False)
    print(result.head(20).to_string(index=False))
    print(f"Saved: {OUTPUT}")


if __name__ == "__main__":
    main()
