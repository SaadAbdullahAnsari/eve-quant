from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

SDE_PATH = Path("data/sde")

OUTPUT = Path("data/sde/groups.parquet")


def main():

    path = SDE_PATH / "groups.jsonl"

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

            name = item.get("name", {})

            rows.append(
                {
                    "group_id": item["_key"],
                    "group_name": name.get(
                        "en",
                        "Unknown",
                    ),
                    "category_id": item.get("categoryID"),
                }
            )

    df = pd.DataFrame(rows)

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    df.to_parquet(
        OUTPUT,
        index=False,
    )

    print(f"Saved {len(df)} groups")

    print(df.head())


if __name__ == "__main__":
    main()
