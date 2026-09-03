from pathlib import Path

import numpy as np
import pandas as pd


STRUCTURE_PATH = (
    "data/analysis/market_structure.parquet"
)

HISTORY_PATH = (
    "data/processed/research_dataset.parquet"
)

OUTPUT_PATH = (
    "data/analysis/market_making_candidates.parquet"
)



def normalise(series):

    return (
        (series - series.min())
        /
        (
            series.max()
            -
            series.min()
            +
            1e-9
        )
    )



def main():

    print(
        "Loading datasets..."
    )


    structure = pd.read_parquet(
        STRUCTURE_PATH
    )


    history = pd.read_parquet(
        HISTORY_PATH
    )


    print(
        "Markets:",
        len(structure)
    )


    liquidity = (

        history
        .groupby("type_id")
        .agg(

            avg_isk_volume=(
                "isk_volume",
                "mean"
            ),

            avg_orders=(
                "order_count",
                "mean"
            ),

            volatility=(
                "volatility_30d",
                "mean"
            )

        )

        .reset_index()

    )


    df = structure.merge(
        liquidity,
        on="type_id",
        how="inner"
    )


    # -------------------------
    # Market making features
    # -------------------------


    df["spread_capture_pct"] = (

        (
            df["best_ask"]
            -
            df["best_bid"]
        )

        /

        df["best_bid"]

        *

        100

    )


    df["liquidity_score"] = (

        normalise(
            np.log1p(
                df["avg_isk_volume"]
            )
        )

        *

        normalise(
            df["avg_orders"]
        )

    )


    df["depth_score"] = normalise(

        np.log1p(
            df["two_sided_depth_1pct_isk"]
        )

    )


    df["competition_penalty"] = (

        1
        -
        (
            (
                df["buy_concentration"]
                +
                df["sell_concentration"]
            )
            /
            2
        )

    )


    df["spread_score"] = normalise(
        df["spread_capture_pct"]
    )


    df["market_making_score"] = (

        df["spread_score"]

        *
        df["liquidity_score"]

        *
        df["depth_score"]

        *
        df["competition_penalty"]

    )


    # remove unrealistic markets

    candidates = df[

        (df["avg_isk_volume"] > 1e8)

        &

        (df["avg_orders"] > 20)

        &

        (df["spread_capture_pct"] > 1)

    ]


    output_columns = [

        "type_id",
        "name",
        "group_name",
        "category_name",

        "avg_isk_volume",
        "avg_orders",
        "volatility",

        "spread_capture_pct",

        "two_sided_depth_1pct_isk",

        "buy_concentration",
        "sell_concentration",

        "market_making_score",

    ]


    candidates = (

        candidates[
            output_columns
        ]

        .sort_values(
            "market_making_score",
            ascending=False
        )

    )


    print()

    print(
        "TOP MARKET MAKING CANDIDATES"
    )


    print(
        candidates
        .head(50)
        .to_string(
            index=False
        )
    )


    Path(
        "data/analysis"
    ).mkdir(
        exist_ok=True
    )


    candidates.to_parquet(
        OUTPUT_PATH,
        index=False
    )


    print()

    print(
        "Saved:",
        OUTPUT_PATH
    )


if __name__ == "__main__":
    main()