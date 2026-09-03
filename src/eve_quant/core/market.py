from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pandas as pd

JITA_44_LOCATION_ID = 60003760
JITA_SYSTEM_ID = 30000142

JumpLookup = Callable[[int, int], int]


def buy_order_reaches_location(
    order: pd.Series,
    target_location_id: int,
    target_system_id: int,
    jump_lookup: JumpLookup,
) -> bool:
    """
    Determine whether a buy order can be fulfilled from a target location.

    EVE buy-order ranges may be:

    - station
    - solarsystem
    - region
    - a numeric jump range such as 1, 5, 10, etc.
    """

    if not bool(order["is_buy_order"]):
        return False

    order_location_id = int(order["location_id"])
    order_system_id = int(order["system_id"])

    order_range = str(order["range"]).lower().strip()

    if order_range == "station":
        return order_location_id == target_location_id

    if order_range == "solarsystem":
        return order_system_id == target_system_id

    if order_range == "region":
        # Our input data is already restricted to The Forge.
        return True

    try:
        max_jumps = int(order_range)
    except ValueError as exc:
        raise ValueError(f"Unknown market-order range: {order['range']!r}") from exc

    jumps = jump_lookup(
        order_system_id,
        target_system_id,
    )

    return jumps <= max_jumps


def find_best_executable_buy_order(
    orders: pd.DataFrame,
    target_location_id: int,
    target_system_id: int,
    jump_lookup: JumpLookup,
) -> pd.Series | None:
    """
    Return the highest-priced buy order that can be fulfilled
    from the target location.
    """

    buy_orders = orders[orders["is_buy_order"]].copy()

    if buy_orders.empty:
        return None

    buy_orders = buy_orders.sort_values(
        "price",
        ascending=False,
    )

    # Start at the most valuable order.
    # Stop as soon as we find one executable from Jita.
    for _, order in buy_orders.iterrows():
        if buy_order_reaches_location(
            order=order,
            target_location_id=target_location_id,
            target_system_id=target_system_id,
            jump_lookup=jump_lookup,
        ):
            return order

    return None


def build_market_state(
    orders: pd.DataFrame,
    type_id: int,
    item_name: str,
    target_location_id: int,
    target_system_id: int,
    jump_lookup: JumpLookup,
) -> dict[str, Any]:
    """
    Build a compact market-state summary for one item.
    """

    item_orders = orders[orders["type_id"] == type_id].copy()

    local_orders = item_orders[item_orders["location_id"] == target_location_id]

    local_buy_orders = local_orders[local_orders["is_buy_order"]]

    local_sell_orders = local_orders[~local_orders["is_buy_order"]]

    best_local_bid = (
        float(local_buy_orders["price"].max()) if not local_buy_orders.empty else None
    )

    best_local_ask = (
        float(local_sell_orders["price"].min()) if not local_sell_orders.empty else None
    )

    best_executable_order = find_best_executable_buy_order(
        orders=item_orders,
        target_location_id=target_location_id,
        target_system_id=target_system_id,
        jump_lookup=jump_lookup,
    )

    if best_executable_order is not None:
        best_executable_bid = float(best_executable_order["price"])

        executable_source_location = int(best_executable_order["location_id"])

        executable_source_system = int(best_executable_order["system_id"])

        executable_range = str(best_executable_order["range"])

    else:
        best_executable_bid = None
        executable_source_location = None
        executable_source_system = None
        executable_range = None

    if best_local_bid is not None and best_local_ask is not None:
        local_mid = (best_local_bid + best_local_ask) / 2

        local_spread = best_local_ask - best_local_bid

        local_spread_pct = (local_spread / local_mid) * 100

    else:
        local_mid = None
        local_spread = None
        local_spread_pct = None

    if best_executable_bid is not None and best_local_ask is not None:
        executable_spread = best_local_ask - best_executable_bid

        executable_mid = (best_local_ask + best_executable_bid) / 2

        executable_spread_pct = (executable_spread / executable_mid) * 100

    else:
        executable_spread = None
        executable_spread_pct = None

    return {
        "type_id": type_id,
        "item": item_name,
        "best_local_bid": best_local_bid,
        "best_executable_bid": best_executable_bid,
        "best_local_ask": best_local_ask,
        "local_mid": local_mid,
        "local_spread": local_spread,
        "local_spread_pct": local_spread_pct,
        "executable_spread": executable_spread,
        "executable_spread_pct": executable_spread_pct,
        "local_bid_volume": int(local_buy_orders["volume_remain"].sum()),
        "local_ask_volume": int(local_sell_orders["volume_remain"].sum()),
        "local_buy_orders": len(local_buy_orders),
        "local_sell_orders": len(local_sell_orders),
        "exec_bid_location_id": executable_source_location,
        "exec_bid_system_id": executable_source_system,
        "exec_bid_range": executable_range,
    }
