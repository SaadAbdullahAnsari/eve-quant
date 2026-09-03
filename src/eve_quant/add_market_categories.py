from pathlib import Path

import pandas as pd

TYPES = Path("data/sde/types.parquet")

GROUPS = Path("data/sde/groups.parquet")

CATEGORIES = Path("data/sde/categories.parquet")

OUTPUT = Path("data/sde/types_with_categories.parquet")


def main():

    types = pd.read_parquet(TYPES)

    groups = pd.read_parquet(GROUPS)

    categories = pd.read_parquet(CATEGORIES)

    df = types.merge(
        groups,
        on="group_id",
        how="left",
    ).merge(
        categories,
        on="category_id",
        how="left",
    )

    df.to_parquet(
        OUTPUT,
        index=False,
    )

    print(
        df[
            [
                "name",
                "group_name",
                "category_name",
            ]
        ].head(20)
    )

    print("Saved:")

    print(OUTPUT)


if __name__ == "__main__":
    main()
