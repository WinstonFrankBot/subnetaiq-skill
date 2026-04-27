"""SubnetAIQ OpenClaw Skill — Bittensor Intelligence for AI Agents

Install this skill to give your agent access to:
- Real-time data on all 128 Bittensor subnets
- Momentum scores (proprietary SubnetAIQ scoring)
- Institutional flow tracking (Grayscale, Polychain, DCG, Kraken)
- Mining directory (what to mine, hardware requirements)
- Whale movement alerts

API Base: https://subnetaiq.io/api/v1
"""

import json
import urllib.request

API_BASE = "https://subnetaiq.io/api/v1"


def _get(endpoint: str, params: dict = None) -> dict:
    """Query the SubnetAIQ API."""
    url = f"{API_BASE}/{endpoint}"
    if params:
        qs = "&".join(f"{k}={v}" for k, v in params.items())
        url += f"?{qs}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "SubnetAIQ-Skill/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        return {"error": str(e)}


# ── Agent-callable functions ──────────────────────────────────────────────


def get_subnet(netuid: int) -> dict:
    """Get details for a specific subnet — price, liquidity, emission, momentum.

    Args:
        netuid: The subnet ID (1-128)

    Returns:
        dict with name, price, tao_in (liquidity), daily_emission, price_changes
    """
    return _get(f"subnet/{netuid}")


def get_all_subnets() -> dict:
    """Get all 128 subnets with live data.

    Returns:
        dict with timestamp, block, subnet_count, total_tao_locked, subnets list
    """
    return _get("subnets")


def get_momentum_scores() -> dict:
    """Get SubnetAIQ proprietary momentum scores for all subnets.
    Scores range from -100 (extreme bearish) to +100 (extreme bullish).
    Based on 1h, 24h, 7d, and 30d price movements weighted by recency.

    Returns:
        dict with subnets list sorted by momentum_score (highest first)
    """
    return _get("momentum")


def get_top_subnets(limit: int = 10, sort_by: str = "liquidity") -> dict:
    """Get top subnets ranked by a metric.

    Args:
        limit: Number of subnets to return (default 10)
        sort_by: 'liquidity', 'emission', or 'price'

    Returns:
        dict with sorted subnets list
    """
    return _get("top-subnets", {"limit": limit, "sort_by": sort_by})


def get_whale_flows() -> dict:
    """Get recent whale and institutional movements.
    Tracks Grayscale, Polychain, DCG/Yuma, Kraken, and 15+ named validators.

    Returns:
        dict with alerts_30d (recent alerts) and movements_24h
    """
    return _get("whale-flows")


def get_mining_directory() -> dict:
    """Get the mining directory — which subnets to mine and how.
    Includes hardware requirements, difficulty rating, setup steps.

    Returns:
        dict with subnets list containing mining info
    """
    return _get("mining-directory")


def get_institutional_players() -> dict:
    """Track institutional players in the Bittensor ecosystem.
    Monitors Grayscale, Bitwise, Polychain, DCG, Stillmark, Pantera, Kraken.

    Returns:
        dict with tracked count, pending count, and institutions list
    """
    return _get("institutional")


def check_health() -> dict:
    """Check if SubnetAIQ API is online and get capability summary.

    Returns:
        dict with status, platform version, block height, endpoints list
    """
    return _get("health")


# ── Convenience functions for common agent tasks ──────────────────────────


def find_best_mining_opportunity(gpu_vram_gb: int = 32) -> list:
    """Find the best subnets to mine based on your GPU.

    Args:
        gpu_vram_gb: Your GPU VRAM in GB (e.g., 32 for RTX 5090)

    Returns:
        list of suitable subnets sorted by opportunity
    """
    directory = get_mining_directory()
    if "error" in directory:
        return []

    suitable = []
    for sn in directory.get("subnets", []):
        hw = sn.get("hardware", "")
        # Check VRAM requirement
        if "None" in hw or "CPU" in hw:
            suitable.append(sn)  # No GPU needed
        elif f"{gpu_vram_gb}GB" in hw or "4GB" in hw or "8GB" in hw or "16GB" in hw:
            suitable.append(sn)
        elif gpu_vram_gb >= 16 and "16GB" in hw:
            suitable.append(sn)
        elif gpu_vram_gb >= 32:
            suitable.append(sn)  # 32GB can run anything

    return suitable


def get_bullish_subnets(min_score: float = 10.0) -> list:
    """Get subnets with strong positive momentum.

    Args:
        min_score: Minimum momentum score (default 10.0)

    Returns:
        list of subnets above the threshold
    """
    data = get_momentum_scores()
    if "error" in data:
        return []
    return [s for s in data.get("subnets", []) if s.get("momentum_score", 0) >= min_score]


def get_bearish_subnets(max_score: float = -10.0) -> list:
    """Get subnets with strong negative momentum.

    Args:
        max_score: Maximum momentum score (default -10.0)

    Returns:
        list of subnets below the threshold
    """
    data = get_momentum_scores()
    if "error" in data:
        return []
    return [s for s in data.get("subnets", []) if s.get("momentum_score", 0) <= max_score]


# ── Skill metadata ────────────────────────────────────────────────────────

SKILL_INFO = {
    "name": "SubnetAIQ",
    "version": "1.0.0",
    "description": "Bittensor intelligence — momentum scores, whale flows, mining opportunities, and institutional tracking for all 128 subnets.",
    "author": "SubnetAIQ / Winston",
    "url": "https://subnetaiq.io",
    "api_base": API_BASE,
    "capabilities": [
        "subnet_analysis",
        "momentum_scoring",
        "whale_tracking",
        "institutional_flows",
        "mining_directory",
    ],
    "functions": [
        "get_subnet", "get_all_subnets", "get_momentum_scores",
        "get_top_subnets", "get_whale_flows", "get_mining_directory",
        "get_institutional_players", "check_health",
        "find_best_mining_opportunity", "get_bullish_subnets", "get_bearish_subnets",
    ],
}


if __name__ == "__main__":
    # Quick test
    print("SubnetAIQ Skill Test")
    print("=" * 40)
    health = check_health()
    print(f"Status: {health.get('status')}")
    print(f"Block: {health.get('block')}")
    print(f"Subnets: {health.get('subnets_tracked')}")
    print(f"Institutions: {health.get('institutional_tracked')}")
    print()

    top = get_top_subnets(5, "emission")
    print("Top 5 by emission:")
    for s in top.get("subnets", []):
        print(f"  SN{s['netuid']} {s['name']}: {s['daily_emission']:.2f}/day")
    print()

    bullish = get_bullish_subnets(15.0)
    print(f"Bullish subnets (momentum > 15): {len(bullish)}")
    for s in bullish[:5]:
        print(f"  SN{s['netuid']}: {s['momentum_score']:.1f}")
