from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

SDE_PATH = Path("data/sde/categories.jsonl")

OUTPUT = Path("data/sde/categories.parquet")


def main():

    rows = []

    with open(
        SDE_PATH,
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
                    "category_id": item["_key"],
                    "category_name": name.get(
                        "en",
                        "Unknown",
                    ),
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

    print(df.head())

    print(f"Saved {len(df)} categories")


if __name__ == "__main__":
    main()
