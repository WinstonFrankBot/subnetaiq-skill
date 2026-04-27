"""SubnetAIQ Deploy Skill — SN64 Chutes
Executable mining skill. Agent runs this → prints requirements → manual setup needed.

SPECIAL: SN64 Chutes is NOT a simple pip install miner. It requires:
  - K3s (lightweight Kubernetes)
  - Ansible for orchestration
  - Ubuntu 22.04 (NOT 24.04)
  - TEE/aegis attestation (TDX or NVIDIA Confidential Computing)
  - Kernel 6.17 is INCOMPATIBLE — waiting for Chutes TEE update

This script checks prerequisites and prints the full setup guide.
Actual deployment must be done manually following the chutes-miner README.

What it does:
1. Checks hardware compatibility
2. Checks OS and kernel version
3. Creates hotkey
4. Registers on-chain
5. Prints full requirements and setup instructions
6. Links to chutes-miner README
7. Verifies on-chain status

Usage:
  python sn64_chutes.py deploy --wallet finflow_miner --machine beast
  python sn64_chutes.py status
  python sn64_chutes.py stop

Requirements:
  - GPU (H100/H200 preferred, RTX 5090 IS supported per chain verification)
  - Ubuntu 22.04 (NOT 24.04)
  - K3s + Ansible
  - TEE attestation capability
  - Kernel < 6.17 (6.17 incompatible with current Chutes TEE)
  - Bittensor wallet with TAO for registration
"""

import argparse
import json
import os
import subprocess
import sys
import time


# ─── CONFIG ──────────────────────────────────────────────────────────────

