from __future__ import annotations

from pathlib import Path

import pandas as pd

RAW = Path("data/raw")

OUTPUT = Path(
    "data/analysis/market_location_analysis.parquet"
)


# Character setup
BROKER_RELATIONS = 2
ACCOUNTING = 0


# Known important trading locations
LOCATIONS = {
    60003760: "Jita 4-4 NPC",
    1044752365771: "Perimeter Structure",
}


def broker_fee(
    broker_relations: int,
    structure: bool,
) -> float:
    """
    Estimate broker fee.
    """

    if structure:
        return 0.01

    return max(
        0.03 - 0.003 * broker_relations,
        0.01,
    )


def sales_tax(
    accounting: int,
) -> float:
    """
    Estimate sales tax.
    """

    return (
        0.075
        *
        (1 - 0.11 * accounting)
    )


def round_trip_cost(
    structure: bool,
) -> float:

    buy_fee = broker_fee(
        BROKER_RELATIONS,
        structure,
    )

    sell_fee = broker_fee(
        BROKER_RELATIONS,
        structure,
    )

    tax = sales_tax(
        ACCOUNTING,
    )

    return (
        buy_fee
        +
        sell_fee
        +
        tax
    )


def latest_snapshot():

    files = sorted(
        RAW.glob(
            "the_forge_orders_*.parquet"
        )
    )

    if not files:
        raise FileNotFoundError(
            "No order snapshot found"
        )

    return pd.read_parquet(
        files[-1]
    )


def main():

    print(
        "Loading market orders..."
    )

    orders = latest_snapshot()


    orders = orders[
        orders.location_id.isin(
            LOCATIONS.keys()
        )
    ]


    orders["location"] = (
        orders.location_id.map(
            LOCATIONS
        )
    )


    results = []


    for (
        (type_id, location),
        group,
    ) in orders.groupby(
        [
            "type_id",
            "location",
        ]
    ):


        buys = group[
            group.is_buy_order
        ]

        sells = group[
            ~group.is_buy_order
        ]


        if buys.empty or sells.empty:
            continue


        best_bid = (
            buys.price.max()
        )

        best_ask = (
            sells.price.min()
        )


        spread_pct = (
            (best_ask - best_bid)
            /
            best_bid
            *
            100
        )


        total_volume = (
            group.volume_remain.sum()
        )


        buy_volume = (
            buys.volume_remain.sum()
        )


        sell_volume = (
            sells.volume_remain.sum()
        )


        order_count = len(group)


        # concentration:
        # largest single order / total volume

        largest_order = (
            group.volume_remain.max()
        )


        concentration = (
            largest_order
            /
            total_volume
        )


        structure = (
            "Structure"
            in location
        )


        fees = (
            round_trip_cost(
                structure
            )
        )


        fee_pct = (
            fees * 100
        )


        gross_edge = (
            spread_pct
        )


        net_edge = (
            gross_edge
            -
            fee_pct
        )


        # crude quality score

        liquidity_score = (
            min(
                order_count / 100,
                1,
            )
            *
            min(
                total_volume / 1e9,
                1,
            )
        )


        quality_score = (
            net_edge
            *
            liquidity_score
            *
            (1 - concentration)
        )


        results.append(
            {

                "type_id": type_id,

                "location": location,

                "best_bid": best_bid,

                "best_ask": best_ask,

                "spread_pct": spread_pct,

                "transaction_cost_pct": fee_pct,

                "net_edge_pct": net_edge,

                "orders": order_count,

                "volume": total_volume,

                "buy_volume": buy_volume,

                "sell_volume": sell_volume,

                "concentration": concentration,

                "quality_score": quality_score,
            }
        )


    result = pd.DataFrame(
        results
    )


    result = result.sort_values(
        "quality_score",
        ascending=False,
    )


    print(
        "\nBest same-location Alpha opportunities:"
    )


    print(
        result.head(50)
    )


    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )


    result.to_parquet(
        OUTPUT,
        index=False,
    )


    print(
        "\nSaved:"
    )

    print(
        OUTPUT
    )


if __name__ == "__main__":
    main()