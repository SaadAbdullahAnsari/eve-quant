import runpy
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
EXECUTOR = runpy.run_path(ROOT / "src/eve_quant/analysis/05_executor_simulator.py")
STRUCTURE = runpy.run_path(ROOT / "src/eve_quant/analysis/02_market_structure.py")


def test_passive_fill_probability_is_bounded_and_queue_sensitive():
    fill_probability = EXECUTOR["fill_probability"]

    assert fill_probability(0, 100, 100) == 0
    assert 0 < fill_probability(1_000_000, 100_000, 50_000) <= 0.95
    assert fill_probability(1_000_000, 10_000_000, 50_000) < fill_probability(
        1_000_000, 100_000, 50_000
    )


def test_liquidation_walks_best_bids_first_and_respects_available_volume():
    liquidation_value = EXECUTOR["liquidation_value"]
    bids = pd.DataFrame({"price": [10.0, 8.0], "volume_remain": [3.0, 5.0]})

    proceeds, filled = liquidation_value(bids, 6)

    assert filled == 6
    assert proceeds == 54


def test_near_touch_depth_excludes_distant_orders():
    near_touch_depth = STRUCTURE["near_touch_depth"]
    asks = pd.DataFrame(
        {"price": [100.0, 100.5, 105.0], "volume_remain": [2.0, 3.0, 99.0]}
    )

    units, isk = near_touch_depth(asks, 100.0, "sell")

    assert units == 5
    assert isk == 501.5
