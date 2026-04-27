# SubnetAIQ Deploy Skills

**One command. Miner deployed. Earning TAO.**

## What Are Deploy Skills?

Each skill is a self-contained Python script that automates the entire mining setup for a Bittensor subnet. An agent (or human) runs the script and gets a working miner in minutes — not hours.

## Available Skills

| Subnet | Script | Difficulty | Hardware |
|--------|--------|-----------|----------|
| SN2 dSperse | `sn2_dsperse.py` | Hard | GPU 24GB+ |
| SN6 Numinous | `sn6_numinous.py` | Easy | CPU only |
| SN9 IOTA | `sn9_iota.py` | Hard | GPU 24GB+ |
| SN13 Data Universe | `sn13_datauniverse.py` | Easy | CPU only |
| SN18 Zeus | `sn18_zeus.py` | Medium | GPU 4GB+ |
| SN25 Mainframe | `sn25_mainframe.py` | Medium | CPU only |
| SN38 Sylliba | `sn38_sylliba.py` | Medium | CPU/GPU |
| SN44 ScoreVision | `sn44_score.py` | Medium | GPU 4GB+ |
| SN50 Synth | `sn50_synth.py` | Medium | CPU only |
| SN64 Chutes | `sn64_chutes.py` | Hard | GPU + K3s |
| SN65 TPN | `sn65_tpn.py` | Easy | CPU only |
| SN68 Metanova | `sn68_metanova.py` | Hard | CPU/GPU |
| SN72 StreetVision | `sn72_streetvision.py` | Medium | GPU 4GB+ |
| SN88 Investing | `sn88_investing.py` | Easy | CPU only |
| SN103 Djinn | `sn103_djinn.py` | Medium | CPU only |
| SN107 Minos | `sn107_minos.py` | Easy | CPU only |

## Usage

```bash
# Deploy a miner
python sn72_streetvision.py deploy --wallet finflow_miner

# Check status
python sn72_streetvision.py status

# Stop miner
python sn72_streetvision.py stop
```

## What Each Skill Does

1. **Checks hardware** — GPU, VRAM, Python version
2. **Clones repo** — gets latest subnet code
3. **Sets up environment** — venv, dependencies, configs
4. **Creates hotkey** — new wallet key for this subnet
5. **Registers on-chain** — burns TAO to get a slot
6. **Configures miner** — .env, ports, model paths
7. **Starts miner** — via PM2 with auto-restart
8. **Verifies status** — confirms earning on-chain

## Building New Skills

Each skill follows the same 7-step pattern. Copy `sn72_streetvision.py` as a template and update the `SUBNET` config dict for your target subnet.

## Built by SubnetAIQ

[subnetaiq.io](https://subnetaiq.io) — The intelligence layer for Bittensor.
