from __future__ import annotations

import logging
from typing import Any

import requests

ESI_ROOT_URL = "https://esi.evetech.net"
BASE_URL = f"{ESI_ROOT_URL}/latest"

THE_FORGE_REGION_ID = 10000002

COMPATIBILITY_DATE = "2026-08-31"

LOGGER = logging.getLogger(__name__)


class ESIClient:
    """Minimal client for public EVE ESI endpoints."""

    def __init__(
        self,
        timeout: float = 30.0,
    ) -> None:

        self.timeout = timeout

        self.session = requests.Session()

        self.session.headers.update(
            {
                "User-Agent": "eve-quant/0.1",
                "X-Compatibility-Date": COMPATIBILITY_DATE,
                "Accept": "application/json",
            }
        )

    def get_region_orders(
        self,
        region_id: int,
        order_type: str = "all",
    ) -> list[dict[str, Any]]:
        """
        Download all active market orders
        for a region.
        """

        url = f"{BASE_URL}/markets/" f"{region_id}/orders/"

        first_response = self.session.get(
            url,
            params={
                "order_type": order_type,
                "page": 1,
            },
            timeout=self.timeout,
        )

        first_response.raise_for_status()

        total_pages = int(
            first_response.headers.get(
                "X-Pages",
                "1",
            )
        )

        LOGGER.info(
            "Region %s contains %s ESI pages",
            region_id,
            total_pages,
        )

        orders = first_response.json()

        for page in range(
            2,
            total_pages + 1,
        ):
            LOGGER.info(
                "Downloading page %s/%s",
                page,
                total_pages,
            )

            response = self.session.get(
                url,
                params={
                    "order_type": order_type,
                    "page": page,
                },
                timeout=self.timeout,
            )

            response.raise_for_status()

            orders.extend(response.json())

        return orders

    def get_market_history(
        self,
        region_id: int,
        type_id: int,
    ) -> list[dict[str, Any]]:
        """
        Download historical market prices
        for an item in a region.

        Returns daily:
        - average price
        - high price
        - low price
        - volume
        - order count
        """

        url = f"{BASE_URL}/markets/" f"{region_id}/history/"

        response = self.session.get(
            url,
            params={
                "type_id": type_id,
            },
            timeout=self.timeout,
        )

        response.raise_for_status()

        return response.json()

    def get_route(
        self,
        origin_system_id: int,
        destination_system_id: int,
    ) -> list[int]:
        """
        Return the shortest ESI route
        between two systems.
        """

        if origin_system_id == destination_system_id:
            return [origin_system_id]

        url = f"{ESI_ROOT_URL}/route/" f"{origin_system_id}/" f"{destination_system_id}"

        response = self.session.post(
            url,
            json={
                "preference": "Shorter",
                "security_penalty": 50,
            },
            timeout=self.timeout,
        )

        response.raise_for_status()

        return response.json()

    def get_jump_count(
        self,
        origin_system_id: int,
        destination_system_id: int,
    ) -> int:
        """
        Return number of jumps between systems.
        """

        route = self.get_route(
            origin_system_id,
            destination_system_id,
        )

        return max(
            len(route) - 1,
            0,
        )
