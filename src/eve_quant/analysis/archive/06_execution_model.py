from __future__ import annotations

import os
import numpy as np
import pandas as pd


INPUT_PATH = (
    "data/analysis/live_validation.parquet"
)

OUTPUT_PATH = (
    "data/analysis/execution_model.parquet"
)


# Alpha account assumptions
# Broker Relations II
# Trade III
# Marketing II

BROKER_FEE = 0.0475
SALES_TAX = 0.033


# realistic constraints

CAPITAL = 10_000_000

MIN_PROFIT_ISK = 100_000

MIN_RETURN_PCT = 2.0



def estimate_execution_quality(
    row: pd.Series,
):

    units = row["units"]

    buy_price = row["buy_price"]

    sell_price = row["sell_price"]


    if units <= 0:
        return None


    gross_cost = (
        units
        *
        buy_price
    )


    gross_revenue = (
        units
        *
        sell_price
    )


    broker_cost = (
        gross_cost
        *
        BROKER_FEE
    )


    tax_cost = (
        gross_revenue
        *
        SALES_TAX
    )


    total_fees = (
        broker_cost
        +
        tax_cost
    )


    profit = (
        gross_revenue
        -
        gross_cost
        -
        total_fees
    )


    return_pct = (
        profit
        /
        gross_cost
        *
        100
    )


    return {

        "capital_used":
            gross_cost,

        "units":
            units,

        "gross_profit_isk":
            gross_revenue
            -
            gross_cost,

        "broker_fee_isk":
            broker_cost,

        "sales_tax_isk":
            tax_cost,

        "total_fee_drag_isk":
            total_fees,

        "net_profit_isk":
            profit,

        "net_return_pct":
            return_pct,

        "fee_adjusted_edge":
            (
                sell_price
                -
                buy_price
            )
            /
            buy_price
            -
            BROKER_FEE
            -
            SALES_TAX,

    }



def main():

    print(
        "Loading live validation..."
    )


    df = pd.read_parquet(
        INPUT_PATH
    )


    print(
        f"Candidates: {len(df)}"
    )


    results = []


    for _, row in df.iterrows():

        execution = estimate_execution_quality(
            row
        )


        if execution is None:
            continue


        result = {

            **row.to_dict(),

            **execution,

        }


        results.append(
            result
        )


    result = pd.DataFrame(
        results
    )


    if len(result) == 0:

        print(
            "No executable candidates."
        )

        return



    # remove tiny theoretical trades

    result = result[
        (
            result.net_profit_isk
            >=
            MIN_PROFIT_ISK
        )
        &
        (
            result.net_return_pct
            >=
            MIN_RETURN_PCT
        )
    ]


    result = result.sort_values(
        [
            "net_return_pct",
            "net_profit_isk",
        ],
        ascending=False,
    )


    print()

    print(
        "EXECUTION MODEL RESULTS"
    )

    print(
        result[
            [
                "type_id",
                "name",
                "category",
                "units",
                "buy_price",
                "sell_price",
                "net_profit_isk",
                "net_return_pct",
                "fee_adjusted_edge",
            ]
        ]
        .head(50)
        .to_string(
            index=False
        )
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