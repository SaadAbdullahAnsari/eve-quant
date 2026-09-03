"""Turn an exported inventory list into conservative live sell recommendations.

This program is intentionally CSV-first: reading character assets directly from
ESI requires an OAuth token and must be explicitly opted into by the player.
It never creates, changes, or cancels an in-game order.
"""

from __future__ import annotations

import argparse
import math
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import requests

if __package__:
    from eve_quant.run_advisor import (
        HUBS,
        ROOT,
        live_hub_book,
        market_tick,
        recent_market_history,
    )
else:
    from run_advisor import (
        HUBS,
        ROOT,
        live_hub_book,
        market_tick,
        recent_market_history,
    )

REPORTS = ROOT / "reports"
TEMPLATE = ROOT / "data/input/inventory_template.csv"


def load_inventory(path: Path) -> pd.DataFrame:
    """Load and validate the small, hand-exported inventory interchange file."""
    inventory = pd.read_csv(path)
    required = {"type_id", "item_name", "quantity", "location", "average_cost_isk"}
    missing = required - set(inventory.columns)
    if missing:
        raise ValueError(
            f"Inventory CSV is missing columns: {', '.join(sorted(missing))}"
        )
    types = pd.read_parquet(ROOT / "data/sde/types.parquet")[["type_id", "name"]]
    by_name = types.set_index("name")["type_id"]

    def resolve(row: pd.Series) -> int:
        if pd.notna(row["type_id"]):
            return int(row["type_id"])
        name = str(row["item_name"]).strip()
        if not name or name not in by_name.index:
            raise ValueError(
                f"Unknown item name: {name!r}. Use a valid type_id instead."
            )
        return int(by_name[name])

    inventory = inventory.dropna(how="all").copy()
    if inventory.empty:
        raise ValueError("Inventory CSV has no items. Add rows to the template first.")
    inventory["type_id"] = inventory.apply(resolve, axis=1)
    inventory["quantity"] = pd.to_numeric(inventory["quantity"], errors="raise")
    inventory["average_cost_isk"] = pd.to_numeric(
        inventory["average_cost_isk"], errors="coerce"
    ).fillna(0.0)
    inventory = inventory[inventory["quantity"] > 0]
    return inventory.merge(types, on="type_id", how="left")


def recommend_item(
    row: pd.Series,
    hub_key: str,
    broker_fee: float,
    sales_tax: float,
    allow_hauling: bool,
) -> dict:
    hub_name, region_id, _ = HUBS[hub_key]
    book = live_hub_book(int(row.type_id), hub_key)
    daily_turnover, daily_orders = recent_market_history(
        int(row.type_id), region_id=region_id
    )
    sell_price = float(book["best_ask"]) - market_tick(float(book["best_ask"]))
    net_per_unit = sell_price * (1 - broker_fee - sales_tax)
    immediate_per_unit = float(book["best_bid"]) * (1 - sales_tax)
    list_quantity = min(
        int(row.quantity), max(1, math.floor(daily_turnover * 0.05 / sell_price))
    )
    same_hub = str(row.location).strip().casefold() in {hub_key, hub_name.casefold()}
    target_return = (
        (net_per_unit / float(row.average_cost_isk) - 1)
        if row.average_cost_isk > 0
        else None
    )
    if not same_hub and not allow_hauling:
        action = "RESEARCH ONLY — item is elsewhere; hauling is disabled"
    elif daily_turnover <= 0:
        action = "HOLD — no recent regional trading history"
    elif target_return is not None and target_return < 0:
        action = "HOLD — listing would realise a loss versus stated cost"
    else:
        action = "LIST NOW — passive sell; do not undercut repeatedly"
    return {
        "action": action,
        "item": row.get("name", row.get("item_name")),
        "type_id": int(row.type_id),
        "inventory_location": row.location,
        "market": hub_name,
        "quantity_owned": int(row.quantity),
        "quantity_to_list": list_quantity,
        "suggested_sell_price_isk": sell_price,
        "net_listing_proceeds_isk": net_per_unit * list_quantity,
        "immediate_sell_price_isk": float(book["best_bid"]),
        "immediate_net_proceeds_isk": immediate_per_unit * list_quantity,
        "return_vs_cost_pct": None if target_return is None else target_return * 100,
        "daily_turnover_isk_14d": daily_turnover,
        "daily_orders_14d": daily_orders,
        "live_checked_utc": book["checked_at"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create live sell advice from an inventory CSV."
    )
    parser.add_argument("--inventory", type=Path, default=TEMPLATE)
    parser.add_argument("--hub", choices=sorted(HUBS), default="jita")
    parser.add_argument(
        "--compare-hubs",
        action="store_true",
        help="Check Jita, Amarr, Dodixie, and Rens for every inventory item.",
    )
    parser.add_argument(
        "--allow-hauling",
        action="store_true",
        help="Permit actionable advice for inventory located at another hub.",
    )
    parser.add_argument(
        "--broker-fee",
        type=float,
        default=0.03,
        help="Use your in-game displayed broker fee as a decimal (default 3%%).",
    )
    parser.add_argument(
        "--sales-tax",
        type=float,
        default=0.075,
        help="Use your in-game displayed sales tax as a decimal (default 7.5%%).",
    )
    args = parser.parse_args()
    if not args.inventory.exists():
        parser.error(f"Inventory file not found. Copy and fill {TEMPLATE}")
    inventory = load_inventory(args.inventory)
    rows = []
    hub_keys = sorted(HUBS) if args.compare_hubs else [args.hub]
    jobs = [(item, hub_key) for _, item in inventory.iterrows() for hub_key in hub_keys]
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {
            executor.submit(
                recommend_item,
                item,
                hub_key,
                args.broker_fee,
                args.sales_tax,
                args.allow_hauling,
            ): (item, hub_key)
            for item, hub_key in jobs
        }
        for future in as_completed(futures):
            item, hub_key = futures[future]
            try:
                rows.append(future.result())
            except (requests.RequestException, ValueError) as error:
                print(
                    f"Skipping {item.get('item_name', item.type_id)} in {hub_key}: {error}"
                )
    report = pd.DataFrame(rows)
    REPORTS.mkdir(exist_ok=True)
    csv_path = REPORTS / "inventory_recommendations.csv"
    md_path = REPORTS / "inventory_recommendations.md"
    report.to_csv(csv_path, index=False)
    lines = [
        "# EVE Quant — Inventory Sale Sheet",
        "",
        f"Generated: {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}",
        "",
    ]
    if report.empty:
        lines.append("No inventory rows produced a live recommendation.")
    else:
        for _, item in report.iterrows():
            lines.extend(
                [
                    f"- **{item['item']}**: {item['action']}",
                    f"  List {item['quantity_to_list']:,} in {item['market']} at {item['suggested_sell_price_isk']:,.2f} ISK each; estimated net proceeds {item['net_listing_proceeds_isk']:,.0f} ISK.",
                    "",
                ]
            )
    md_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Inventory action sheet: {md_path}")
    print(f"Spreadsheet-friendly output: {csv_path}")


if __name__ == "__main__":
    main()
