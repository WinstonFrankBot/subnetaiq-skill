"""SubnetAIQ Deploy Skill — SN2 dsperse
Executable mining skill. Agent runs this → miner deployed → earning TAO.

What it does:
1. Checks hardware compatibility
2. Downloads binary from GitHub releases (not pip install)
3. Sets up working directory
4. Creates hotkey
5. Registers on-chain
6. Configures environment
7. Starts miner via PM2

Usage:
  python sn2_dsperse.py deploy --wallet finflow_miner --machine beast
  python sn2_dsperse.py status
  python sn2_dsperse.py stop

Requirements:
  - GPU with 8GB+ VRAM
  - Bittensor wallet with TAO for registration
  - PM2 installed
"""

import argparse
import json
import os
import subprocess
import sys
import time


# ─── CONFIG ──────────────────────────────────────────────────────────────

SUBNET = {
    "netuid": 2,
    "name": "dsperse",
    "repo": "https://github.com/inference-labs-inc/subnet-2.git",
    "repo_dir": "subnet-2",
    "github": "inference-labs-inc/subnet-2",
    "min_vram_gb": 8,
    "python_version": "3.10",
    "difficulty": "Hard",
    "type": "ZK Proof Generation",
    "burn_estimate_tao": 0.07,
    "axon_port": 8091,
}


# ─── HELPERS ─────────────────────────────────────────────────────────────

def run(cmd, cwd=None, timeout=120, check=True):
    """Run a shell command and return output."""
    print(f"  $ {cmd}")
    try:
        r = subprocess.run(
            cmd, shell=True, cwd=cwd, capture_output=True, text=True, timeout=timeout
        )
        if check and r.returncode != 0:
            print(f"  ERROR: {r.stderr[:200]}")
            return None
        return r.stdout.strip()
    except subprocess.TimeoutExpired:
        print(f"  TIMEOUT after {timeout}s")
        return None


def check_gpu():
    """Check GPU compatibility."""
    print("\n[1/7] Checking GPU...")
    result = run("nvidia-smi --query-gpu=name,memory.total --format=csv,noheader,nounits", check=False)
    if not result:
        print("  No NVIDIA GPU found. SN2 needs GPU with 8GB+ VRAM.")
        return False
    name, vram = result.split(", ")
    vram_gb = int(vram) / 1024
    print(f"  GPU: {name} ({vram_gb:.0f}GB VRAM)")
    if vram_gb < SUBNET["min_vram_gb"]:
        print(f"  FAIL: Need {SUBNET['min_vram_gb']}GB+, you have {vram_gb:.0f}GB")
        return False
    print(f"  PASS: {vram_gb:.0f}GB >= {SUBNET['min_vram_gb']}GB required")
    return True


def clone_repo(home_dir):
    """Download the sn2-miner binary from GitHub releases."""
    print("\n[2/7] Downloading sn2-miner binary...")
    repo_path = os.path.join(home_dir, SUBNET["repo_dir"])
    os.makedirs(repo_path, exist_ok=True)

    binary_path = os.path.join(repo_path, "sn2-miner")
    if os.path.exists(binary_path):
        print(f"  Binary already exists: {binary_path}")
        return repo_path

    # Also clone repo for reference configs
    if not os.path.exists(os.path.join(repo_path, ".git")):
        run(f"git clone {SUBNET['repo']} {repo_path}", check=False)

    # Download latest binary from GitHub releases
    print("  Fetching latest release binary...")
    result = run(
        f"curl -sL https://api.github.com/repos/{SUBNET['github']}/releases/latest "
        f"| python3 -c \"import sys,json; r=json.load(sys.stdin); "
        f"assets=[a for a in r.get('assets',[]) if 'miner' in a['name'].lower() and 'linux' in a['name'].lower()]; "
        f"print(assets[0]['browser_download_url'] if assets else '')\"",
        check=False
    )

    if result:
        run(f"curl -sL -o {binary_path} '{result}'", check=False)
        run(f"chmod +x {binary_path}", check=False)
        if os.path.exists(binary_path):
            print(f"  Downloaded binary: {binary_path}")
            return repo_path

    print("  WARNING: Could not auto-download binary.")
    print(f"  Manual: Go to https://github.com/{SUBNET['github']}/releases")
    print(f"  Download the sn2-miner binary for your platform to {binary_path}")
    return repo_path


