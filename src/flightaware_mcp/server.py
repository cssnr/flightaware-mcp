import json
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Annotated

from mcp.server.fastmcp import Context, FastMCP
from mcp.server.session import ServerSession
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import CallToolResult, TextContent
from pydantic import Field

from ._version import __version__
from .fa import FlightAware

logger = logging.getLogger(__name__)

logging.basicConfig(level=logging.INFO)


@dataclass
class AppContext:
    fa: FlightAware


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[AppContext]:
    logger.info("%s %s", server.name, __version__)
    fa = FlightAware()
    try:
        yield AppContext(fa=fa)
    finally:
        await fa.close()


mcp = FastMCP(
    "flightaware",
    lifespan=app_lifespan,
    json_response=True,
    stateless_http=True,
    transport_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
)

# noinspection PyProtectedMember
mcp._mcp_server.version = __version__


@mcp.tool()
async def search_flights(
    flight_number: Annotated[str, Field(description="ICAO or IATA Flight Number, Example: UA123, UAL123")],
    ctx: Context[ServerSession, AppContext],
) -> CallToolResult:
    """Returns a list of flights for a given ICAO or IATA Flight Number from the FlightAware API."""
    logger.info("search_flights: %s", flight_number)
    icao = await ctx.request_context.lifespan_context.fa.get_icao_flight_number(flight_number)
    ident = icao or flight_number
    logger.info("ident: %s", ident)
    fa: FlightAware = ctx.request_context.lifespan_context.fa
    # flights = await fa.flights_search(f"-identOrReg {flight_or_registration}")
    flights = await fa.flights_ident(ident)
    logger.info("flights: %s", flights)
    text = json.dumps(flights)
    is_error = flights.get("status")
    if is_error:
        logger.error("is_error: %s - %s", is_error, flights)
    return CallToolResult(content=[TextContent(type="text", text=text)], isError=bool(is_error))


@mcp.tool()
async def iata_to_icao(
    flight_number: Annotated[str, Field(description="ICAO or IATA flight number, ex: AA100, ASA602, UAL123")],
    ctx: Context[ServerSession, AppContext],
) -> CallToolResult:
    """Return an ICAO Flight Number from an IATA or ICAO Flight Number, ex: AS602 → ASA602 or ASA602 → ASA602"""
    logger.info("iata_to_icao: %s", flight_number)
    result = await ctx.request_context.lifespan_context.fa.get_icao_flight_number(flight_number)
    logger.info("result: %s", result)
    text = result or f"Unable to convert flight_number to ICAO: {flight_number}"
    return CallToolResult(content=[TextContent(type="text", text=text)], isError=not result)


def main():
    mcp.run(transport="stdio")


app = mcp.streamable_http_app()
