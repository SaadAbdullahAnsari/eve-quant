from pathlib import Path

import numpy as np
import pandas as pd


INPUT_PATH = (
    "data/analysis/market_making_backtest.parquet"
)

OUTPUT_PATH = (
    "data/analysis/risk_adjusted_ranking.parquet"
)



def main():

    print(
        "Loading backtest..."
    )


    df = pd.read_parquet(
        INPUT_PATH
    )


    print(
        "Strategies:",
        len(df)
    )


    #
    # Risk adjusted return
    #

    df["risk_adjusted_return"] = (

        df["return_pct"]

        /

        (
            abs(
                df["max_drawdown_pct"]
            )

            +

            1e-6

        )

    )



    #
    # Inventory exposure
    #

    df["inventory_ratio"] = (

        abs(
            df["ending_inventory"]
        )

        /

        (
            df["final_equity"]

            +

            1e-6

        )

    )


    #
    # Trading frequency
    #

    df["trade_frequency"] = (

        df["trades"]

        /

        df["days"]

    )



    #
    # Normalisation helper
    #

    def normalise(series):

        minimum = series.min()

        maximum = series.max()


        if maximum == minimum:

            return pd.Series(
                np.ones(len(series)),
                index=series.index
            )


        return (

            series - minimum

        ) / (

            maximum - minimum

        )



    #
    # Scores
    #

    df["risk_score"] = normalise(
        df["risk_adjusted_return"]
    )


    df["return_score"] = normalise(
        df["return_pct"]
    )


    df["activity_score"] = normalise(
        df["trade_frequency"]
    )


    #
    # Lower inventory is better
    #

    df["inventory_score"] = (

        1 -

        normalise(
            df["inventory_ratio"]
        )

    )



    #
    # Final ranking
    #

    df["strategy_score"] = (

        0.45 *
        df["risk_score"]

        +

        0.25 *
        df["return_score"]

        +

        0.15 *
        df["activity_score"]

        +

        0.15 *
        df["inventory_score"]

    )


    df = df.sort_values(

        "strategy_score",

        ascending=False

    )


    print(
        "\nRISK ADJUSTED STRATEGY RANKING\n"
    )


    print(

        df[

            [

                "type_id",

                "name",

                "category_name",

                "return_pct",

                "max_drawdown_pct",

                "trades",

                "ending_inventory",

                "risk_adjusted_return",

                "strategy_score"

            ]

        ]

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


    df.to_parquet(

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