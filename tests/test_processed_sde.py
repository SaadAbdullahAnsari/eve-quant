from pathlib import Path

import pandas as pd


def test_processed_sde_exists():

    path = Path("data/sde/types.parquet")

    assert path.exists()


def test_processed_sde_contains_items():

    df = pd.read_parquet("data/sde/types.parquet")

    assert not df.empty

    assert "type_id" in df.columns
    assert "name" in df.columns
