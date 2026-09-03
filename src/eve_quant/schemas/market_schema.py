UNIVERSE_COLUMNS = [

    "type_id",
    "name",
    "category_name",

    "observations",
    "avg_price",

    "avg_daily_volume",
    "avg_isk_volume",
    "avg_orders",

    "avg_volatility",
    "history_quality",

    "liquidity_score",
    "tradability_score",

]


STRUCTURE_COLUMNS = [

    "type_id",

    "venue",

    "best_bid",
    "best_ask",
    "midpoint",

    "gross_spread_isk",
    "gross_spread_pct",

    "buy_order_count",
    "sell_order_count",

    "buy_volume_units",
    "sell_volume_units",

    "buy_book_isk",
    "sell_book_isk",

    "buy_concentration",
    "sell_concentration",

    "two_sided_depth_1pct_isk",

    "structure_quality_score",

]


FEATURE_COLUMNS = [

    "type_id",

    "return_1d",
    "return_7d",
    "return_30d",

    "volatility_7d",
    "volatility_30d",

    "price_deviation_30d",

    "isk_volume",
    "isk_volume_ratio",

]


ALPHA_COLUMNS = [

    "broker_relations_level",
    "accounting_level",

    "broker_fee",
    "sales_tax",

    "starting_capital",

    "hauling_allowed",

    "max_order_range",

]