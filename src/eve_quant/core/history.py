from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
from eve_quant.esi import (
    THE_FORGE_REGION_ID,
    ESIClient,
)

RAW_DIR = Path("data/raw")


def collect_history(
    type_ids: list[int],
) -> pd.DataFrame:
    """
    Download historical market data
    for selected items.
    """

    client = ESIClient()

    rows = []

    total = len(type_ids)

    for index, type_id in enumerate(
        type_ids,
        start=1,
    ):

        print(f"[{index}/{total}] " f"Fetching {type_id}")

        history = client.get_market_history(
            region_id=THE_FORGE_REGION_ID,
            type_id=type_id,
        )

        for day in history:

            rows.append(
                {
                    "type_id": type_id,
                    "date": day["date"],
                    "average": day["average"],
                    "highest": day["highest"],
                    "lowest": day["lowest"],
                    "volume": day["volume"],
                    "order_count": day["order_count"],
                }
            )

    return pd.DataFrame(rows)


def save_history(
    df: pd.DataFrame,
) -> Path:

    RAW_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    timestamp = datetime.now(UTC)

    path = RAW_DIR / (
        "market_history_" f"{timestamp.strftime('%Y%m%dT%H%M%SZ')}" ".parquet"
    )

    df.to_parquet(
        path,
        index=False,
    )

    return path
