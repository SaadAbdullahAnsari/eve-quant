from eve_quant.sde import load_type_database

df = load_type_database()

print(
    df[
        df["type_id"].isin(
            [
                34,
                35,
                36,
                37,
                38,
            ]
        )
    ]
)
