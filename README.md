# SubnetAIQ — Bittensor Intelligence for AI Agents

**The ONLY open, agent-friendly API for Bittensor (TAO) subnet analytics.**

128 subnets tracked. 100 GitHub repos monitored. 15 institutional players. Proprietary momentum scoring. Free tier.

## Quick Start
```bash
curl https://subnetaiq.io/api/v1/health
```

## What We Track

| Data | Coverage |
|------|----------|
| **Subnets** | All 128, live every 2 min |
| **GitHub Dev Activity** | 100 repos — commit velocity, last commit, active/stale/inactive |
| **Institutional Players** | 15 named validators (Polychain, DCG, Kraken, OTF, Grayscale pending) |
| **Momentum Scoring** | Proprietary -100 to +100 for every subnet |
| **Twitter Sentiment** | 13 subnets via SN13 Data Universe |
| **Mining Skills** | "How to use" + "How to mine" for 14 subnets |
| **Whale Flows** | Large position changes + institutional movements |

## 13 API Endpoints

| Endpoint | Description |
|----------|-------------|
| `/api/v1/health` | Status + capabilities |
| `/api/v1/subnets` | All 128 subnets — price, liquidity, emissions |
| `/api/v1/subnet/{id}` | Single subnet + momentum |
| `/api/v1/momentum` | Proprietary momentum scores |
| `/api/v1/top-subnets` | Ranked by liquidity, emission, or price |
| `/api/v1/whale-flows` | Institutional + whale movements |
| `/api/v1/institutional` | 15+ named institutional players |
| `/api/v1/dev-activity` | 100 GitHub repos — commit velocity |
| `/api/v1/sentiment` | Twitter sentiment for 13 subnets |
| `/api/v1/skills` | Subnet skill directory |
| `/api/v1/skills/{id}` | Per-subnet use + mine instructions |
| `/api/v1/mining-directory` | Hardware requirements + setup |
| `/api/v1/pricing` | Tier pricing for agents |

## Install

### MCP Server (Claude Code)
```bash
claude mcp add subnetaiq -- python3 subnetaiq_mcp_server.py
```

### Python Skill
```python
from subnetaiq_skill import get_momentum_scores, get_bullish_subnets
bullish = get_bullish_subnets(min_score=15)
```

### Direct API
```bash
curl https://subnetaiq.io/api/v1/momentum
curl https://subnetaiq.io/api/v1/dev-activity
curl https://subnetaiq.io/api/v1/institutional
```

## Discovery

| Method | URL |
|--------|-----|
| OpenAPI Spec | `subnetaiq.io/openapi.json` |
| AI Plugin | `subnetaiq.io/.well-known/ai-plugin.json` |
| MCP Server | This repo: `subnetaiq_mcp_server.py` |
| Python Skill | This repo: `subnetaiq_skill.py` |

## Free Tier

10 queries/minute. No auth required. All endpoints.

---

**[subnetaiq.io](https://subnetaiq.io)** — The intelligence layer for Bittensor.

128 subnets · 100 GitHub repos · 15 institutions · 13 endpoints · Free tier
