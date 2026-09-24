# agent-routing-mcp

A small MCP server for routing software-engineering work to the lowest sufficient execution model.

The public MCP surface is intentionally minimal: one tool, `route_model`.

The core does not depend on a specific typed-decision model. Decision backends implement a `DecisionProvider` interface, and route-to-model mappings live in external configuration.

## Architecture

```
coding agent
    |
    v
route_model
    |
    v
ModelRouter
    |
    v
DecisionProvider
    |
    +-- systemone_http
    +-- future providers
    |
    v
LOW | MEDIUM | HIGH | ESCALATE
    |
    v
routing configuration
    |
    v
model + reasoning effort
```

## Current status

Initial MVP:

- MCP stdio server
- one tool: `route_model`
- provider abstraction
- System-One-compatible HTTP provider
- configurable route targets
- ambiguity reporting
- unit tests for routing behavior

## Requirements

- Python 3.10+
- an MCP-compatible host
- a configured typed-decision HTTP service

The MCP implementation targets the current stable v2 line of the official Python MCP SDK.

## Quick start

```bash
git clone https://github.com/JotavioS/agent-routing-mcp.git
cd agent-routing-mcp

python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"

cp config.example.json routing.json
export AGENT_ROUTING_CONFIG="$PWD/routing.json"

.venv/bin/agent-routing-mcp
```

For development with MCP Inspector:

```bash
.venv/bin/mcp dev src/agent_routing_mcp/server.py
```

## Configuration

`config.example.json` contains both the decision-provider connection and route-to-model mapping.

The decision provider returns only an abstract route:

- `LOW`
- `MEDIUM`
- `HIGH`
- `ESCALATE`

The router then resolves that route to the configured model and reasoning effort. This keeps the MCP contract stable when providers or execution models change.

## Codex

After installation, register the stdio server with Codex using the executable created by the package and pass `AGENT_ROUTING_CONFIG` in the MCP server environment.

Verify registration with:

```bash
codex mcp list
```

The global/project `AGENTS.md` only needs to instruct the agent to call `route_model` before delegating substantial implementation work. It does not need to know the provider endpoint or typed-decision request format.

## Design principles

- One stable public routing tool.
- No provider-specific terminology in the public MCP contract.
- Typed decisions are bounded classification, not code generation.
- Deterministic evidence remains outside the decision model.
- Model mappings are configuration, not code.
- Low confidence is surfaced instead of hidden.


### Tested Codex configuration

A working Codex configuration for a local stdio installation is:

```toml
[mcp_servers.route-model]
command = "/absolute/path/to/agent-routing-mcp/.venv/bin/agent-routing-mcp"
default_tools_approval_mode = "approve"
enabled_tools = ["route_model"]

[mcp_servers.route-model.env]
AGENT_ROUTING_CONFIG = "/absolute/path/to/routing.json"
```

`enabled_tools` deliberately keeps the public surface restricted to `route_model`.

For non-interactive Codex runs, `default_tools_approval_mode = "approve"` allows this bounded read-only routing tool to execute without stopping for an interactive MCP approval prompt.

Validated with Codex CLI 0.156.1 and MCP SDK 2.2.0.
