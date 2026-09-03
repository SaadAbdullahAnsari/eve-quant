"""Run the complete on-demand EVE Quant advisor and write an action sheet.

The default path refreshes the Jita order book once, then rebuilds all research
outputs locally.  It never schedules itself and never places an in-game order.
"""

from __future__ import annotations

import argparse
import math
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import requests

ROOT = Path(__file__).resolve().parents[2]
ANALYSIS = ROOT / "data/analysis"
REPORTS = ROOT / "reports"
STAGES = [
    "analysis/00_alpha_constraints.py",
    "analysis/01_universe_quality.py",
    "analysis/02_market_structure.py",
    "analysis/03_signal_features.py",
    "analysis/04_candidate_ranker.py",
]
JITA_LOCATION_ID = 60003760
THE_FORGE_REGION_ID = 10000002
HUBS = {
    "jita": ("Jita 4-4", THE_FORGE_REGION_ID, JITA_LOCATION_ID),
    "amarr": ("Amarr VIII (Oris)", 10000043, 60008494),
    "dodixie": ("Dodixie IX", 10000032, 60011866),
    "rens": ("Rens VI", 10000030, 60004588),
}


def live_hub_book(type_id: int, hub: str = "jita") -> dict[str, float | str]:
    """Fetch the current station-local book directly from ESI."""
    hub_name, region_id, location_id = HUBS[hub]
    response = requests.get(
        f"https://esi.evetech.net/latest/markets/{region_id}/orders/",
        params={"order_type": "all", "type_id": int(type_id)},
        timeout=12,
    )
    response.raise_for_status()
    local_orders = [
        order
        for order in response.json()
        if order["location_id"] == location_id
        and order["price"] > 0
        and order["volume_remain"] > 0
    ]
    buys = [order for order in local_orders if order["is_buy_order"]]
    sells = [order for order in local_orders if not order["is_buy_order"]]
    if not buys or not sells:
        raise ValueError(f"No live two-sided {hub_name} book for type {type_id}.")
    best_bid = max(order["price"] for order in buys)
    best_ask = min(order["price"] for order in sells)
    checked_at = datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
    return {
        "best_bid": best_bid,
        "best_ask": best_ask,
        "buy_queue_units": sum(
            order["volume_remain"] for order in buys if order["price"] == best_bid
        ),
        "sell_queue_units": sum(
            order["volume_remain"] for order in sells if order["price"] == best_ask
        ),
        "checked_at": checked_at,
        "hub": hub_name,
    }


def live_jita_book(type_id: int) -> dict[str, float | str]:
    """Compatibility wrapper for the main Jita candidate pipeline."""
    return live_hub_book(type_id, "jita")


def recent_market_history(
    type_id: int, days: int = 14, region_id: int = THE_FORGE_REGION_ID
) -> tuple[float, float]:
    """Return 14-day average ISK turnover and daily order count from ESI."""
    response = requests.get(
        f"https://esi.evetech.net/latest/markets/{region_id}/history/",
        params={"type_id": int(type_id)},
        timeout=12,
    )
    response.raise_for_status()
    history = response.json()[-days:]
    if not history:
        return 0.0, 0.0
    turnover = sum(day["average"] * day["volume"] for day in history) / len(history)
    orders = sum(day["order_count"] for day in history) / len(history)
    return float(turnover), float(orders)


