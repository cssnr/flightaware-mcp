import logging
import os
import re
from datetime import datetime, timedelta
from json import JSONDecodeError
from pathlib import Path
from typing import Any, Dict, List, Optional

from hishel import AsyncSqliteStorage, FilterPolicy
from hishel.httpx import AsyncCacheClient

logger = logging.getLogger(__name__)


class FlightAware(object):
    """
    :param api_key: FlightAware API Key or AEROAPI_KEY environment variable
    """

    url = "https://aeroapi.flightaware.com/aeroapi"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("AEROAPI_KEY", "")
        self.headers = {
            "Accept": "application/json; charset=UTF-8",
            "x-apikey": self.api_key,
        }

        cache_path = os.environ.get("HISHEL_CACHE_PATH", Path.cwd() / "hishel_cache.db")
        cache_ttl = int(os.environ.get("HISHEL_CACHE_TTL", "60"))
        logger.info("fa(cache_path=%s, cache_ttl=%s)", cache_path, cache_ttl)
        storage = AsyncSqliteStorage(database_path=cache_path, default_ttl=cache_ttl)
        policy = FilterPolicy()
        self._client = AsyncCacheClient(storage=storage, policy=policy, follow_redirects=True, timeout=10)
        self.airlines: List[Dict] | None = None
        self.iata_to_icao: Dict[str, str] = {}
        self.icao_to_iata: Dict[str, str] = {}

    def __repr__(self):
        return f"FlightAware(api_key=<{self.api_key[:6]}...>)"

    async def close(self):
        await self._client.aclose()

    async def _get_request(self, url, **kwargs) -> Dict[str, Any]:
        try:
            r = await self._client.get(url, headers=self.headers, **kwargs)
            logger.info("hishel_from_cache: %s", r.extensions.get("hishel_from_cache"))
            return r.json()
        except JSONDecodeError:
            # noinspection PyUnboundLocalVariable
            return {"title": f"API Error - Status: {r.status_code}"}
        except Exception as error:
            logger.error("url: %s - error: %s", url, error)
            return {"title": "API Error - Unknown"}

    async def flights_ident(self, ident: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        :param ident: Registration, Flight Number, FA ID
        :param params: Optional: Additional query parameters
        :return: Dictionary from JSON response
        """
        if not params:
            params = {"start": (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")}
        url = f"{self.url}/flights/{ident.strip().upper()}"
        return await self._get_request(url, params=params)

    async def flights_search(self, query: str) -> Dict[str, Any]:
        # NOT USED
        url = f"{self.url}/flights/search"
        params = {"query": query}
        return await self._get_request(url, params=params)

    async def flights_map(self, fa_id: str) -> Dict[str, Any]:
        # NOT USED
        url = f"{self.url}/flights/{fa_id}/map"
        return await self._get_request(url)

    async def operators_id(self, operator_id: str) -> Dict[str, Any]:
        # NOT USED
        url = f"{self.url}/operators/{operator_id}"
        return await self._get_request(url)

    async def owner_ident(self, ident: str) -> Dict[str, Any]:
        # NOT USED
        url = f"{self.url}/aircraft/{ident.upper()}/owner"
        return await self._get_request(url)

    async def get_airlines(self) -> List[Dict]:
        """
        Generates iata_to_icao, icao_to_iata and airlines
        :return: airlines
        """
        if not self.airlines:
            r = await self._client.get(
                "https://raw.githubusercontent.com/npow/airline-codes/refs/heads/master/airlines.json",
                extensions={"hishel_ttl": 604800},
            )
            logger.info("_load_airlines: %s", r.extensions.get("hishel_from_cache"))
            self.airlines = r.json()
            self.iata_to_icao = {a["iata"]: a["icao"] for a in self.airlines if a.get("active") == "Y"}
            self.icao_to_iata = {a["icao"]: a["iata"] for a in self.airlines if a.get("active") == "Y"}
        return self.airlines

    async def get_icao_flight_number(self, flight_number: str) -> str | None:
        logger.info("get_icao_flight_number: %s", flight_number)
        flight_number = flight_number.strip().upper()

        if not re.match("[a-z0-9]{2,3}[0-9]{1,4}", flight_number, re.IGNORECASE):  # NOSONAR
            return None

        if not self.iata_to_icao:
            await self.get_airlines()

        if flight_number[:2] in self.iata_to_icao and flight_number[2:].isdigit():
            icao = self.iata_to_icao[flight_number[:2]]
            if icao:
                return icao + flight_number[2:]

        if flight_number[:3] in self.icao_to_iata and flight_number[3:].isdigit():
            return flight_number

        return None
