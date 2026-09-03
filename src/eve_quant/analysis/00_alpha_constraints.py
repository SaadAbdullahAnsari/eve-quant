import os
from pathlib import Path

import pandas as pd

OUTPUT = "data/analysis/" "alpha_constraints.parquet"


def calculate_fees():

    # -----------------------------
    # Alpha character assumptions
    # -----------------------------

    broker_relations = int(os.environ.get("EVE_QUANT_BROKER_RELATIONS", "2"))
    accounting = int(os.environ.get("EVE_QUANT_ACCOUNTING", "0"))
    trade = int(os.environ.get("EVE_QUANT_TRADE", "3"))
    marketing = int(os.environ.get("EVE_QUANT_MARKETING", "2"))

    # Jita NPC station fees; standings are deliberately treated as zero.
    broker_fee = 0.03 - (0.003 * broker_relations)

    sales_tax = 0.075 * (1 - 0.11 * accounting)

    return {
        "broker_relations_level": broker_relations,
        "accounting_level": accounting,
        "trade_level": trade,
        "marketing_level": marketing,
        "broker_fee": broker_fee,
        "sales_tax": sales_tax,
    }


def create_constraints():

    fees = calculate_fees()
    trade = int(os.environ.get("EVE_QUANT_TRADE", "3"))
    hub_key = os.environ.get("EVE_QUANT_HUB", "jita").casefold()
    hub_names = {
        "jita": "Jita 4-4",
        "amarr": "Amarr VIII (Oris)",
        "dodixie": "Dodixie IX",
        "rens": "Rens VI",
    }
    if hub_key not in hub_names:
        raise ValueError(f"Unknown EVE_QUANT_HUB {hub_key!r}")

    constraints = {
        **fees,
        # -------------------------
        # Capital
        # -------------------------
        "starting_capital": int(os.environ.get("EVE_QUANT_CAPITAL", "427934016")),
        # maximum ISK exposed in one item
        "max_single_item_exposure": float(
            os.environ.get("EVE_QUANT_MAX_SINGLE_ITEM_EXPOSURE", "0.20")
        ),
        # -------------------------
        # Trading limitations
        # -------------------------
        "max_active_orders": int(
            os.environ.get("EVE_QUANT_MAX_ACTIVE_ORDERS", str(5 + 4 * trade))
        ),
        "max_order_range": 10,
        # -------------------------
        # Market assumptions
        # -------------------------
        "primary_market": hub_names[hub_key],
        "secondary_market": "Perimeter",
        # -------------------------
        # Strategy constraints
        # -------------------------
        "minimum_spread_pct": 0.03,
        "minimum_daily_volume_isk": 50_000_000,
        "minimum_depth_isk": 10_000_000,
        "minimum_net_return_pct": 0.10,
        "minimum_cycle_profit_isk": 10_000_000,
        # -------------------------
        # Risk
        # -------------------------
        "inventory_holding_days_limit": 7,
        "hauling_allowed": False,
    }

    return pd.DataFrame([constraints])


def main():

    print("Building Alpha constraints...")

    df = create_constraints()

    Path("data/analysis").mkdir(exist_ok=True)

    df.to_parquet(OUTPUT, index=False)

    print(df.T)

    print("\nSaved:", OUTPUT)


if __name__ == "__main__":
    main()
