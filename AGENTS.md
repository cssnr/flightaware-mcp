# Agents - flightaware-mcp

MCP Server exposing the FlightAware AeroAPI via the Model Context Protocol.

- MCP SDK: https://github.com/modelcontextprotocol/python-sdk
- HTTPX: https://github.com/projectdiscovery/httpx
- Hishel: https://github.com/karpetrosyan/hishel
- AeroAPI: https://www.flightaware.com/commercial/aeroapi/resources/aeroapi-openapi.yml (blocks bots)

These files **may** be available locally, check the local file before fetching remote contents.

| Local File          | Remote URL                                                                           | Notes                                         |
| ------------------- | ------------------------------------------------------------------------------------ | --------------------------------------------- |
| aeroapi-openapi.yml | https://www.flightaware.com/commercial/aeroapi/resources/aeroapi-openapi.yml         | Length: 891,174 - Lines: 19,285               |
| airlines.json       | https://raw.githubusercontent.com/npow/airline-codes/refs/heads/master/airlines.json | Length: 814,610 - Lines: 12,130 - Items: 6064 |

## Commands

This project uses `toml-run` — run any `[tool.scripts]` entry by name:

| Command      | What it does                                 |
| ------------ | -------------------------------------------- |
| `run build`  | hatch build                                  |
| `run cli`    | python -m flightaware_mcp                    |
| `run dev`    | uvicorn w/ --reload                          |
| `run server` | uvicorn w/ --host 0.0.0.0                    |
| `run format` | Full format: should always be used to format |
| `run lint`   | Full lint: should always be used to lint     |

## Important

- `app_lifespan` does not run on server startup, it runs on every client connection...
