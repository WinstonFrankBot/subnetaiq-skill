"""SubnetAIQ Deploy Skill — SN65 TPN (Trusted Proxy Network)
Executable mining skill. Agent runs this → miner deployed → earning TAO.

What it does:
1. Checks hardware compatibility
2. Clones repo + sets up venv
3. Creates hotkey
4. Registers on-chain
5. Installs local sybil package
6. Starts miner via PM2
7. Verifies earning status

Usage:
  python sn65_tpn.py deploy --wallet finflow_miner
  python sn65_tpn.py status
  python sn65_tpn.py stop

Requirements:
  - CPU (no GPU required)
  - Python 3.10+
  - Bittensor wallet with TAO for registration
  - PM2 installed
  - Optional: IP2Location + MaxMind accounts for enhanced scoring
"""

import argparse
import json
import os
import subprocess
import sys
import time


# ─── CONFIG ──────────────────────────────────────────────────────────────

SUBNET = {
    "netuid": 65,
    "name": "TPN",
    "repo": "https://github.com/tpn-subnet/tpn-subnet.git",
    "repo_dir": "tpn-subnet",
    "github": "tpn-subnet/tpn-subnet",
    "min_vram_gb": 0,
    "python_version": "3.10",
    "difficulty": "Easy",
    "type": "Proxy network — Sybil resistance + IP verification",
    "burn_estimate_tao": 0.1,
    "axon_port": 8091,
    "miner_script": "neurons/miner.py",
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
    """Check hardware compatibility — SN65 is CPU-only."""
    print("\n[1/7] Checking hardware...")
    py_version = sys.version_info
    print(f"  Python: {py_version.major}.{py_version.minor}")
    if py_version < (3, 10):
        print(f"  FAIL: Need Python 3.10+, you have {py_version.major}.{py_version.minor}")
        return False
    print(f"  PASS: No GPU required — CPU-only miner")
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
    """Set up Python virtual environment and install the local sybil package."""
    print("\n[3/7] Setting up Python environment...")
    venv_path = os.path.join(repo_path, "venv")
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
    python = os.path.join(venv_path, "bin", "python")

    # Install requirements
    requirements = os.path.join(repo_path, "requirements.txt")
    if os.path.exists(requirements):
        run(f"{pip} install -r requirements.txt --quiet", cwd=repo_path, timeout=300, check=False)

    # CRITICAL: Install the local sybil package — it's a local module in the repo,
    # not a PyPI package. Without this, miner crashes with "ModuleNotFoundError: No module named 'sybil'"
    run(f"{pip} install -e . --quiet", cwd=repo_path, timeout=300, check=False)

    # Verify sybil import
    test = run(f"{python} -c \"import sybil; print('OK')\"", cwd=repo_path, check=False)
    if test and "OK" in test:
        print("  Dependencies + sybil package installed successfully")
        return True
    print("  WARNING: sybil import test failed — miner will crash without it")
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

    btcli = run("which btcli", check=False)
    if not btcli:
        for path in [
            os.path.expanduser("~/synth-subnet/.venv/bin/btcli"),
            os.path.expanduser("~/tpn-subnet/venv/bin/btcli"),
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
    """Register on SN65. Requires wallet password."""
    print(f"\n[5/7] Registering on SN{SUBNET['netuid']}...")
    print(f"  Estimated burn: ~{SUBNET['burn_estimate_tao']} TAO")
    print("  *** REQUIRES YOUR WALLET PASSWORD ***")
    print(f"  Run this command manually:")
    btcli = run("which btcli", check=False) or "btcli"
    print(f"  {btcli} subnet recycle_register --netuid {SUBNET['netuid']} --wallet.name {wallet_name} --wallet.hotkey {hotkey_name} --subtensor.network finney")
    return "MANUAL"


def configure(repo_path, wallet_name, hotkey_name):
    """Configure the miner — TPN uses CLI args, no .env needed."""
    print("\n[6/7] Configuring miner...")
    print("  TPN miner uses CLI args — no .env file needed")
    print(f"  Wallet: {wallet_name}")
    print(f"  Hotkey: {hotkey_name}")
    print(f"  Port: {SUBNET['axon_port']}")
    print("  NOTE: For enhanced scoring, set up IP2Location + MaxMind accounts")
    return True


def start_miner(repo_path, wallet_name, hotkey_name):
    """Start the miner via PM2."""
    print("\n[7/7] Starting miner...")
    python = os.path.join(repo_path, "venv", "bin", "python")
    miner_name = f"sn{SUBNET['netuid']}-tpn"

    # Check if already running
    result = run(f"pm2 list | grep {miner_name}", check=False)
    if result and "online" in result:
        print(f"  Already running: {miner_name}")
        return True

    cmd = (
        f"pm2 start {python} --name {miner_name} --interpreter none "
        f"--cwd {repo_path} -- {SUBNET['miner_script']} "
        f"--netuid {SUBNET['netuid']} --subtensor.network finney "
        f"--wallet.name {wallet_name} --wallet.hotkey {hotkey_name} "
        f"--logging.info --axon.port {SUBNET['axon_port']}"
    )
    run(cmd, check=False)
    time.sleep(10)

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
    miner_name = f"sn{SUBNET['netuid']}-tpn"
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
    print(f"  Miner: sn{SUBNET['netuid']}-tpn")
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
        run(f"pm2 stop sn{SUBNET['netuid']}-tpn", check=False)
        print("Miner stopped.")