def recent_hub_quote_churn(hub: str, snapshot_count: int = 4) -> pd.DataFrame:
    """Measure best-price changes across saved Jita snapshots.

    This is a coarse, deliberately conservative measure: it detects a market
    that needs frequent order updates, not actual queue position or fills.
    """
    paths = sorted((ROOT / "data/raw").glob(f"{hub}_orders_*.parquet"))[
        -snapshot_count:
    ]
    quotes: list[pd.DataFrame] = []
    for sequence, path in enumerate(paths):
        orders = pd.read_parquet(
            path,
            columns=["type_id", "is_buy_order", "price", "volume_remain"],
        )
        orders = orders[orders["volume_remain"] > 0]
        buys = (
            orders[orders["is_buy_order"]]
            .groupby("type_id", as_index=False)["price"]
            .max()
            .rename(columns={"price": "best_bid"})
        )
        sells = (
            orders[~orders["is_buy_order"]]
            .groupby("type_id", as_index=False)["price"]
            .min()
            .rename(columns={"price": "best_ask"})
        )
        quotes.append(
            buys.merge(sells, on="type_id", how="outer").assign(sequence=sequence)
        )
    if len(quotes) < 2:
        return pd.DataFrame(
            columns=["type_id", "quote_samples", "bid_change_rate", "ask_change_rate"]
        )
    quote_frame = pd.concat(quotes, ignore_index=True).sort_values(
        ["type_id", "sequence"]
    )
    grouped = quote_frame.groupby("type_id")
    summary = grouped.agg(
        quote_samples=("sequence", "count"),
        bid_change_rate=(
            "best_bid",
            lambda prices: prices.pct_change(fill_method=None).dropna().ne(0).sum()
            / max(len(prices) - 1, 1),
        ),
        ask_change_rate=(
            "best_ask",
            lambda prices: prices.pct_change(fill_method=None).dropna().ne(0).sum()
            / max(len(prices) - 1, 1),
        ),
    ).reset_index()
    return summary.fillna(1.0)


def recent_jita_quote_churn(snapshot_count: int = 4) -> pd.DataFrame:
    """Compatibility wrapper for callers that explicitly need Jita churn."""
    return recent_hub_quote_churn("jita", snapshot_count)


def market_tick(price: float) -> float:
    for threshold, tick in (
        (100, 0.01),
        (1_000, 0.1),
        (10_000, 1),
        (100_000, 10),
        (1_000_000, 100),
        (10_000_000, 1_000),
        (100_000_000, 10_000),
        (1_000_000_000, 100_000),
        (10_000_000_000, 1_000_000),
    ):
        if price < threshold:
            return tick
    return 10_000_000


def fill_probability(daily_turnover: float, order_value: float) -> float:
    # ESI does not expose fills at our queue position. Until local snapshot
    # history is calibrated, cap this explicit assumption at 50%.
    available_flow = daily_turnover * 3 / 2
    return (
        0.0
        if order_value <= 0
        else min(0.50, available_flow / (available_flow + order_value))
    )


def run_script(relative_path: str, env: dict[str, str]) -> None:
    subprocess.run(
        [sys.executable, str(ROOT / "src/eve_quant" / relative_path)],
        cwd=ROOT,
        env=env,
        check=True,
    )


