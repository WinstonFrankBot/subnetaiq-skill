# SubnetAIQ — Bittensor Intelligence for AI Agents

**The ONLY open, agent-friendly API for Bittensor (TAO) subnet analytics.**

Real-time data for all 128 Bittensor subnets. Momentum scores, institutional flow tracking, mining directory, whale alerts.

## Install

### OpenClaw Skill (Python)
```python
from subnetaiq_skill import get_momentum_scores, get_bullish_subnets, find_best_mining_opportunity

# Which subnets are trending?
bullish = get_bullish_subnets(min_score=15)

# What should I mine with my GPU?
opportunities = find_best_mining_opportunity(gpu_vram_gb=32)

# Where is institutional money flowing?
from subnetaiq_skill import get_institutional_players
institutions = get_institutional_players()
```

### MCP Server (Claude Code)
```bash
claude mcp add subnetaiq -- python3 subnetaiq_mcp_server.py
```
Then ask: "What's the momentum for SN64?" or "Where is Polychain staking?"

### Direct API
```bash
curl https://subnetaiq.io/api/v1/health
curl https://subnetaiq.io/api/v1/momentum
curl https://subnetaiq.io/api/v1/subnet/64
curl https://subnetaiq.io/api/v1/institutional
```

## Discovery

| Method | URL |
|--------|-----|
| OpenAPI Spec | `subnetaiq.io/openapi.json` |
| AI Plugin | `subnetaiq.io/.well-known/ai-plugin.json` |
| MCP Server | This repo: `subnetaiq_mcp_server.py` |
| Python Skill | This repo: `subnetaiq_skill.py` |

## Endpoints

| Endpoint | Description |
|----------|-------------|
| `/api/v1/subnets` | All 128 subnets — price, liquidity, emissions |
| `/api/v1/subnet/{id}` | Single subnet with momentum data |
| `/api/v1/momentum` | Proprietary momentum scores (-100 to +100) |
| `/api/v1/top-subnets` | Ranked by liquidity, emission, or price |
| `/api/v1/whale-flows` | Institutional + whale movements |
| `/api/v1/institutional` | 15+ named institutional players |
| `/api/v1/mining-directory` | Mining guide with hardware requirements |
| `/api/v1/pricing` | API tier pricing |
| `/api/v1/health` | Status check |

## What We Track

- **128 Bittensor subnets** — live price, liquidity, daily emissions
- **15+ institutional players** — Polychain, DCG/Yuma, Grayscale, Bitwise, Kraken, Stillmark, OTF
- **Momentum scoring** — proprietary algorithm (-100 to +100)
- **Mining directory** — 13 subnets with hardware requirements, difficulty, setup steps
- **Whale movements** — large position changes + new entries/exits

## Free Tier

10 queries/minute. No auth required. All endpoints accessible.

## Built by SubnetAIQ

[subnetaiq.io](https://subnetaiq.io) — The intelligence layer for Bittensor.
