"""Conservative passive-order model for the current Jita snapshot.

This is an expected-value screen, not a claim that an order will fill.  It keeps
the immediate cross-spread result as a stress liquidation measure.
"""

from pathlib import Path

import pandas as pd

ANALYSIS = Path("data/analysis")
RAW_DIR = Path("data/raw")
OUTPUT = ANALYSIS / "execution_results.parquet"
FILL_HORIZON_DAYS = 3
MAX_DAILY_TURNOVER_SHARE = 0.05
MAX_NEAR_TOUCH_DEPTH_SHARE = 0.10


def latest_snapshot() -> Path:
    snapshots = sorted(RAW_DIR.glob("jita_orders_*.parquet"))
    if not snapshots:
        raise FileNotFoundError("No Jita order snapshots found in data/raw.")
    return snapshots[-1]


def liquidation_value(buys: pd.DataFrame, units: float) -> tuple[float, float]:
    """Return proceeds and quantity that can be sold by walking current bids."""
    remaining = units
    proceeds = 0.0
    for order in buys.sort_values("price", ascending=False).itertuples():
        filled = min(remaining, float(order.volume_remain))
        proceeds += filled * float(order.price)
        remaining -= filled
        if remaining <= 0:
            break
    return proceeds, units - remaining


def fill_probability(
    daily_isk_volume: float, queue_isk: float, order_isk: float
) -> float:
    # Half of daily flow is conservatively assumed to be relevant to each side.
    expected_flow = daily_isk_volume * FILL_HORIZON_DAYS / 2
    if expected_flow <= 0 or order_isk <= 0:
        return 0.0
    return float(min(0.95, expected_flow / (expected_flow + queue_isk + order_isk)))


def main() -> None:
    candidates = pd.read_parquet(ANALYSIS / "candidate_markets.parquet")
    alpha = pd.read_parquet(ANALYSIS / "alpha_constraints.parquet").iloc[0]
    orders = pd.read_parquet(latest_snapshot())
    broker_fee = float(alpha["broker_fee"])
    sales_tax = float(alpha["sales_tax"])
    capital = float(alpha["starting_capital"])
    max_item_capital = capital * float(alpha["max_single_item_exposure"])
    order_books = {type_id: group for type_id, group in orders.groupby("type_id")}
    results: list[dict] = []

    for row in candidates.itertuples(index=False):
        entry_price = float(row.best_bid)
        exit_price = float(row.best_ask)
        if entry_price <= 0 or exit_price <= entry_price:
            continue
        turnover_capital = float(row.isk_volume_ma_7) * MAX_DAILY_TURNOVER_SHARE
        depth_capital = (
            float(row.sell_depth_units_1pct) * entry_price * MAX_NEAR_TOUCH_DEPTH_SHARE
        )
        committed_capital = min(max_item_capital, turnover_capital, depth_capital)
        units = committed_capital / entry_price
        if units <= 0:
            continue

        buy_queue_isk = float(row.top_buy_queue_units) * entry_price
        sell_queue_isk = float(row.top_sell_queue_units) * exit_price
        entry_fill = fill_probability(
            float(row.isk_volume_ma_7), buy_queue_isk, committed_capital
        )
        exit_fill = fill_probability(
            float(row.isk_volume_ma_7), sell_queue_isk, units * exit_price
        )
        cycle_fill = entry_fill * exit_fill
        fee_cost = units * entry_price * broker_fee + units * exit_price * (
            broker_fee + sales_tax
        )
        cycle_net_profit = units * (exit_price - entry_price) - fee_cost
        expected_net_profit = cycle_net_profit * cycle_fill
        post_tax_return_pct = cycle_net_profit / committed_capital * 100
        if post_tax_return_pct < float(
            alpha["minimum_net_return_pct"]
        ) * 100 or cycle_net_profit < float(alpha["minimum_cycle_profit_isk"]):
            continue

        book = order_books.get(row.type_id)
        if book is None:
            continue
        liquidation_proceeds, liquidated_units = liquidation_value(
            book[book["is_buy_order"]], units
        )
        liquidation_fraction = liquidated_units / units
        liquidation_net_profit = liquidation_proceeds * (
            1 - float(alpha["broker_fee"]) - float(alpha["sales_tax"])
        ) - committed_capital * (1 + float(alpha["broker_fee"]))
        results.append(
            {
                "type_id": row.type_id,
                "venue": row.venue,
                "capital_committed": committed_capital,
                "units": units,
                "entry_price": entry_price,
                "exit_price": exit_price,
                "gross_spread_pct": row.gross_spread_pct,
                "fee_rate": fee_cost / (units * (entry_price + exit_price)),
                "entry_fill_probability": entry_fill,
                "exit_fill_probability": exit_fill,
                "cycle_fill_probability": cycle_fill,
                "cycle_net_profit": cycle_net_profit,
                "expected_net_profit": expected_net_profit,
                "expected_return_pct": expected_net_profit / committed_capital * 100,
                "post_tax_return_pct": post_tax_return_pct,
                "immediate_liquidation_net_profit": liquidation_net_profit,
                "immediate_liquidation_return_pct": liquidation_net_profit
                / committed_capital
                * 100,
                "liquidation_fraction": liquidation_fraction,
                "inventory_risk": committed_capital / capital,
                "candidate_score": row.candidate_score,
                "risk_flags": "MODELLED_FILL",
            }
        )

    result = pd.DataFrame(results)
    if result.empty:
        raise RuntimeError("No candidates produced an executable passive-order model.")
    result = result.sort_values("expected_net_profit", ascending=False)
    result.to_parquet(OUTPUT, index=False)
    print(f"Modelled passive orders: {len(result)}")
    print(result.head(20).to_string(index=False))
    print(f"Saved: {OUTPUT}")


if __name__ == "__main__":
    main()
