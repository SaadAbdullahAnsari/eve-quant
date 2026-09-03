from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

SDE_DIR = Path("data/sde")


def load_type_database(
    path: Path | None = None,
) -> pd.DataFrame:
    """
    Load EVE type metadata from CCP SDE JSONL.
    """

    if path is None:
        path = SDE_DIR / "types.jsonl"

    if not path.exists():
        raise FileNotFoundError(f"SDE file not found: {path}")

    rows = []

    with open(
        path,
        "r",
        encoding="utf-8",
    ) as f:

        for line in f:

            item = json.loads(line)

            if not item.get(
                "published",
                False,
            ):
                continue

            name = item.get(
                "name",
                {},
            )

            rows.append(
                {
                    "type_id": int(item["_key"]),
                    "name": name.get(
                        "en",
                        "Unknown",
                    ),
                    "group_id": item.get("groupID"),
                    "category_id": item.get("categoryID"),
                    "market_group_id": item.get("marketGroupID"),
                    "volume": item.get("volume"),
                }
            )

    return pd.DataFrame(rows)


def save_type_database(
    df: pd.DataFrame,
    output: Path | None = None,
) -> None:

    if output is None:
        output = SDE_DIR / "types.parquet"

    output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    df.to_parquet(
        output,
        index=False,
    )


def load_processed_type_database(
    path: Path | None = None,
) -> pd.DataFrame:

    if path is None:
        path = SDE_DIR / "types.parquet"

    return pd.read_parquet(path)
