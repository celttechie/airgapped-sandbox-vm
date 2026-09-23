#!/usr/bin/env python3
"""
Air-Gapped Sandbox VM - Shared Automation & Verification Utilities
Provides unified target host resolution, SSH execution helpers, target.env and tfvars parsing,
colored terminal formatting, and standardized diagnostic reporting.
"""

import os
import re
import shutil
import subprocess
import sys

# -----------------------------------------------------------------------------
# Terminal Styling Constants
# -----------------------------------------------------------------------------
GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
BLUE = "\033[36m"
BOLD = "\033[1m"
RESET = "\033[0m"


def get_repo_root():
    """Return the absolute path to the repository root."""
    return os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def print_banner(title):
    """Print a standardized styled banner."""
    print(f"\n{BLUE}{BOLD}{'=' * 78}{RESET}")
    print(f"{BLUE}{BOLD}  {title:<74}  {RESET}")
    print(f"{BLUE}{BOLD}{'=' * 78}{RESET}\n")


def print_table(rows, headers=("Check / Resource", "Status", "Purpose")):
    """Print formatted 3-column table for doctor/pre-flight checks."""
    print(f"{BOLD}{headers[0]:<34} {headers[1]:<36} {headers[2]}{RESET}")
    print("-" * 78)
    for name, status, purpose in rows:
        print(f"{name:<34} {status:<36} {purpose}")
    print("-" * 78)


def load_target_env(env_path=None):
    """Load and parse key-value pairs from target.env file."""
    if env_path is None:
        env_path = os.path.join(get_repo_root(), "target.env")

    env_vars = {}
    if os.path.exists(env_path):
        try:
            with open(env_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#") and "=" in line:
                        k, v = line.split("=", 1)
                        env_vars[k.strip()] = v.strip().strip('"\'')
        except Exception:
            pass
    return env_vars


def save_target_env(env_vars, env_path=None):
    """Save key-value pairs to target.env."""
    if env_path is None:
        env_path = os.path.join(get_repo_root(), "target.env")

    with open(env_path, "w") as f:
        f.write("# Target Hypervisor Server Environment Configuration\n")
        f.write("# Generated automatically by scripts/configure.py\n\n")
        for k, v in sorted(env_vars.items()):
            f.write(f"{k}=\"{v}\"\n")


def get_target_host(repo_root=None):
    """Dynamically determine target hypervisor host.
    Search precedence:
    1. TARGET_HOST environment variable
    2. TARGET_HOST declared in target.env
    3. libvirt_uri in terraform.tfvars
    """
    if os.getenv("TARGET_HOST"):
        return os.getenv("TARGET_HOST")

    if repo_root is None:
        repo_root = get_repo_root()

    target_env = load_target_env(os.path.join(repo_root, "target.env"))
    if target_env.get("TARGET_HOST"):
        return target_env["TARGET_HOST"]

    tfvars_path = os.path.join(repo_root, "terraform.tfvars")
    if os.path.exists(tfvars_path):
        try:
            with open(tfvars_path, "r") as f:
                for line in f:
                    m = re.search(r'libvirt_uri\s*=\s*"qemu\+ssh://(?:[^@]+@)?([^/]+)/system"', line)
                    if m:
                        return m.group(1)
        except Exception:
            pass

    return None


def get_libvirt_uri(repo_root=None):
    """Return configured libvirt_uri or compute from target host."""
    if repo_root is None:
        repo_root = get_repo_root()

    tfvars_path = os.path.join(repo_root, "terraform.tfvars")
    if os.path.exists(tfvars_path):
        try:
            with open(tfvars_path, "r") as f:
                for line in f:
                    m = re.search(r'libvirt_uri\s*=\s*"([^"]+)"', line)
                    if m:
                        return m.group(1)
        except Exception:
            pass

    host = get_target_host(repo_root)
    if host:
        return f"qemu+ssh://{host}/system"
    return "qemu:///system"


def build_ssh_command(target_host, user=None, key_path=None, command=None, timeout=6):
    """Construct an ssh command list with standard resilient flags."""
    ssh_cmd = [
        "ssh",
        "-o", f"ConnectTimeout={timeout}",
        "-o", "StrictHostKeyChecking=accept-new",
        "-o", "BatchMode=yes",
    ]
    if key_path and os.path.exists(os.path.expanduser(key_path)):
        ssh_cmd += ["-i", os.path.expanduser(key_path)]

    target_spec = f"{user}@{target_host}" if user else target_host
    ssh_cmd.append(target_spec)

    if command:
        if isinstance(command, list):
            ssh_cmd.extend(command)
        else:
            ssh_cmd.append(command)
    return ssh_cmd


def run_remote(target_host, command, user=None, key_path=None, timeout=10):
    """Execute a command on the remote host via SSH and return CompletedProcess."""
    cmd = build_ssh_command(target_host, user=user, key_path=key_path, command=command, timeout=timeout)
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 2)


def run_local(command, capture_output=True, check=False):
    """Execute a local shell command and return CompletedProcess."""
    if isinstance(command, str):
        return subprocess.run(command, shell=True, capture_output=capture_output, text=True, check=check)
    return subprocess.run(command, capture_output=capture_output, text=True, check=check)
