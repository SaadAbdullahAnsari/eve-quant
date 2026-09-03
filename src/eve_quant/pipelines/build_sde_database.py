from __future__ import annotations

from eve_quant.sde import (
    load_type_database,
    save_type_database,
)


def main() -> None:
    print("Loading CCP SDE...")

    df = load_type_database()

    print(f"Loaded {len(df):,} published items.")

    save_type_database(df)

    print("Saved processed database:")

    print("data/sde/types.parquet")


if __name__ == "__main__":
    main()