SUBNET = {
    "netuid": 64,
    "name": "Chutes",
    "repo": "https://github.com/chutes-ai/chutes-miner.git",
    "repo_dir": "chutes-miner",
    "github": "chutes-ai/chutes-miner",
    "min_vram_gb": 24,
    "python_version": "3.10",
    "difficulty": "Hard",
    "type": "Serverless AI Inference",
    "burn_estimate_tao": 0.07,
    "axon_port": None,
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
    """Check GPU and system compatibility."""
    print("\n[1/7] Checking hardware and OS...")

    # GPU check
    result = run("nvidia-smi --query-gpu=name,memory.total --format=csv,noheader,nounits", check=False)
    if not result:
        print("  No NVIDIA GPU found. SN64 Chutes needs GPU with 24GB+ VRAM.")
        return False
    name, vram = result.split(", ")
    vram_gb = int(vram) / 1024
    print(f"  GPU: {name} ({vram_gb:.0f}GB VRAM)")

    if vram_gb < SUBNET["min_vram_gb"]:
        print(f"  FAIL: Need {SUBNET['min_vram_gb']}GB+, you have {vram_gb:.0f}GB")
        return False
    print(f"  PASS: {vram_gb:.0f}GB >= {SUBNET['min_vram_gb']}GB required")

    # OS check
    result = run("cat /etc/os-release 2>/dev/null | grep PRETTY_NAME", check=False)
    if result:
        print(f"  OS: {result}")
        if "24.04" in result:
            print("  WARNING: Ubuntu 24.04 detected. SN64 requires Ubuntu 22.04!")
    else:
        print("  WARNING: Could not determine OS version")

    # Kernel check
    result = run("uname -r", check=False)
    if result:
        print(f"  Kernel: {result}")
        if "6.17" in result:
            print("  !!! BLOCKER: Kernel 6.17 is INCOMPATIBLE with Chutes TEE !!!")
            print("  !!! Waiting for Chutes TEE update before deployment !!!")
            return False

    # K3s check
    result = run("which k3s", check=False)
    if result:
        print(f"  K3s: {result}")
    else:
        print("  K3s: NOT INSTALLED (required)")

    # Ansible check
    result = run("which ansible", check=False)
    if result:
        print(f"  Ansible: {result}")
    else:
        print("  Ansible: NOT INSTALLED (required)")

    return True


def clone_repo(home_dir):
    """Clone the chutes-miner repo."""
    print("\n[2/7] Cloning repo...")
    repo_path = os.path.join(home_dir, SUBNET["repo_dir"])
    if os.path.exists(repo_path):
        print(f"  Already exists: {repo_path}")
        run(f"git pull", cwd=repo_path, check=False)
        return repo_path
    run(f"git clone {SUBNET['repo']} {repo_path}")
    if os.path.exists(repo_path):
        print(f"  Cloned to {repo_path}")
        return repo_path
    print("  FAIL: Clone failed")
    return None


def setup_venv(repo_path):
    """Print setup requirements — Chutes uses K3s/Ansible, not a simple venv."""
    print("\n[3/7] Environment setup (K3s + Ansible required)...")
    print("  SN64 Chutes does NOT use a standard Python venv.")
    print("  It requires K3s (lightweight Kubernetes) + Ansible for deployment.")
    print("")
    print("  Required packages:")
    print("    - K3s: curl -sfL https://get.k3s.io | sh -")
    print("    - Ansible: pip install ansible")
    print("    - NVIDIA Container Toolkit")
    print("    - TEE attestation (TDX or NVIDIA CC)")
    print("")
    print("  See README: https://github.com/chutes-ai/chutes-miner")
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
    """Register on SN64. Requires wallet password."""
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
    """Print configuration requirements."""
    print("\n[6/7] Configuration (manual setup required)...")
    print("")
    print("  SN64 Chutes requires MANUAL configuration:")
    print("")
    print("  1. Set up K3s cluster:")
    print("     curl -sfL https://get.k3s.io | sh -")
    print("")
    print("  2. Configure Ansible inventory for your machines")
    print("")
    print("  3. Set up TEE attestation (aegis):")
    print("     - Intel TDX or NVIDIA Confidential Computing")
    print("     - Trust Security audited smart-contract vault")
    print("")
    print("  4. Configure miner:")
    print(f"     WALLET_NAME={wallet_name}")
    print(f"     WALLET_HOTKEY={hotkey_name}")
    print(f"     NETUID={SUBNET['netuid']}")
    print("")
    print("  BLOCKERS:")
    print("  - TEE/aegis required — kernel 6.17 is INCOMPATIBLE")
    print("  - Waiting for Chutes TEE update before deployment is possible")
    print("")
    print(f"  Full guide: https://github.com/{SUBNET['github']}")
    return True


def start_miner(repo_path, wallet_name, hotkey_name):
    """Cannot auto-start — requires K3s/Ansible."""
    print("\n[7/7] Miner start (manual)...")
    print("  SN64 Chutes cannot be auto-started via PM2.")
    print("  It runs as a K3s deployment managed by Ansible.")
    print("")
    print("  After K3s + Ansible setup, deploy with:")
    print(f"  cd {repo_path}")
    print("  ansible-playbook deploy.yml")
    print("")
    print("  Revenue info: $22K/day across network, REVENUE-BASED incentive")
    print("  700 H200 inventory, optimization comps coming")
    return True


def check_status():
    """Check on-chain status."""
    print(f"\n=== SN{SUBNET['netuid']} {SUBNET['name']} Status ===")

    # K3s status
    result = run("k3s kubectl get pods 2>/dev/null | grep chutes", check=False)
    if result:
        print(f"  K3s pods: {result}")
    else:
        print("  K3s: No chutes pods found (or K3s not installed)")

    # On-chain status
    run(f"python3 -c \"\nimport bittensor as bt\nsub = bt.Subtensor('finney')\nmg = sub.metagraph({SUBNET['netuid']})\nprint(f'Total UIDs: {{mg.n}}')\nprint(f'Active miners: {{sum(1 for i in range(mg.n) if float(mg.incentive[i]) > 0)}}')\nprint(f'Total stake: {{float(mg.total_stake):.0f}} TAO')\nsub.substrate.close()\n\"", check=False)


def deploy(wallet_name, hotkey_name):
    """Full deployment pipeline — mostly informational for SN64."""
    print(f"{'='*60}")
    print(f"  SubnetAIQ Deploy Skill — SN{SUBNET['netuid']} {SUBNET['name']}")
    print(f"  Type: {SUBNET['type']}")
    print(f"  Difficulty: {SUBNET['difficulty']}")
    print(f"  Burn: ~{SUBNET['burn_estimate_tao']} TAO")
    print(f"  SPECIAL: Requires K3s + Ansible + Ubuntu 22.04 + TEE")
    print(f"  BLOCKER: Kernel 6.17 incompatible — waiting for Chutes TEE update")
    print(f"{'='*60}")

    home = os.path.expanduser("~")

    if not check_gpu():
        print("\nDEPLOY BLOCKED: Hardware/OS requirements not met.")
        return False

    repo_path = clone_repo(home)
    if not repo_path:
        print("\nDEPLOY FAILED: Could not clone repo.")
        return False

    if not setup_venv(repo_path):
        print("\nDEPLOY FAILED: Could not verify prerequisites.")
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
        print("\nDEPLOY WARNING: Could not auto-start.")
        return False

    print(f"\n{'='*60}")
    print(f"  SN{SUBNET['netuid']} {SUBNET['name']} — SETUP PARTIALLY COMPLETE")
    print(f"  NEXT: Follow manual K3s/Ansible setup in chutes-miner README")
    print(f"  BLOCKER: TEE/kernel 6.17 incompatibility — wait for update")
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
        print("SN64 Chutes: Managed by K3s, not PM2.")
        print("To stop: k3s kubectl delete deployment chutes-miner")
