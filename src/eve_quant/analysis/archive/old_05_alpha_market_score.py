from pathlib import Path

import numpy as np
import pandas as pd


CANDIDATES = (
    "data/analysis/"
    "candidate_markets.parquet"
)

STRUCTURE = (
    "data/analysis/"
    "market_structure.parquet"
)

ALPHA = (
    "data/analysis/"
    "alpha_constraints.parquet"
)

OUTPUT = (
    "data/analysis/"
    "alpha_market_score.parquet"
)


# -----------------------------
# Alpha assumptions
# -----------------------------

CAPITAL = 500_000_000

ORDER_SLOTS = 17


def minmax(series):

    low = series.min()
    high = series.max()

    if high == low:
        return series * 0

    return (
        series - low
    ) / (
        high - low
    )



def main():

    print(
        "Loading datasets..."
    )


    candidates = pd.read_parquet(
        CANDIDATES
    )


    structure = pd.read_parquet(
        STRUCTURE
    )


    alpha = pd.read_parquet(
        ALPHA
    ).iloc[0]



    print(
        "Candidates:",
        len(candidates)
    )



    # -----------------------------
    # Merge
    # -----------------------------

    df = candidates.merge(
    structure[
        [
            "type_id",
            "venue",
            "best_bid",
            "best_ask",
        ]
    ],
    on="type_id",
    how="inner"
    )


    print(
        "After merge:",
        len(df)
    )



    # -----------------------------
    # Alpha fees
    # -----------------------------

    broker_fee = alpha[
        "broker_fee"
    ]

    sales_tax = alpha[
        "sales_tax"
    ]



    df["effective_spread"] = (

        df["gross_spread_pct"]

        -

        broker_fee

        -

        sales_tax

    )



    # -----------------------------
    # Capital model
    #
    # Assume deploy 1% of capital
    # per market initially
    # -----------------------------

    df["capital_required"] = (

        df["two_sided_depth_1pct_isk"]

        *

        0.05

    )


    df["capital_required"] = (

        df["capital_required"]
        .clip(
            lower=1_000_000
        )

    )



    # -----------------------------
    # Expected daily turnover
    # -----------------------------

    df["turnover_capacity"] = (

        df["two_sided_depth_1pct_isk"]

        *

        0.25

    )



    df["expected_daily_profit"] = (

        df["turnover_capacity"]

        *

        df["effective_spread"]

    )



    # -----------------------------
    # Capital efficiency
    # -----------------------------

    df["capital_efficiency"] = (

        df["expected_daily_profit"]

        /

        df["capital_required"]

    )



    # -----------------------------
    # Fill probability proxy
    #
    # Higher depth
    # Lower concentration
    # More orders
    # -----------------------------

    depth_score = minmax(
        df[
            "two_sided_depth_1pct_isk"
        ]
    )


    competition_score = 1 - (

        (
            df["buy_concentration"]

            +

            df["sell_concentration"]

        )

        /

        2

    )


    order_score = minmax(

        df["buy_order_count"]

        +

        df["sell_order_count"]

    )


    df["fill_probability"] = (

        0.5 *
        depth_score

        +

        0.3 *
        competition_score

        +

        0.2 *
        order_score

    )



    # -----------------------------
    # Inventory risk
    # -----------------------------

    df["inventory_risk"] = (

        df["volatility"]

        *

        df["capital_required"]

        /

        CAPITAL

    )



    # -----------------------------
    # Slot efficiency
    # -----------------------------

    df["slot_efficiency"] = (

        df["expected_daily_profit"]

        /

        ORDER_SLOTS

    )



    # -----------------------------
    # Venue adjustment
    # -----------------------------

    df["venue_score"] = 1.0


    df.loc[
        df["venue"]
        ==
        "Perimeter 60000358",
        "venue_score"
    ] = 1.05



    # -----------------------------
    # Normalised score components
    # -----------------------------

    df["capital_eff_norm"] = minmax(
        df["capital_efficiency"]
    )


    df["spread_norm"] = minmax(
        df["effective_spread"]
    )


    df["inventory_norm"] = 1 - minmax(
        df["inventory_risk"]
    )


    df["slot_norm"] = minmax(
        df["slot_efficiency"]
    )



    # -----------------------------
    # Final Alpha score
    # -----------------------------

    df["alpha_score"] = (

        0.30 *
        df["capital_eff_norm"]

        +

        0.25 *
        df["fill_probability"]

        +

        0.20 *
        df["spread_norm"]

        +

        0.15 *
        df["inventory_norm"]

        +

        0.10 *
        df["slot_norm"]

    ) * df["venue_score"]



    output = df[

        [

            "type_id",

            "venue",

            "best_bid",

            "best_ask",

            "effective_spread",

            "capital_required",

            "expected_daily_profit",

            "capital_efficiency",

            "slot_efficiency",

            "fill_probability",

            "inventory_risk",

            "alpha_score",

        ]

    ].sort_values(

        "alpha_score",

        ascending=False

    )



    Path(
        "data/analysis"
    ).mkdir(
        exist_ok=True
    )


    output.to_parquet(
        OUTPUT,
        index=False
    )



    print(
        "\nTOP ALPHA MARKETS\n"
    )


    print(
        output.head(30)
        .to_string(
            index=False
        )
    )


    print(
        "\nSaved:",
        OUTPUT
    )



if __name__ == "__main__":
    main()