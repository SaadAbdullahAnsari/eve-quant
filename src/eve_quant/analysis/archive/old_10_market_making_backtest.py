from pathlib import Path

import numpy as np
import pandas as pd


DATA_PATH = (
    "data/processed/research_dataset.parquet"
)

CANDIDATE_PATH = (
    "data/analysis/market_making_candidates.parquet"
)

OUTPUT_PATH = (
    "data/analysis/market_making_backtest.parquet"
)


STARTING_CAPITAL = 500_000_000

BROKER_FEE = 0.036
SALES_TAX = 0.0345


DAYS = 60



def estimate_fill(
    volume,
    order_count,
    inventory_value
):
    """
    Estimate passive fill probability.

    More volume/orders:
        easier fills

    More inventory:
        slower turnover
    """

    if volume <= 0:
        return 0.05


    liquidity = (

        np.log1p(volume)

        +

        np.log1p(order_count)

    )


    inventory_penalty = (

        1 +

        inventory_value /
        500_000_000

    )


    probability = (

        liquidity /
        50

        /

        inventory_penalty

    )


    return np.clip(
        probability,
        0.01,
        0.8
    )



def simulate_item(
    df,
    type_id
):

    item = df[
        df["type_id"]
        ==
        type_id
    ].copy()


    item = item.sort_values(
        "date"
    )


    if len(item) < 30:
        return None



    cash = STARTING_CAPITAL

    inventory = 0


    equity_curve = []


    trades = 0


    for _, row in item.iterrows():


        price = row["average"]


        if price <= 0:
            continue



        #
        # Dynamic spread estimate
        #

        volatility = row.get(
            "volatility_30d",
            0.05
        )


        spread = max(

            volatility * 0.5,

            0.01

        )


        bid = (

            price *

            (
                1 -
                spread
            )

        )


        ask = (

            price *

            (
                1 +
                spread
            )

        )



        inventory_value = (

            inventory *

            price

        )


        fill_probability = estimate_fill(

            row["volume"],

            row["order_count"],

            abs(inventory_value)

        )



        #
        # Buy side
        #

        if np.random.random() < fill_probability:


            buy_amount = min(

                cash * 0.1,

                50_000_000

            )


            units = (

                buy_amount /

                bid

            )


            cost = (

                units *

                bid

            )


            fees = (

                cost *

                BROKER_FEE

            )


            cash -= (
                cost +
                fees
            )


            inventory += units

            trades += 1




        #
        # Sell side
        #

        if inventory > 0:


            if np.random.random() < fill_probability:


                sell_units = (

                    inventory *

                    0.1

                )


                revenue = (

                    sell_units *

                    ask

                )


                fees = (

                    revenue *

                    SALES_TAX

                )


                cash += (

                    revenue -
                    fees

                )


                inventory -= sell_units

                trades += 1



        #
        # Mark to market
        #

        equity = (

            cash +

            inventory *

            price

        )


        equity_curve.append(
            equity
        )



    if len(equity_curve) == 0:
        return None



    curve = np.array(
        equity_curve
    )


    returns = (

        curve[-1]

        /

        STARTING_CAPITAL

        -

        1

    )


    peak = np.maximum.accumulate(
        curve
    )


    drawdown = (

        curve -

        peak

    ) / peak



    return {


        "type_id":

            type_id,


        "days":

            len(curve),


        "trades":

            trades,


        "final_equity":

            curve[-1],


        "return_pct":

            returns * 100,


        "max_drawdown_pct":

            drawdown.min()
            *
            100,


        "average_equity":

            curve.mean(),


        "ending_inventory":

            inventory

    }




def main():

    print(
        "Loading datasets..."
    )


    history = pd.read_parquet(
        DATA_PATH
    )


    candidates = pd.read_parquet(
        CANDIDATE_PATH
    )


    ids = candidates[
        "type_id"
    ].unique()



    print(
        "Candidates:",
        len(ids)
    )



    results = []



    for type_id in ids:


        result = simulate_item(

            history,

            type_id

        )


        if result:

            results.append(
                result
            )



    if not results:

        print(
            "No results"
        )

        return



    results = pd.DataFrame(
        results
    )


    results = results.merge(

        candidates[

            [
                "type_id",

                "name",

                "category_name",

                "market_making_score"

            ]

        ],

        on="type_id",

        how="left"

    )



    results = results.sort_values(

        "return_pct",

        ascending=False

    )


    print(
        "\nBACKTEST RESULTS\n"
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