# SubnetAIQ — OpenClaw Skill

## What is this?
The SubnetAIQ skill gives your AI agent instant access to Bittensor intelligence — momentum scores, whale flows, mining opportunities, and institutional tracking across all 128 subnets.

## Install
Add this skill to your OpenClaw agent:
```
numi skills install subnetaiq
```
Or manually add to your agent's skill directory.

## What your agent can do with this skill

### 1. Check any subnet
"What's the current price and momentum for SN64 Chutes?"
→ Queries `/api/v1/subnet/64`

### 2. Find the best subnets to stake
"Which subnets have the highest momentum right now?"
→ Queries `/api/v1/momentum`

### 3. Track institutional money
"Where are Grayscale and Polychain staking?"
→ Queries `/api/v1/institutional`

### 4. Find mining opportunities
"What subnets can I mine with an RTX 5090?"
→ Queries `/api/v1/mining-directory`

### 5. Monitor whale movements
"Have any whales moved TAO in the last 24 hours?"
→ Queries `/api/v1/whale-flows`

### 6. Get top subnets by any metric
"Top 10 subnets by daily emission"
→ Queries `/api/v1/top-subnets?limit=10&sort_by=emission`

## API Base URL
```
https://subnetaiq.io/api/v1
```

## Pricing
- **Free tier**: All endpoints, 10 queries/minute
- **Pro** ($4.99/mo): Unlimited queries + full whale data + email alerts
- **Institutional** ($24.99/mo): Everything + raw API access + priority support

## About SubnetAIQ
The only institutional-grade research platform for Bittensor subnets. 128 subnets tracked. 15 institutional players monitored. Real-time momentum scoring.

Built by miners, for miners.