def setup_venv(repo_path):
    """No venv needed — binary miner. Just verify binary exists."""
    print("\n[3/7] Verifying binary...")
    binary_path = os.path.join(repo_path, "sn2-miner")
    if os.path.exists(binary_path):
        result = run(f"file {binary_path}", check=False)
        if result:
            print(f"  Binary: {result}")
        return True
    print("  FAIL: sn2-miner binary not found")
    print(f"  Download from: https://github.com/{SUBNET['github']}/releases")
    return False


def create_hotkey(wallet_name, hotkey_name):
    """Create a new hotkey if it doesn't exist."""
    print("\n[4/7] Setting up wallet...")
    hotkey_path = os.path.expanduser(f"~/.bittensor/wallets/{wallet_name}/hotkeys/{hotkey_name}")
    if os.path.exists(hotkey_path):
        print(f"  Hotkey {hotkey_name} already exists")
        result = run(f"python3 -c \"import json; print(json.load(open('{hotkey_path}'))['ss58Address'])\"", check=False)
        if result:
            print(f"  Address: {result}")
        return True

    btcli = None
    for path in [
        os.path.expanduser("~/synth-subnet/.venv/bin/btcli"),
        os.path.expanduser("~/subnet-72/.venv/bin/btcli"),
    ]:
        if os.path.exists(path):
            btcli = path
            break

    if not btcli:
        print("  FAIL: btcli not found. Install bittensor first.")
        return False

    result = run(f"echo | {btcli} wallet new_hotkey --wallet.name {wallet_name} --wallet.hotkey {hotkey_name}", check=False)
    if os.path.exists(hotkey_path):
        print(f"  Created hotkey: {hotkey_name}")
        return True
    print("  FAIL: Could not create hotkey")
    return False


def register(wallet_name, hotkey_name):
    """Register on SN2. Requires wallet password."""
    print(f"\n[5/7] Registering on SN{SUBNET['netuid']}...")
    print(f"  Estimated burn: ~{SUBNET['burn_estimate_tao']} TAO")

    check = run(f"python3 -c \"\nimport bittensor as bt, json, os\nsub = bt.Subtensor('finney')\nmg = sub.metagraph({SUBNET['netuid']})\nhk_path = os.path.expanduser('~/.bittensor/wallets/{wallet_name}/hotkeys/{hotkey_name}')\nss58 = json.load(open(hk_path))['ss58Address']\nif ss58 in mg.hotkeys:\n    print(f'REGISTERED UID {{mg.hotkeys.index(ss58)}}')\nelse:\n    print('NOT_REGISTERED')\nsub.substrate.close()\n\"", check=False)

    if check and "REGISTERED" in check and "NOT" not in check:
        print(f"  Already registered: {check}")
        return True

    print("  *** REQUIRES YOUR WALLET PASSWORD ***")
    print(f"  Run this command manually:")
    btcli = os.path.expanduser("~/synth-subnet/.venv/bin/btcli")
    print(f"  {btcli} subnet recycle_register --netuid {SUBNET['netuid']} --wallet.name {wallet_name} --wallet.hotkey {hotkey_name} --subtensor.network finney")
    return "MANUAL"


def configure(repo_path, wallet_name, hotkey_name):
    """Configure the miner environment."""
    print("\n[6/7] Configuring miner...")
    env_file = os.path.join(repo_path, "miner.env")
    config = f"""# SN2 dsperse — Auto-configured by SubnetAIQ Deploy Skill
WALLET_NAME={wallet_name}
WALLET_HOTKEY={hotkey_name}
NETUID={SUBNET['netuid']}
SUBTENSOR_NETWORK=finney
SUBTENSOR_CHAIN_ENDPOINT=wss://entrypoint-finney.opentensor.ai:443
AXON_PORT={SUBNET['axon_port']}
# ZK Proof Generation settings
DEVICE=cuda
"""
    with open(env_file, "w") as f:
        f.write(config)
    print(f"  Config written: {env_file}")
    return True


