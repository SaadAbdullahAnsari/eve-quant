def validate_columns(
    df,
    required,
    name="dataset"
):

    missing = set(required) - set(df.columns)


    if missing:

        raise ValueError(
            f"{name} missing columns: {missing}"
        )


    return True