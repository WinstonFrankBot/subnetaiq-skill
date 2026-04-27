"""SubnetAIQ Mineability Engine — Should you mine this subnet?

Scores every Bittensor subnet on actual mineability (0-100) based on
on-chain data, not vibes. Tells agents which subnets are worth deploying
to BEFORE they burn TAO to register.

Metrics:
  - earning_ratio: % of miners with nonzero incentive
  - concentration: how spread out incentive is (Gini coefficient)
  - emission_value: daily TAO emission to the subnet
  - reg_cost: registration burn in TAO
  - verdict: MINE / CAUTION / AVOID

Usage:
  from subnetaiq_mineability import score_subnet, score_all_subnets, get_mineability_report

API endpoint: /api/v1/mineability
"""

import json
import time
import traceback
from datetime import datetime, timezone

# Cache results for 10 minutes
_cache = {}
_cache_ttl = 600


def _gini(values):
    """Calculate Gini coefficient (0 = perfect equality, 1 = one entity has everything)."""
    if not values or len(values) == 0:
        return 1.0
    values = sorted(values)
    n = len(values)
    if n == 1:
        return 0.0
    total = sum(values)
    if total == 0:
        return 1.0
    cumsum = 0
    gini_sum = 0
    for i, v in enumerate(values):
        cumsum += v
        gini_sum += (2 * (i + 1) - n - 1) * v
    return gini_sum / (n * total)