def start_miner(repo_path, wallet_name, hotkey_name):
    """Start the miner via PM2."""
    print("\n[7/7] Starting miner...")
    binary = os.path.join(repo_path, "sn2-miner")
    miner_name = f"sn{SUBNET['netuid']}-dsperse"

    result = run(f"pm2 list | grep {miner_name}", check=False)
    if result and "online" in result:
        print(f"  Already running: {miner_name}")
        return True

    cmd = (
        f"pm2 start {binary} --name {miner_name} "
        f"--cwd {repo_path} -- "
        f"--wallet.name {wallet_name} --wallet.hotkey {hotkey_name} "
        f"--netuid {SUBNET['netuid']} --subtensor.network finney "
        f"--axon.port {SUBNET['axon_port']} "
        f"--axon.external_ip 100.38.4.25 --axon.external_port {SUBNET['axon_port']}"
    )
    run(cmd, check=False)
    time.sleep(10)

    result = run(f"pm2 list | grep {miner_name}", check=False)
    if result and "online" in result:
        print(f"  Miner RUNNING: {miner_name}")
        run("pm2 save", check=False)
        return True
    print(f"  WARNING: Miner may not be running. Check: pm2 logs {miner_name}")
    return False


def check_status():
    """Check miner status and earnings."""
    miner_name = f"sn{SUBNET['netuid']}-dsperse"
    print(f"\n=== SN{SUBNET['netuid']} {SUBNET['name']} Status ===")

    result = run(f"pm2 list | grep {miner_name}", check=False)
    if result:
        print(f"  PM2: {result.strip()}")
    else:
        print("  PM2: NOT RUNNING")
        return

    run(f"python3 -c \"\nimport bittensor as bt\nsub = bt.Subtensor('finney')\nmg = sub.metagraph({SUBNET['netuid']})\nfor uid in range(mg.n):\n    if mg.axons[uid].port == {SUBNET['axon_port']}:\n        print(f'UID {{uid}}: inc={{float(mg.incentive[uid]):.6f}} serving={{mg.axons[uid].is_serving}}')\n        break\nsub.substrate.close()\n\"", check=False)


def deploy(wallet_name, hotkey_name):
    """Full deployment pipeline."""
    print(f"{'='*60}")
    print(f"  SubnetAIQ Deploy Skill — SN{SUBNET['netuid']} {SUBNET['name']}")
    print(f"  Type: {SUBNET['type']}")
    print(f"  Difficulty: {SUBNET['difficulty']}")
    print(f"  Burn: ~{SUBNET['burn_estimate_tao']} TAO")
    print(f"  NOTE: Binary miner (not Python). Downloads from GitHub releases.")
    print(f"{'='*60}")

    home = os.path.expanduser("~")

    if not check_gpu():
        print("\nDEPLOY FAILED: GPU requirements not met.")
        return False

    repo_path = clone_repo(home)
    if not repo_path:
        print("\nDEPLOY FAILED: Could not download binary.")
        return False

    if not setup_venv(repo_path):
        print("\nDEPLOY FAILED: Binary not found.")
        return False

    if not create_hotkey(wallet_name, hotkey_name):
        print("\nDEPLOY FAILED: Could not create hotkey.")
        return False

    reg_result = register(wallet_name, hotkey_name)
    if reg_result == "MANUAL":
        print("\n!! PAUSED: Run the registration command above, then re-run this script.")
        return False
    if not reg_result:
        print("\nDEPLOY FAILED: Registration failed.")
        return False

    if not configure(repo_path, wallet_name, hotkey_name):
        print("\nDEPLOY FAILED: Configuration failed.")
        return False

    if not start_miner(repo_path, wallet_name, hotkey_name):
        print("\nDEPLOY WARNING: Miner may not have started. Check PM2 logs.")
        return False

    print(f"\n{'='*60}")
    print(f"  SN{SUBNET['netuid']} {SUBNET['name']} DEPLOYED")
    print(f"  Miner: sn{SUBNET['netuid']}-dsperse")
    print(f"  Port: {SUBNET['axon_port']}")
    print(f"  Check: python3 {__file__} status")
    print(f"{'='*60}")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f"SubnetAIQ Deploy Skill — SN{SUBNET['netuid']} {SUBNET['name']}")
    parser.add_argument("action", choices=["deploy", "status", "stop"], help="Action to perform")
    parser.add_argument("--wallet", default="finflow_miner", help="Wallet name")
    parser.add_argument("--hotkey", default=f"sn{SUBNET['netuid']}_01", help="Hotkey name")
    args = parser.parse_args()

    if args.action == "deploy":
        deploy(args.wallet, args.hotkey)
    elif args.action == "status":
        check_status()
    elif args.action == "stop":
        run(f"pm2 stop sn{SUBNET['netuid']}-dsperse", check=False)
        print("Miner stopped.")
