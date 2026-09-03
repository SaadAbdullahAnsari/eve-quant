from __future__ import annotations

import os
import pandas as pd
import numpy as np

from eve_quant.core.esi import ESIClient


INPUT_PATH = (
    "data/analysis/candidate_rankings.parquet"
)

OUTPUT_PATH = (
    "data/analysis/order_book_depth_model.parquet"
)


THE_FORGE_REGION_ID = 10000002


CAPITAL = 10_000_000


# Alpha assumptions
BROKER_FEE = 0.0475
SALES_TAX = 0.033



def execute_buy(
    orders: pd.DataFrame,
    capital: float,
):

    sells = orders[
        orders["is_buy_order"] == False
    ].copy()


    sells = sells.sort_values(
        "price"
    )


    remaining = capital

    units = 0

    cost = 0


    for _, order in sells.iterrows():

        price = order["price"]

        volume = order["volume_remain"]


        affordable = remaining / price


        fill = min(
            volume,
            affordable,
        )


        if fill <= 0:
            continue


        value = (
            fill
            *
            price
        )


        units += fill

        cost += value

        remaining -= value


        if remaining <= 0:
            break


    if units == 0:
        return None


    return {

        "units":
            units,

        "vwap":
            cost / units,

        "cost":
            cost,

    }



def execute_sell(
    orders: pd.DataFrame,
    units: float,
):

    buys = orders[
        orders["is_buy_order"] == True
    ].copy()


    buys = buys.sort_values(
        "price",
        ascending=False,
    )


    remaining = units

    revenue = 0

    filled = 0


    for _, order in buys.iterrows():

        price = order["price"]

        volume = order["volume_remain"]


        fill = min(
            volume,
            remaining,
        )


        if fill <= 0:
            continue


        value = (
            fill
            *
            price
        )


        revenue += value

        filled += fill

        remaining -= fill


        if remaining <= 0:
            break



    if filled == 0:
        return None


    return {

        "units":
            filled,

        "vwap":
            revenue / filled,

        "revenue":
            revenue,

    }



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
        "Downloading live order book..."
    )


    orders = pd.DataFrame(
        client.get_region_orders(
            THE_FORGE_REGION_ID
        )
    )


    print(
        f"Orders: {len(orders):,}"
    )


    results = []


    for _, candidate in candidates.iterrows():


        type_id = candidate["type_id"]


        market = orders[
            orders.type_id == type_id
        ]


        if len(market) == 0:
            continue



        buy = execute_buy(
            market,
            CAPITAL,
        )


        if buy is None:
            continue



        sell = execute_sell(
            market,
            buy["units"],
        )


        if sell is None:
            continue



        entry = buy["vwap"]

        exit = sell["vwap"]



        gross_return = (
            exit
            -
            entry
        ) / entry



        gross_cost = (
            buy["cost"]
        )


        gross_revenue = (
            sell["revenue"]
        )


        fees = (
            gross_cost
            *
            BROKER_FEE
            +
            gross_revenue
            *
            SALES_TAX
        )


        profit = (
            gross_revenue
            -
            gross_cost
            -
            fees
        )


        entry_slippage = (
            entry
            -
            market[
                market.is_buy_order == False
            ]["price"].min()
        ) / entry



        exit_slippage = (
            market[
                market.is_buy_order == True
            ]["price"].max()
            -
            exit
        ) / exit



        results.append(

            {

            "type_id":
                type_id,

            "name":
                candidate["name"],

            "category":
                candidate["category_name"],


            "units":
                buy["units"],


            "entry_vwap":
                entry,

            "exit_vwap":
                exit,


            "entry_slippage":
                entry_slippage,

            "exit_slippage":
                exit_slippage,


            "gross_return_pct":
                gross_return * 100,


            "net_profit_isk":
                profit,


            "net_return_pct":
                profit
                /
                gross_cost
                *
                100,


            "candidate_score":
                candidate["candidate_score"],

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
        "ORDER BOOK DEPTH RESULTS"
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