def score_subnet(netuid, subtensor=None, metagraph=None):
    """Score a single subnet's mineability.

    Returns dict with:
      - netuid, name
      - earning_ratio: fraction of miners with incentive > 0
      - earning_count: number of miners earning
      - total_miners: total registered miners
      - gini: incentive concentration (0=equal, 1=monopoly)
      - top1_share: % of incentive held by top earner
      - top5_share: % of incentive held by top 5
      - emission_per_day: estimated daily TAO emission
      - reg_cost: registration burn in TAO (if available)
      - score: 0-100 mineability score
      - verdict: MINE / CAUTION / AVOID
      - reason: human-readable explanation
    """
    import bittensor as bt

    close_sub = False
    if subtensor is None:
        subtensor = bt.Subtensor("finney")
        close_sub = True

    try:
        if metagraph is None:
            mg = subtensor.metagraph(netuid)
        else:
            mg = metagraph

        n = mg.n
        if n == 0:
            return _empty_result(netuid, "No miners registered")

        # Incentive distribution
        incentives = [float(mg.incentive[uid]) for uid in range(n)]
        earning = [i for i in incentives if i > 0]
        earning_count = len(earning)
        earning_ratio = earning_count / n if n > 0 else 0

        # Concentration metrics
        gini = _gini(incentives)
        sorted_inc = sorted(incentives, reverse=True)
        total_inc = sum(sorted_inc)
        top1_share = sorted_inc[0] / total_inc if total_inc > 0 else 1.0
        top5_share = sum(sorted_inc[:5]) / total_inc if total_inc > 0 else 1.0

        # Emission estimate (subnet emission per day)
        try:
            emission_per_day = float(sum(mg.emission)) * 7200 / 1e9  # blocks per day / rao conversion
        except:
            emission_per_day = 0

        # Registration cost
        try:
            reg_cost = float(subtensor.burn(netuid)) / 1e9
        except:
            reg_cost = 0

        # --- SCORING ---
        score = 0
        reasons = []

        # 1. Earning ratio (0-35 points)
        #    >80% earning = 35pts, >50% = 25pts, >20% = 15pts, >5% = 5pts
        if earning_ratio > 0.80:
            score += 35
        elif earning_ratio > 0.50:
            score += 25
        elif earning_ratio > 0.20:
            score += 15
        elif earning_ratio > 0.05:
            score += 5
        else:
            reasons.append(f"Only {earning_ratio*100:.0f}% of miners earn")

        # 2. Concentration / fairness (0-25 points)
        #    Low gini = fair distribution = good for new miners
        if gini < 0.5:
            score += 25
        elif gini < 0.7:
            score += 15
        elif gini < 0.85:
            score += 8
        else:
            reasons.append(f"Top miner takes {top1_share*100:.0f}% of incentive")

        # 3. Top1 share penalty
        #    If one miner has >50% of incentive, it's a monopoly
        if top1_share > 0.90:
            score -= 20
            reasons.append("Single miner monopoly (>90%)")
        elif top1_share > 0.50:
            score -= 10
            reasons.append(f"Top miner dominates ({top1_share*100:.0f}%)")

        # 4. Network size (0-15 points)
        #    More miners = more competitive but also more legitimate
        if n >= 200:
            score += 15
        elif n >= 100:
            score += 12
        elif n >= 50:
            score += 8
        elif n >= 10:
            score += 5
        else:
            reasons.append(f"Very small subnet ({n} miners)")

        # 5. Emission value (0-15 points)
        if emission_per_day > 100:
            score += 15
        elif emission_per_day > 50:
            score += 12
        elif emission_per_day > 10:
            score += 8
        elif emission_per_day > 1:
            score += 4
        else:
            reasons.append("Low emission")

        # 6. Registration cost penalty (0-10 points)
        if reg_cost < 0.05:
            score += 10
        elif reg_cost < 0.2:
            score += 7
        elif reg_cost < 1.0:
            score += 4
        elif reg_cost < 5.0:
            score += 1
        else:
            reasons.append(f"High registration cost ({reg_cost:.2f} TAO)")

        # Clamp
        score = max(0, min(100, score))

        # Verdict
        if score >= 60:
            verdict = "MINE"
        elif score >= 35:
            verdict = "CAUTION"
        else:
            verdict = "AVOID"

        if not reasons:
            if verdict == "MINE":
                reasons.append("Healthy earning distribution")
            elif verdict == "CAUTION":
                reasons.append("Mixed signals — research before deploying")

        return {
            "netuid": netuid,
            "total_miners": n,
            "earning_count": earning_count,
            "earning_ratio": round(earning_ratio, 4),
            "gini": round(gini, 4),
            "top1_share": round(top1_share, 4),
            "top5_share": round(top5_share, 4),
            "emission_per_day_tao": round(emission_per_day, 2),
            "reg_cost_tao": round(reg_cost, 4),
            "score": score,
            "verdict": verdict,
            "reason": "; ".join(reasons),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    except Exception as e:
        return _empty_result(netuid, f"Error: {str(e)[:80]}")
    finally:
        if close_sub:
            try:
                subtensor.close()
            except:
                pass


def _empty_result(netuid, reason):
    return {
        "netuid": netuid,
        "total_miners": 0,
        "earning_count": 0,
        "earning_ratio": 0,
        "gini": 1.0,
        "top1_share": 1.0,
        "top5_share": 1.0,
        "emission_per_day_tao": 0,
        "reg_cost_tao": 0,
        "score": 0,
        "verdict": "AVOID",
        "reason": reason,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def score_all_subnets(netuids=None):
    """Score multiple subnets. Returns list sorted by score descending.

    Args:
        netuids: list of subnet IDs to score, or None for our deployed subnets
    """
    import bittensor as bt

    if netuids is None:
        # Our deployed subnets
        netuids = [2, 6, 9, 13, 18, 25, 38, 44, 50, 64, 65, 68, 72, 88, 103, 107]

    cache_key = f"all_{','.join(map(str, sorted(netuids)))}"
    if cache_key in _cache and time.time() - _cache[cache_key]["ts"] < _cache_ttl:
        return _cache[cache_key]["data"]

    sub = bt.Subtensor("finney")
    results = []
    for netuid in netuids:
        try:
            result = score_subnet(netuid, subtensor=sub)
            results.append(result)
        except Exception as e:
            results.append(_empty_result(netuid, str(e)[:80]))

    sub.close()
    results.sort(key=lambda x: x["score"], reverse=True)

    _cache[cache_key] = {"ts": time.time(), "data": results}
    return results


def get_mineability_report(netuids=None):
    """Generate a human-readable mineability report."""
    results = score_all_subnets(netuids)

    lines = []
    lines.append("=" * 70)
    lines.append("  SubnetAIQ MINEABILITY REPORT")
    lines.append(f"  {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    lines.append("=" * 70)
    lines.append("")
    lines.append(f"{'SN':<6} {'Score':<7} {'Verdict':<9} {'Earning':<12} {'Top1%':<8} {'Emission':<10} {'Reason'}")
    lines.append("-" * 70)

    mine_count = 0
    for r in results:
        earning_str = f"{r['earning_count']}/{r['total_miners']}"
        line = (
            f"SN{r['netuid']:<4d} "
            f"{r['score']:<7d} "
            f"{r['verdict']:<9s} "
            f"{earning_str:<12s} "
            f"{r['top1_share']*100:<7.0f}% "
            f"{r['emission_per_day_tao']:<10.1f} "
            f"{r['reason'][:40]}"
        )
        lines.append(line)
        if r["verdict"] == "MINE":
            mine_count += 1

    lines.append("")
    lines.append(f"MINE: {mine_count} | CAUTION: {sum(1 for r in results if r['verdict']=='CAUTION')} | AVOID: {sum(1 for r in results if r['verdict']=='AVOID')}")
    lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    print(get_mineability_report())
