"""Build a conservative, station-local view of the current order book.

All percentage fields in this project are stored as decimals: 0.05 means 5%.
"""

import os
from pathlib import Path

import numpy as np
import pandas as pd

RAW_DIR = Path("data/raw")
OUTPUT = Path("data/analysis/market_structure.parquet")

NEAR_TOUCH_BAND = 0.01
MAX_GROSS_SPREAD = 0.50
MIN_TOTAL_BOOK_ISK_PER_SIDE = 1_000_000
MIN_NEAR_TOUCH_DEPTH_ISK_PER_SIDE = 5_000_000


def latest_snapshot() -> Path:
    hub_key = os.environ.get("EVE_QUANT_HUB", "jita").casefold()
    snapshots = sorted(RAW_DIR.glob(f"{hub_key}_orders_*.parquet"))
    if not snapshots:
        raise FileNotFoundError(f"No {hub_key} order snapshots found in data/raw.")
    return snapshots[-1]


def concentration(values: pd.Series) -> float:
    total = values.sum()
    return 1.0 if total <= 0 else float(values.max() / total)


def near_touch_depth(
    orders: pd.DataFrame, reference_price: float, side: str
) -> tuple[float, float]:
    if side == "buy":
        orders = orders[orders["price"] >= reference_price * (1 - NEAR_TOUCH_BAND)]
    else:
        orders = orders[orders["price"] <= reference_price * (1 + NEAR_TOUCH_BAND)]
    units = float(orders["volume_remain"].sum())
    return units, float((orders["price"] * orders["volume_remain"]).sum())


def main() -> None:
    source = latest_snapshot()
    orders = pd.read_parquet(source)
    required = {
        "type_id",
        "is_buy_order",
        "price",
        "volume_remain",
        "location_id",
        "system_id",
    }
    missing = required - set(orders.columns)
    if missing:
        raise ValueError(f"Order snapshot is missing columns: {sorted(missing)}")

    orders = orders[(orders["price"] > 0) & (orders["volume_remain"] > 0)].copy()
    results: list[dict] = []
    rejected = {"one_sided": 0, "invalid_price": 0, "wide_spread": 0, "thin_book": 0}

    for type_id, group in orders.groupby("type_id"):
        buys = group[group["is_buy_order"]].sort_values("price", ascending=False)
        sells = group[~group["is_buy_order"]].sort_values("price")
        if buys.empty or sells.empty:
            rejected["one_sided"] += 1
            continue

        best_bid = float(buys.iloc[0]["price"])
        best_ask = float(sells.iloc[0]["price"])
        if best_bid <= 0 or best_ask <= best_bid:
            rejected["invalid_price"] += 1
            continue

        midpoint = (best_bid + best_ask) / 2
        gross_spread_pct = (best_ask - best_bid) / midpoint
        if gross_spread_pct > MAX_GROSS_SPREAD:
            rejected["wide_spread"] += 1
            continue

        buy_book_isk = float((buys["price"] * buys["volume_remain"]).sum())
        sell_book_isk = float((sells["price"] * sells["volume_remain"]).sum())
        buy_depth_units, buy_depth_isk = near_touch_depth(buys, best_bid, "buy")
        sell_depth_units, sell_depth_isk = near_touch_depth(sells, best_ask, "sell")
        if (
            buy_book_isk < MIN_TOTAL_BOOK_ISK_PER_SIDE
            or sell_book_isk < MIN_TOTAL_BOOK_ISK_PER_SIDE
            or buy_depth_isk < MIN_NEAR_TOUCH_DEPTH_ISK_PER_SIDE
            or sell_depth_isk < MIN_NEAR_TOUCH_DEPTH_ISK_PER_SIDE
        ):
            rejected["thin_book"] += 1
            continue

        top_buy_queue_units = float(
            buys.loc[buys["price"] == best_bid, "volume_remain"].sum()
        )
        top_sell_queue_units = float(
            sells.loc[sells["price"] == best_ask, "volume_remain"].sum()
        )
        total_book = buy_book_isk + sell_book_isk
        results.append(
            {
                "type_id": type_id,
                "location_id": int(group["location_id"].iloc[0]),
                "system_id": int(group["system_id"].iloc[0]),
                "venue": str(group["location_id"].iloc[0]),
                "snapshot_path": str(source),
                "best_bid": best_bid,
                "best_ask": best_ask,
                "midpoint": midpoint,
                "gross_spread_isk": best_ask - best_bid,
                "gross_spread_pct": gross_spread_pct,
                "buy_order_count": len(buys),
                "sell_order_count": len(sells),
                "buy_book_isk": buy_book_isk,
                "sell_book_isk": sell_book_isk,
                "buy_depth_units_1pct": buy_depth_units,
                "sell_depth_units_1pct": sell_depth_units,
                "buy_depth_1pct_isk": buy_depth_isk,
                "sell_depth_1pct_isk": sell_depth_isk,
                "two_sided_depth_1pct_isk": buy_depth_isk + sell_depth_isk,
                "top_buy_queue_units": top_buy_queue_units,
                "top_sell_queue_units": top_sell_queue_units,
                "buy_concentration": concentration(buys["volume_remain"]),
                "sell_concentration": concentration(sells["volume_remain"]),
                "book_balance": buy_book_isk / total_book,
                "structure_quality_score": np.log1p(buy_depth_isk + sell_depth_isk)
                + gross_spread_pct * 100,
            }
        )

    result = pd.DataFrame(results)
    if result.empty:
        raise RuntimeError("No market passed the order-book quality gates.")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    result.sort_values("structure_quality_score", ascending=False).to_parquet(
        OUTPUT, index=False
    )
    print(f"Source: {source}")
    print(f"Markets generated: {len(result)}")
    print(f"Rejected: {rejected}")
    print(f"Saved: {OUTPUT}")


if __name__ == "__main__":
    main()
