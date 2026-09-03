from pathlib import Path

import numpy as np
import pandas as pd


CAPITAL = 500_000_000

CANDIDATES_PATH = (
    "data/analysis/market_making_candidates.parquet"
)

STRUCTURE_PATH = (
    "data/analysis/market_structure.parquet"
)

OUTPUT_PATH = (
    "data/analysis/queue_simulation.parquet"
)


BROKER_FEE = 0.036
SALES_TAX = 0.0345



def estimate_fill_probability(
    queue_volume,
    daily_flow
):
    """
    Estimate probability of order filling.

    Approximation:

        incoming volume
        ----------------
        queue ahead

    """

    if queue_volume <= 0:
        return 0.01


    turnover = (
        daily_flow /
        queue_volume
    )


    probability = (
        1 -
        np.exp(-turnover)
    )


    return np.clip(
        probability,
        0.01,
        0.95
    )



def simulate(row):

    bid = row["best_bid"]
    ask = row["best_ask"]


    if bid <= 0:
        return None


    if ask <= bid:
        return None


    spread = ask - bid


    #
    # Daily opposing market flow
    #

    daily_units = (

        row["median_daily_isk_volume"]

        /

        bid

    )


    buy_fill = estimate_fill_probability(

        row["buy_depth_1pct_units"],

        daily_units

    )


    sell_fill = estimate_fill_probability(

        row["sell_depth_1pct_units"],

        daily_units

    )


    cycle_probability = (

        buy_fill

        *

        sell_fill

    )


    #
    # Capital deployment
    #

    theoretical_units = (

        CAPITAL

        /

        bid

    )


    filled_units = (

        theoretical_units

        *

        cycle_probability

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


    gross_profit = (

        sell_value

        -

        buy_value

    )


    fees = (

        buy_value * BROKER_FEE

        +

        sell_value * SALES_TAX

    )


    net_profit = (

        gross_profit

        -

        fees

    )


    return {


        "type_id":

            row["type_id"],


        "name":

            row["name"],


        "category":

            row["category_name"],


        "capital":

            CAPITAL,


        "bid":

            bid,


        "ask":

            ask,


        "spread_pct":

            spread /
            bid *
            100,


        "buy_fill_probability":

            buy_fill,


        "sell_fill_probability":

            sell_fill,


        "cycle_probability":

            cycle_probability,


        "filled_units":

            filled_units,


        "gross_profit_isk":

            gross_profit,


        "fees_isk":

            fees,


        "net_profit_isk":

            net_profit,


        "return_pct":

            net_profit /
            CAPITAL *
            100,


        "market_making_score":

            row["market_making_score"]

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
        "Candidates:",
        len(candidates)
    )


    #
    # Restrict to Jita
    #

    structure = structure[
        structure["venue"]
        ==
        "Jita 4-4"
    ]


    #
    # Keep only required columns
    #

    structure = structure[

        [

            "type_id",

            "best_bid",

            "best_ask",

            "buy_depth_1pct_units",

            "sell_depth_1pct_units",

            "median_daily_isk_volume",

        ]

    ]



    #
    # Remove duplicates
    #

    structure = (

        structure

        .drop_duplicates(
            "type_id"
        )

    )


    #
    # Merge cleanly
    #

    df = candidates.merge(

        structure,

        on="type_id",

        how="inner"

    )


    print(
        "After merge:",
        len(df)
    )


    print(
        "Columns:"
    )

    print(
        df.columns.tolist()
    )



    results = []


    for _, row in df.iterrows():

        result = simulate(
            row
        )

        if result:

            results.append(
                result
            )



    if len(results) == 0:

        print(
            "No results"
        )

        return



    results = pd.DataFrame(
        results
    )


    results = results.sort_values(

        "net_profit_isk",

        ascending=False

    )


    print(
        "\nQUEUE SIMULATION RESULTS\n"
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