def build_action_sheet(
    capital: float, max_orders: int, candidate_pool: int = 20, hub: str = "jita"
) -> pd.DataFrame:
    """Validate a broad, liquid shortlist with fresh orders and 14-day history."""
    results = pd.read_parquet(ANALYSIS / "candidate_markets.parquet")
    alpha = pd.read_parquet(ANALYSIS / "alpha_constraints.parquet").iloc[0]
    names = pd.read_parquet(ROOT / "data/sde/types.parquet")[["type_id", "name"]]
    results = results.merge(names, on="type_id", how="left")
    results["name"] = results["name"].fillna(results["type_id"].astype(str))
    churn = recent_hub_quote_churn(hub)
    results = results.merge(churn, on="type_id", how="left").fillna(
        {"quote_samples": 0, "bid_change_rate": 1.0, "ask_change_rate": 1.0}
    )
    results = results.sort_values("candidate_score", ascending=False).head(
        candidate_pool
    )

    def fetch_live_data(type_id: int) -> tuple[dict[str, float | str], float, float]:
        book = live_hub_book(type_id, hub)
        turnover, orders = recent_market_history(type_id, region_id=HUBS[hub][1])
        return book, turnover, orders

    validations: dict[int, tuple[dict[str, float | str], float, float]] = {}
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            executor.submit(fetch_live_data, int(row.type_id)): int(row.type_id)
            for row in results.itertuples(index=False)
        }
        for future in as_completed(futures):
            type_id = futures[future]
            try:
                validations[type_id] = future.result()
            except (requests.RequestException, ValueError) as error:
                print(f"Skipping type {type_id}: live validation failed ({error})")

    remaining = capital
    recommendations: list[dict] = []
    for row in results.itertuples(index=False):
        if len(recommendations) >= max_orders:
            break
        validation = validations.get(int(row.type_id))
        if validation is None:
            continue
        book, daily_turnover, daily_orders = validation
        live_bid = float(book["best_bid"])
        live_ask = float(book["best_ask"])
        # A four-check-in trader cannot reliably win an update war. Join only
        # saved books whose top prices have remained reasonably stable.
        if (
            row.quote_samples < 3
            or row.bid_change_rate > 0.34
            or row.ask_change_rate > 0.34
        ):
            continue
        entry_price = live_bid
        exit_price = live_ask - market_tick(live_ask)
        if exit_price <= entry_price or daily_turnover < float(
            alpha["minimum_daily_volume_isk"]
        ):
            continue
        proposed_capital = min(
            capital * float(alpha["max_single_item_exposure"]),
            daily_turnover * 0.05,
            float(row.sell_depth_units_1pct) * entry_price * 0.10,
            remaining,
        )
        units = math.floor(proposed_capital / entry_price)
        if units <= 0:
            continue
        spent = units * entry_price
        fee_cost = units * entry_price * float(
            alpha["broker_fee"]
        ) + units * exit_price * (
            float(alpha["broker_fee"]) + float(alpha["sales_tax"])
        )
        cycle_profit = units * (exit_price - entry_price) - fee_cost
        post_tax_return_pct = cycle_profit / spent * 100
        fill_chance = fill_probability(daily_turnover, spent)
        expected_profit = cycle_profit * fill_chance
        if post_tax_return_pct < float(
            alpha["minimum_net_return_pct"]
        ) * 100 or cycle_profit < float(alpha["minimum_cycle_profit_isk"]):
            continue
        remaining -= spent
        recommendations.append(
            {
                "action": "Low-touch buy: join the best bid; do not chase an outbid. List after fill.",
                "item": row.name,
                "type_id": row.type_id,
                "buy_price_isk": entry_price,
                "sell_price_isk": exit_price,
                "units": units,
                "isk_to_commit": spent,
                "cycle_profit_isk": cycle_profit,
                "expected_profit_isk": expected_profit,
                "expected_return_pct": expected_profit / spent * 100,
                "post_tax_return_pct": post_tax_return_pct,
                "cycle_fill_probability": fill_chance,
                "bid_change_rate": row.bid_change_rate,
                "ask_change_rate": row.ask_change_rate,
                "daily_turnover_isk_14d": daily_turnover,
                "daily_orders_14d": daily_orders,
                "stress_liquidation_loss_isk": spent
                * -(2 * float(alpha["broker_fee"]) + float(alpha["sales_tax"])),
                "risk_score": row.candidate_score,
                "live_checked_utc": str(book["checked_at"]),
            }
        )
    return pd.DataFrame(recommendations)


