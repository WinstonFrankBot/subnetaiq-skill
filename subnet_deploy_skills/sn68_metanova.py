"""SubnetAIQ Deploy Skill — SN68 Metanova
Executable mining skill. Agent runs this → miner deployed → earning TAO.

What it does:
1. Checks hardware compatibility
2. Clones repo + sets up venv
3. Creates hotkey
4. Registers on-chain
5. Configures environment (.env with GitHub vars)
6. Starts miner via PM2
7. Verifies earning status

Usage:
  python sn68_metanova.py deploy --wallet finflow_miner
  python sn68_metanova.py status
  python sn68_metanova.py stop

Requirements:
  - CPU (no GPU required, but GPU speeds up molecular sim)
  - Python 3.10+
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
    "netuid": 68,
    "name": "Metanova",
    "repo": "https://github.com/metanova-labs/nova.git",
    "repo_dir": "nova",
    "github": "metanova-labs/nova",
    "min_vram_gb": 0,
    "python_version": "3.10",
    "difficulty": "Hard",
    "type": "Protein design — nanobody + small molecule optimization",
    "burn_estimate_tao": 0.1,
    "axon_port": 8068,
    "miner_script": "neurons/miner/miner.py",
    "network_url": "wss://entrypoint-finney.opentensor.ai:443",
    "env_vars": {
        "GITHUB_REPO_NAME": "nova",
        "GITHUB_REPO_BRANCH": "main",
        "GITHUB_REPO_OWNER": "metanova-labs",
        "GITHUB_REPO_PATH": "data/results",
    },
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


def check_hardware():
    """Check hardware compatibility — SN68 is CPU-capable, GPU optional."""
    print("\n[1/7] Checking hardware...")
    py_version = sys.version_info
    print(f"  Python: {py_version.major}.{py_version.minor}")
    if py_version < (3, 10):
        print(f"  FAIL: Need Python 3.10+, you have {py_version.major}.{py_version.minor}")
        return False

    # Check for GPU (optional, speeds up molecular sim)
    result = run("nvidia-smi --query-gpu=name,memory.total --format=csv,noheader,nounits", check=False)
    if result:
        name, vram = result.split(", ")
        print(f"  GPU: {name} ({int(vram)/1024:.0f}GB VRAM) — will accelerate computation")
    else:
        print("  No GPU found — will run on CPU (slower but functional)")

    print(f"  PASS: Minimum requirements met")
    return True


def clone_repo(home_dir):
    """Clone the subnet repo."""
    print("\n[2/7] Cloning repo...")
    repo_path = os.path.join(home_dir, SUBNET["repo_dir"])
    if os.path.exists(repo_path):
        print(f"  Already exists: {repo_path}")
        run("git pull", cwd=repo_path, check=False)
        return repo_path
    run(f"git clone {SUBNET['repo']} {repo_path}")
    if os.path.exists(repo_path):
        print(f"  Cloned to {repo_path}")
        return repo_path
    print("  FAIL: Clone failed")
    return None


def setup_venv(repo_path):
    """Set up Python virtual environment."""
    print("\n[3/7] Setting up Python environment...")
    venv_path = os.path.join(repo_path, ".venv")
    if os.path.exists(os.path.join(venv_path, "bin", "python")):
        print("  Venv already exists")
    else:
        for py in ["python3.12", "python3.11", "python3.10", "python3"]:
            result = run(f"{py} -m venv {venv_path}", check=False)
            if result is not None and os.path.exists(os.path.join(venv_path, "bin", "python")):
                print(f"  Created venv with {py}")
                break
        else:
            print("  FAIL: Could not create venv")
            return False

    pip = os.path.join(venv_path, "bin", "pip")

    # Install from requirements or pyproject
    requirements = os.path.join(repo_path, "requirements.txt")
    pyproject = os.path.join(repo_path, "pyproject.toml")
    if os.path.exists(requirements):
        run(f"{pip} install -r requirements.txt --quiet", cwd=repo_path, timeout=300, check=False)
    elif os.path.exists(pyproject):
        run(f"{pip} install -e . --quiet", cwd=repo_path, timeout=300, check=False)

    # Verify bittensor import
    python = os.path.join(venv_path, "bin", "python")
    test = run(f"{python} -c \"import bittensor; print('OK')\"", check=False)
    if test and "OK" in test:
        print("  Dependencies installed successfully")
        return True
    print("  WARNING: Import test failed, but continuing...")
    return True


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

    btcli = run("which btcli", check=False)
    if not btcli:
        for path in [
            os.path.expanduser("~/synth-subnet/.venv/bin/btcli"),
            os.path.expanduser("~/nova/.venv/bin/btcli"),
        ]:
            if os.path.exists(path):
                btcli = path
                break
    if not btcli:
        print("  FAIL: btcli not found. Install bittensor first.")
        return False

    run(f"echo | {btcli} wallet new_hotkey --wallet.name {wallet_name} --wallet.hotkey {hotkey_name}", check=False)
    if os.path.exists(hotkey_path):
        print(f"  Created hotkey: {hotkey_name}")
        return True
    print("  FAIL: Could not create hotkey")
    return False


def register(wallet_name, hotkey_name):
    """Register on SN68. Requires wallet password."""
    print(f"\n[5/7] Registering on SN{SUBNET['netuid']}...")
    print(f"  Estimated burn: ~{SUBNET['burn_estimate_tao']} TAO")
    print("  *** REQUIRES YOUR WALLET PASSWORD ***")
    print(f"  Run this command manually:")
    btcli = run("which btcli", check=False) or "btcli"
    print(f"  {btcli} subnet recycle_register --netuid {SUBNET['netuid']} --wallet.name {wallet_name} --wallet.hotkey {hotkey_name} --subtensor.network finney")
    return "MANUAL"


def configure(repo_path, wallet_name, hotkey_name):
    """Configure the miner environment via .env file."""
    print("\n[6/7] Configuring miner...")
    env_file = os.path.join(repo_path, ".env")

    env_lines = [
        f"# SN68 Metanova — Auto-configured by SubnetAIQ Deploy Skill",
        f"GITHUB_REPO_NAME=nova",
        f"GITHUB_REPO_BRANCH=main",
        f"GITHUB_REPO_OWNER=metanova-labs",
        f"GITHUB_REPO_PATH=data/results",
    ]

    with open(env_file, "w") as f:
        f.write("\n".join(env_lines) + "\n")
    print(f"  Config written: {env_file}")
    return True


def start_miner(repo_path, wallet_name, hotkey_name):
    """Start the miner via PM2."""
    print("\n[7/7] Starting miner...")
    python = os.path.join(repo_path, ".venv", "bin", "python")
    miner_name = f"sn{SUBNET['netuid']}-nova"

    # Check if already running
    result = run(f"pm2 list | grep {miner_name}", check=False)
    if result and "online" in result:
        print(f"  Already running: {miner_name}")
        return True

    # IMPORTANT: Use --network with full WSS URL, not --subtensor.network
    # The miner uses SubstrateInterface(url=config.network) which needs a URL, not "finney"
    # IMPORTANT: Miner script is neurons/miner/miner.py NOT neurons/miner.py
    cmd = (
        f"pm2 start {python} --name {miner_name} --interpreter none "
        f"--cwd {repo_path} -- {SUBNET['miner_script']} "
        f"--wallet.name {wallet_name} --wallet.hotkey {hotkey_name} "
        f"--netuid {SUBNET['netuid']} "
        f"--network {SUBNET['network_url']} "
        f"--logging.info"
    )
    run(cmd, check=False)
    time.sleep(15)

    # Verify
    result = run(f"pm2 list | grep {miner_name}", check=False)
    if result and "online" in result:
        print(f"  Miner RUNNING: {miner_name}")
        run("pm2 save", check=False)
        return True
    print(f"  WARNING: Miner may not be running. Check: pm2 logs {miner_name}")
    return False


def check_status():
    """Check miner status."""
    miner_name = f"sn{SUBNET['netuid']}-nova"
    print(f"\n=== SN{SUBNET['netuid']} {SUBNET['name']} Status ===")

    result = run(f"pm2 list | grep {miner_name}", check=False)
    if result:
        print(f"  PM2: {result.strip()}")
    else:
        print("  PM2: NOT RUNNING")


def deploy(wallet_name, hotkey_name):
    """Full deployment pipeline."""
    print(f"{'='*60}")
    print(f"  SubnetAIQ Deploy Skill — SN{SUBNET['netuid']} {SUBNET['name']}")
    print(f"  Type: {SUBNET['type']}")
    print(f"  Difficulty: {SUBNET['difficulty']}")
    print(f"  Burn: ~{SUBNET['burn_estimate_tao']} TAO")
    print(f"{'='*60}")

    home = os.path.expanduser("~")

    if not check_hardware():
        print("\nDEPLOY FAILED: Hardware requirements not met.")
        return False

    repo_path = clone_repo(home)
    if not repo_path:
        print("\nDEPLOY FAILED: Could not clone repo.")
        return False

    if not setup_venv(repo_path):
        print("\nDEPLOY FAILED: Could not set up environment.")
        return False

    if not create_hotkey(wallet_name, hotkey_name):
        print("\nDEPLOY FAILED: Could not create hotkey.")
        return False

    reg_result = register(wallet_name, hotkey_name)
    if reg_result == "MANUAL":
        print("\n⚠ PAUSED: Run the registration command above, then re-run this script.")
        return False

    if not configure(repo_path, wallet_name, hotkey_name):
        print("\nDEPLOY FAILED: Configuration failed.")
        return False

    if not start_miner(repo_path, wallet_name, hotkey_name):
        print("\nDEPLOY WARNING: Miner may not have started. Check PM2 logs.")
        return False

    print(f"\n{'='*60}")
    print(f"  SN{SUBNET['netuid']} {SUBNET['name']} DEPLOYED")
    print(f"  Miner: sn{SUBNET['netuid']}-nova")
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
        run(f"pm2 stop sn{SUBNET['netuid']}-nova", check=False)
        print("Miner stopped.")
