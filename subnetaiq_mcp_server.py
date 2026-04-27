"""SubnetAIQ MCP Server — Bittensor intelligence inside Claude Code

Install:
  claude mcp add subnetaiq -- python3 /path/to/subnetaiq_mcp_server.py

Then in any Claude Code session:
  "What's the momentum for SN64?"
  "Which subnets are bullish right now?"
  "Where is institutional money flowing in Bittensor?"
"""

import json
import sys
import urllib.request

API_BASE = "https://subnetaiq.io/api/v1"


def _api(endpoint, params=None):
    url = f"{API_BASE}/{endpoint}"
    if params:
        url += "?" + "&".join(f"{k}={v}" for k, v in params.items())
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "SubnetAIQ-MCP/1.0"})
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode())
    except Exception as e:
        return {"error": str(e)}


# MCP Protocol: read JSON-RPC from stdin, write to stdout
def handle_request(request):
    method = request.get("method", "")
    params = request.get("params", {})

    if method == "initialize":
        return {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {
                "name": "SubnetAIQ",
                "version": "1.0.0",
            },
        }

    elif method == "tools/list":
        return {
            "tools": [
                {
                    "name": "subnetaiq_subnet",
                    "description": "Get details for a specific Bittensor subnet — price, liquidity, emission, momentum. Use this when asked about any subnet by number.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "netuid": {"type": "integer", "description": "Subnet ID (1-128)"}
                        },
                        "required": ["netuid"],
                    },
                },
                {
                    "name": "subnetaiq_momentum",
                    "description": "Get momentum scores for all 128 Bittensor subnets. Scores range from -100 (bearish) to +100 (bullish). Use this to find trending subnets.",
                    "inputSchema": {"type": "object", "properties": {}},
                },
                {
                    "name": "subnetaiq_top_subnets",
                    "description": "Get top Bittensor subnets ranked by liquidity, emission, or price.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "limit": {"type": "integer", "description": "Number of results (default 10)", "default": 10},
                            "sort_by": {"type": "string", "description": "Sort by: liquidity, emission, or price", "default": "liquidity"},
                        },
                    },
                },
                {
                    "name": "subnetaiq_whale_flows",
                    "description": "Get whale and institutional money movements in Bittensor. Tracks Grayscale, Polychain, DCG, Kraken, and 15+ validators.",
                    "inputSchema": {"type": "object", "properties": {}},
                },
                {
                    "name": "subnetaiq_institutional",
                    "description": "Track institutional players in Bittensor — who's staking, where, how much. Covers ETF filers, VC funds, exchanges.",
                    "inputSchema": {"type": "object", "properties": {}},
                },
                {
                    "name": "subnetaiq_mining_directory",
                    "description": "Find which Bittensor subnets to mine. Includes hardware requirements, difficulty rating, and setup steps.",
                    "inputSchema": {"type": "object", "properties": {}},
                },
            ]
        }

    elif method == "tools/call":
        tool_name = params.get("name", "")
        args = params.get("arguments", {})

        if tool_name == "subnetaiq_subnet":
            data = _api(f"subnet/{args.get('netuid', 1)}")
        elif tool_name == "subnetaiq_momentum":
            data = _api("momentum")
            # Trim to top/bottom 10 to keep response manageable
            subnets = data.get("subnets", [])
            data["subnets"] = subnets[:10]
            data["bottom_10"] = subnets[-10:] if len(subnets) > 10 else []
            data["total_scored"] = len(subnets)
        elif tool_name == "subnetaiq_top_subnets":
            data = _api("top-subnets", {
                "limit": args.get("limit", 10),
                "sort_by": args.get("sort_by", "liquidity"),
            })
        elif tool_name == "subnetaiq_whale_flows":
            data = _api("whale-flows")
        elif tool_name == "subnetaiq_institutional":
            data = _api("institutional")
        elif tool_name == "subnetaiq_mining_directory":
            data = _api("mining-directory")
        else:
            data = {"error": f"Unknown tool: {tool_name}"}

        return {
            "content": [
                {"type": "text", "text": json.dumps(data, indent=2)}
            ]
        }

    elif method == "notifications/initialized":
        return None  # No response needed

    return {"error": {"code": -32601, "message": f"Method not found: {method}"}}


def main():
    """Run MCP server on stdin/stdout."""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
            result = handle_request(request)
            if result is not None:
                response = {
                    "jsonrpc": "2.0",
                    "id": request.get("id"),
                    "result": result,
                }
                sys.stdout.write(json.dumps(response) + "\n")
                sys.stdout.flush()
        except Exception as e:
            error_resp = {
                "jsonrpc": "2.0",
                "id": request.get("id") if 'request' in dir() else None,
                "error": {"code": -32603, "message": str(e)},
            }
            sys.stdout.write(json.dumps(error_resp) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
