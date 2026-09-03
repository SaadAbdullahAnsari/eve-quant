from pathlib import Path

import pandas as pd

INPUT = "data/processed/" "research_dataset.parquet"

OUTPUT = "data/analysis/" "signal_features.parquet"


def safe_zscore(series):

    std = series.std()

    if std == 0 or pd.isna(std):

        return series * 0

    return (series - series.mean()) / std


def main():

    print("Loading historical dataset...")

    df = pd.read_parquet(INPUT)

    print("Rows:", len(df))

    df = df.sort_values(["type_id", "date"])

    # -------------------------
    # Momentum
    # -------------------------

    df["momentum_raw"] = 0.5 * df["return_7d"] + 0.5 * df["return_30d"]

    # -------------------------
    # Mean reversion
    # -------------------------

    df["mean_reversion_raw"] = -df["price_deviation_30d"]

    # -------------------------
    # Liquidity behaviour
    # -------------------------

    df["liquidity_trend"] = df["isk_volume_ratio"] * df["volume_ratio"]

    # -------------------------
    # Normalise signals
    # -------------------------

    df["momentum_score"] = safe_zscore(df["momentum_raw"])

    df["mean_reversion_score"] = safe_zscore(df["mean_reversion_raw"])

    df["liquidity_score"] = safe_zscore(df["liquidity_trend"])

    # -------------------------
    # Combined alpha signal
    # -------------------------

    df["signal_quality"] = (
        0.45 * df["momentum_score"]
        + 0.35 * df["mean_reversion_score"]
        + 0.20 * df["liquidity_score"]
    )

    output_cols = [
        "type_id",
        "date",
        "return_1d",
        "return_7d",
        "return_30d",
        "volatility_7d",
        "volatility_30d",
        "isk_volume_ma_7",
        "isk_volume_ma_30",
        "volume_ma_30",
        "momentum_score",
        "mean_reversion_score",
        "liquidity_trend",
        "signal_quality",
    ]

    result = df[output_cols].copy()

    # rename for downstream consistency

    result = result.rename(columns={"volatility_30d": "volatility"})

    Path("data/analysis").mkdir(exist_ok=True)

    result.to_parquet(OUTPUT, index=False)

    print(result.head(20).to_string(index=False))

    print("\nSaved:", OUTPUT)


if __name__ == "__main__":
    main()