def write_report(
    recommendations: pd.DataFrame, capital: float, max_orders: int
) -> None:
    REPORTS.mkdir(exist_ok=True)
    csv_path = REPORTS / "current_recommendations.csv"
    markdown_path = REPORTS / "current_recommendations.md"
    recommendations.to_csv(csv_path, index=False)
    committed = (
        recommendations["isk_to_commit"].sum() if not recommendations.empty else 0
    )
    expected_profit = (
        recommendations["expected_profit_isk"].sum() if not recommendations.empty else 0
    )
    stress_loss = (
        recommendations["stress_liquidation_loss_isk"].sum()
        if not recommendations.empty
        else 0
    )
    lines = [
        "# EVE Quant — Current Action Sheet",
        "",
        f"Generated: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}",
        f"Capital supplied: {capital:,.0f} ISK | Order limit: {max_orders}",
        f"Recommended commitment: {committed:,.0f} ISK",
        f"Modelled expected profit per passive-order cycle: {expected_profit:,.0f} ISK",
        f"Immediate-liquidation stress loss: {stress_loss:,.0f} ISK",
        "",
        "Each recommended price was rechecked directly against the live hub ESI book immediately before this report was written.",
        "These remain passive-order estimates; do not buy at the ask.",
        "",
    ]
    if recommendations.empty:
        lines.append("No candidate passed the current safety and expected-value gates.")
    else:
        lines.extend(["## Do this", ""])
        for index, row in recommendations.iterrows():
            lines.extend(
                [
                    f"{index + 1}. **{row['item']}** — place a buy order for {row['units']:,.0f} at {row['buy_price_isk']:,.2f} ISK each.",
                    f"   Once filled, list at {row['sell_price_isk']:,.2f} ISK. Completed-cycle profit: {row['cycle_profit_isk']:,.0f} ISK ({row['post_tax_return_pct']:.1f}% post-fee); 14-day daily turnover: {row['daily_turnover_isk_14d']:,.0f} ISK.",
                    f"   Probability-weighted expected profit: {row['expected_profit_isk']:,.0f} ISK, using the provisional {row['cycle_fill_probability']:.0%} fill assumption.",
                ]
            )
    markdown_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Action sheet: {markdown_path}")
    print(f"Spreadsheet-friendly output: {csv_path}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Refresh EVE Quant and write a current action sheet."
    )
    parser.add_argument(
        "--capital", type=float, default=427_934_016, help="Available ISK to allocate."
    )
    parser.add_argument(
        "--max-orders",
        type=int,
        default=5,
        help="Maximum simultaneous recommendations.",
    )
    parser.add_argument(
        "--max-item-exposure",
        type=float,
        default=0.20,
        help="Maximum fraction of capital in one item.",
    )
    parser.add_argument(
        "--candidate-pool",
        type=int,
        default=20,
        help="How many ranked markets receive live validation (default: 20).",
    )
    parser.add_argument(
        "--hub",
        choices=sorted(HUBS),
        default="jita",
        help="Station hub to collect and evaluate (default: jita).",
    )
    parser.add_argument(
        "--no-refresh",
        action="store_true",
        help="Reuse the newest downloaded Jita snapshot (for offline testing).",
    )
    args = parser.parse_args()
    if (
        args.capital <= 0
        or args.max_orders <= 0
        or args.candidate_pool <= 0
        or not 0 < args.max_item_exposure <= 1
    ):
        parser.error(
            "capital, max-orders, and candidate-pool must be positive; max-item-exposure must be in (0, 1]."
        )

    env = os.environ.copy()
    env["EVE_QUANT_CAPITAL"] = str(int(args.capital))
    env["EVE_QUANT_MAX_SINGLE_ITEM_EXPOSURE"] = str(args.max_item_exposure)
    env["EVE_QUANT_MAX_ACTIVE_ORDERS"] = str(args.max_orders)
    env["EVE_QUANT_TRADE"] = "3"
    env["EVE_QUANT_MARKETING"] = "2"
    env["EVE_QUANT_BROKER_RELATIONS"] = "2"
    env["EVE_QUANT_HUB"] = args.hub
    if not args.no_refresh:
        run_script("pipelines/collect_jita_orders.py", env)
    for stage in STAGES:
        run_script(stage, env)
    write_report(
        build_action_sheet(
            args.capital, args.max_orders, args.candidate_pool, args.hub
        ),
        args.capital,
        args.max_orders,
    )


if __name__ == "__main__":
    main()
