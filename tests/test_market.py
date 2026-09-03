import pandas as pd

from eve_quant.core.market import (
    build_market_state,
    buy_order_reaches_location,
)

JITA_LOCATION = 60003760
JITA_SYSTEM = 30000142


def fake_jump_lookup(
    origin: int,
    destination: int,
) -> int:
    distances = {
        (30000142, 30000142): 0,
        (999, 30000142): 1,
        (888, 30000142): 2,
    }

    return distances[(origin, destination)]


def test_station_order_at_jita_executes():
    order = pd.Series(
        {
            "is_buy_order": True,
            "location_id": JITA_LOCATION,
            "system_id": JITA_SYSTEM,
            "range": "station",
        }
    )

    assert buy_order_reaches_location(
        order=order,
        target_location_id=JITA_LOCATION,
        target_system_id=JITA_SYSTEM,
        jump_lookup=fake_jump_lookup,
    )


def test_remote_station_order_does_not_execute():
    order = pd.Series(
        {
            "is_buy_order": True,
            "location_id": 12345,
            "system_id": 999,
            "range": "station",
        }
    )

    assert not buy_order_reaches_location(
        order=order,
        target_location_id=JITA_LOCATION,
        target_system_id=JITA_SYSTEM,
        jump_lookup=fake_jump_lookup,
    )


def test_one_jump_order_reaches_jita():
    order = pd.Series(
        {
            "is_buy_order": True,
            "location_id": 12345,
            "system_id": 999,
            "range": "1",
        }
    )

    assert buy_order_reaches_location(
        order=order,
        target_location_id=JITA_LOCATION,
        target_system_id=JITA_SYSTEM,
        jump_lookup=fake_jump_lookup,
    )


def test_two_jump_order_does_not_reach_with_range_one():
    order = pd.Series(
        {
            "is_buy_order": True,
            "location_id": 12345,
            "system_id": 888,
            "range": "1",
        }
    )

    assert not buy_order_reaches_location(
        order=order,
        target_location_id=JITA_LOCATION,
        target_system_id=JITA_SYSTEM,
        jump_lookup=fake_jump_lookup,
    )


def test_market_state_prefers_remote_executable_bid():
    orders = pd.DataFrame(
        [
            {
                "type_id": 34,
                "is_buy_order": True,
                "location_id": JITA_LOCATION,
                "system_id": JITA_SYSTEM,
                "range": "station",
                "price": 3.77,
                "volume_remain": 10_000,
            },
            {
                "type_id": 34,
                "is_buy_order": True,
                "location_id": 12345,
                "system_id": 999,
                "range": "1",
                "price": 3.78,
                "volume_remain": 20_000,
            },
            {
                "type_id": 34,
                "is_buy_order": False,
                "location_id": JITA_LOCATION,
                "system_id": JITA_SYSTEM,
                "range": "region",
                "price": 3.83,
                "volume_remain": 30_000,
            },
        ]
    )

    state = build_market_state(
        orders=orders,
        type_id=34,
        item_name="Tritanium",
        target_location_id=JITA_LOCATION,
        target_system_id=JITA_SYSTEM,
        jump_lookup=fake_jump_lookup,
    )

    assert state["best_local_bid"] == 3.77
    assert state["best_executable_bid"] == 3.78
    assert state["best_local_ask"] == 3.83

    assert state["exec_bid_range"] == "1"
