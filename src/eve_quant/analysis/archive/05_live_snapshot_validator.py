from __future__ import annotations

import os
import pandas as pd
import numpy as np

from eve_quant.core.esi import ESIClient


INPUT_PATH = (
    "data/analysis/candidate_rankings.parquet"
)

OUTPUT_PATH = (
    "data/analysis/live_validation.parquet"
)


THE_FORGE_REGION_ID = 10000002


# Alpha assumptions

BROKER_FEE = 0.0475
SALES_TAX = 0.033


TEST_CAPITAL = 10_000_000


MIN_FILL_CONFIDENCE = 0.5


# --------------------------------------------------
# Helpers
# --------------------------------------------------


def simulate_execution(
    orders: pd.DataFrame,
    buy: bool,
    isk_budget: float,
):

    if buy:

        book = orders[
            orders["is_buy_order"] == False
        ].copy()

        book = book.sort_values(
            "price"
        )

    else:

        book = orders[
            orders["is_buy_order"] == True
        ].copy()

        book = book.sort_values(
            "price",
            ascending=False
        )


    remaining_isk = isk_budget

    units = 0

    spent = 0


    for _, row in book.iterrows():

        price = row["price"]

        available = row["volume_remain"]


        affordable = (
            remaining_isk
            /
            price
        )


        amount = min(
            available,
            affordable,
        )


        if amount <= 0:
            break


        units += amount

        value = amount * price

        spent += value

        remaining_isk -= value


        if remaining_isk <= 0:
            break


    if units == 0:

        return {
            "units":0,
            "average_price":np.nan,
        }


    return {

        "units":units,

        "average_price":
            spent / units,

    }



# --------------------------------------------------
# Main
# --------------------------------------------------


def main():

    print(
        "Loading candidates..."
    )


    candidates = pd.read_parquet(
        INPUT_PATH
    )


    print(
        f"Candidates: {len(candidates)}"
    )


    client = ESIClient()


    print(
        "Downloading live orders..."
    )


    orders = client.get_region_orders(
        THE_FORGE_REGION_ID
    )


    orders = pd.DataFrame(
        orders
    )


    print(
        f"Orders downloaded: {len(orders):,}"
    )


    results = []


    for _, item in candidates.iterrows():

        type_id = item["type_id"]


        market = orders[
            orders.type_id == type_id
        ]


        if len(market) == 0:

            continue


        buy_side = simulate_execution(
            market,
            buy=False,
            isk_budget=TEST_CAPITAL,
        )


        sell_side = simulate_execution(
            market,
            buy=True,
            isk_budget=TEST_CAPITAL,
        )


        if (
            buy_side["units"] == 0
            or
            sell_side["units"] == 0
        ):

            continue


        buy_price = (
            buy_side["average_price"]
        )

        sell_price = (
            sell_side["average_price"]
        )


        gross_return = (
            sell_price
            -
            buy_price
        ) / buy_price


        fee_drag = (
            BROKER_FEE
            +
            SALES_TAX
        )


        net_return = (
            gross_return
            -
            fee_drag
        )


        results.append(

            {

            "type_id":
                type_id,

            "name":
                item["name"],

            "category":
                item["category_name"],


            "capital":
                TEST_CAPITAL,


            "buy_price":
                buy_price,


            "sell_price":
                sell_price,


            "units":
                min(
                    buy_side["units"],
                    sell_side["units"],
                ),


            "gross_return_pct":
                gross_return * 100,


            "net_return_pct":
                net_return * 100,


            "candidate_score":
                item["candidate_score"],

            }

        )


    result = pd.DataFrame(
        results
    )


    if len(result):

        result = result.sort_values(
            "net_return_pct",
            ascending=False,
        )


    print()

    print(
        "LIVE VALIDATION RESULTS"
    )

    print(
        result.head(50)
        .to_string(index=False)
    )


    os.makedirs(
        "data/analysis",
        exist_ok=True
    )


    result.to_parquet(
        OUTPUT_PATH,
        index=False,
    )


    print()

    print(
        "Saved:"
    )

    print(
        OUTPUT_PATH
    )


if __name__ == "__main__":
    main()