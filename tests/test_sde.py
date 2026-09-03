from pathlib import Path

from eve_quant.core.sde import load_type_database


def test_type_database_loads():
    """
    Ensure the SDE type database exists and loads correctly.
    """

    path = Path("data/sde/types.jsonl")

    assert path.exists(), (
        "SDE types.jsonl file is missing. "
        "Download the CCP SDE and place it in data/sde/"
    )

    df = load_type_database(path)

    assert not df.empty

    assert "type_id" in df.columns
    assert "name" in df.columns


def test_known_items_exist():
    """
    Check that common market items are present.
    """

    path = Path("data/sde/types.jsonl")

    df = load_type_database(path)

    names = set(df["name"])

    expected_items = {
        "Tritanium",
        "Pyerite",
        "Mexallon",
        "Isogen",
        "Nocxium",
    }

    missing = expected_items - names

    assert not missing, f"Missing expected items: {missing}"
