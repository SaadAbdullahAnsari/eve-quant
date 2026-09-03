from pathlib import Path

import numpy as np
import pandas as pd


CANDIDATES_PATH = (
    "data/analysis/market_making_candidates.parquet"
)

STRUCTURE_PATH = (
    "data/analysis/market_structure.parquet"
)

OUTPUT_PATH = (
    "data/analysis/market_making_backtest.parquet"
)


CAPITAL_LEVELS = [
    10_000_000,
    50_000_000,
    100_000_000,
    500_000_000,
]


# Alpha approximate values
BROKER_FEE = 0.036
SALES_TAX = 0.0345



def estimate_fill_probability(row):

    """
    Approximate passive order fill probability.

    Uses:
    - historical volume
    - order activity
    - competition

    This is deliberately conservative.
    """


    volume_factor = np.tanh(
        row["avg_isk_volume"] / 1e10
    )


    order_factor = np.tanh(
        row["avg_orders"] / 500
    )


    competition_factor = (

        1
        -
        (
            row["buy_concentration"]
            +
            row["sell_concentration"]
        )
        /
        2

    )


    probability = (

        0.45 * volume_factor

        +

        0.35 * order_factor

        +

        0.20 * competition_factor

    )


    return np.clip(
        probability,
        0.01,
        0.90
    )



def simulate_trade(row, capital):


    bid = row["best_bid"]

    ask = row["best_ask"]


    if bid <= 0 or ask <= 0:
        return None


    if ask <= bid:
        return None



    spread_pct = (

        (ask - bid)

        /

        bid

        *

        100

    )


    units = capital / bid


    buy_fill = estimate_fill_probability(
        row
    )


    sell_fill = estimate_fill_probability(
        row
    )


    filled_units = (

        units

        *

        buy_fill

        *

        sell_fill

    )


    buy_value = (

        filled_units

        *

        bid

    )


    sell_value = (

        filled_units

        *

        ask

    )


    broker_fee = (

        buy_value

        *

        BROKER_FEE

    )


    sales_tax = (

        sell_value

        *

        SALES_TAX

    )


    gross_profit = (

        sell_value

        -

        buy_value

    )


    net_profit = (

        gross_profit

        -

        broker_fee

        -

        sales_tax

    )


    return {

        "units":

            filled_units,


        "buy_fill_probability":

            buy_fill,


        "sell_fill_probability":

            sell_fill,


        "gross_profit_isk":

            gross_profit,


        "fees_isk":

            broker_fee + sales_tax,


        "net_profit_isk":

            net_profit,


        "return_pct":

            net_profit / capital * 100,


        "spread_pct":

            spread_pct,


        "capital_utilisation":

            buy_value / capital,

    }



def main():


    print(
        "Loading datasets..."
    )


    candidates = pd.read_parquet(
        CANDIDATES_PATH
    )


    structure = pd.read_parquet(
        STRUCTURE_PATH
    )


    print(
        "Candidate rows:",
        len(candidates)
    )


    #
    # Only Jita
    #

    structure = structure[
        structure["venue"]
        ==
        "Jita 4-4"
    ]


    #
    # Remove duplicate locations
    #

    structure = (

        structure
        .sort_values(
            "two_sided_depth_1pct_isk",
            ascending=False
        )

        .drop_duplicates(
            "type_id"
        )

    )


    #
    # Only add execution fields
    #

    structure_fields = [

        "type_id",

        "best_bid",

        "best_ask",

        "two_sided_depth_1pct_isk",

    ]


    df = candidates.merge(

        structure[
            structure_fields
        ],

        on="type_id",

        how="inner"

    )


    print(
        "After merge:",
        len(df)
    )


    results = []


    for _, row in df.iterrows():


        for capital in CAPITAL_LEVELS:


            output = simulate_trade(
                row,
                capital
            )


            if output is None:
                continue


            results.append({

                "type_id":
                    row["type_id"],


                "name":
                    row["name"],


                "category":
                    row["category_name"],


                "capital":
                    capital,


                **output,


                "market_making_score":
                    row["market_making_score"],

            })



    results = pd.DataFrame(
        results
    )


    if len(results) == 0:

        print(
            "No results"
        )

        return



    results["risk_adjusted_score"] = (

        results["net_profit_isk"]

        *

        results["buy_fill_probability"]

        *

        results["sell_fill_probability"]

    )


    results = results.sort_values(

        [

            "capital",

            "risk_adjusted_score"

        ],

        ascending=[

            True,

            False

        ]

    )



    print()

    print(
        "MARKET MAKING BACKTEST RESULTS"
    )

    print(

        results
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


    results.to_parquet(
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