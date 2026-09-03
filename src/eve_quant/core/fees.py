from dataclasses import dataclass


@dataclass
class TraderProfile:
    name: str

    broker_relations: int
    accounting: int

    npc_station: bool = True

    structure_broker_fee: float = 0.01


def npc_broker_fee(
    broker_relations: int,
    faction_standing: float = 0,
    corp_standing: float = 0,
):

    fee = (
        0.03
        - 0.003 * broker_relations
        - 0.0003 * faction_standing
        - 0.0002 * corp_standing
    )

    return max(fee, 0.01)


def sales_tax(accounting: int):

    return 0.075 * (1 - 0.11 * accounting)


def broker_fee(trader: TraderProfile, location_type="npc"):

    if location_type == "structure":
        return trader.structure_broker_fee

    return npc_broker_fee(trader.broker_relations)


def round_trip_cost(trader: TraderProfile, location_type="npc"):

    buy = broker_fee(trader, location_type)

    sell = broker_fee(trader, location_type)

    tax = sales_tax(trader.accounting)

    return buy + sell + tax


if __name__ == "__main__":

    alpha = TraderProfile(name="Alpha", broker_relations=2, accounting=0)

    print("NPC:", round_trip_cost(alpha))

    print("Structure:", round_trip_cost(alpha, "structure"))
