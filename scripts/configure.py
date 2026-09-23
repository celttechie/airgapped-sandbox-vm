#!/usr/bin/env python3
"""
Air-Gapped Sandbox VM - Interactive Target Configuration & SSH Setup
Generates dedicated SSH keys, updates ~/.ssh/config, verifies passwordless access,
and produces target.env and terraform.tfvars.
"""

import argparse
import getpass
import os
import shutil
import subprocess
import sys

from common import (
    BLUE,
    BOLD,
    GREEN,
    RED,
    RESET,
    YELLOW,
    get_repo_root,
    load_target_env,
    print_banner,
    run_remote,
    save_target_env,
)


def prompt(text, default=None):
    """Prompt the user for input with an optional default value."""
    if default:
        val = input(f"{text} [{default}]: ").strip()
        return val if val else default
    while True:
        val = input(f"{text}: ").strip()
        if val:
            return val


def main():
    parser = argparse.ArgumentParser(description="Configure Target Hypervisor Host & OpenTofu Variables")
    parser.add_argument("--host", help="Target hypervisor IP address or hostname")
    parser.add_argument("--user", help="SSH username on target host")
    parser.add_argument("--alias", help="SSH host alias (default: sandbox-hypervisor)")
    parser.add_argument("--key", help="SSH private key path")
    parser.add_argument("--non-interactive", action="store_true", help="Run non-interactively using defaults/args")
    args = parser.parse_args()

    print_banner("Air-Gapped Sandbox VM - Target Hypervisor Setup")

    existing_env = load_target_env()
    current_user = getpass.getuser()

    if args.non_interactive:
        target_ip = args.host or existing_env.get("TARGET_IP")
        if not target_ip:
            print(f"{RED}Error: --host is required in non-interactive mode.{RESET}")
            return 1
        target_user = args.user or existing_env.get("TARGET_USER") or current_user
        host_alias = args.alias or existing_env.get("TARGET_HOST") or "sandbox-hypervisor"
        key_path = os.path.expanduser(args.key or existing_env.get("TARGET_SSH_KEY") or "~/.ssh/id_sandbox_hypervisor_ed25519")
    else:
        print("Configure the connection to your virtualization server.\n")
        default_ip = existing_env.get("TARGET_IP", "")
        target_ip = args.host or prompt("Enter Target Hypervisor Hostname or IP Address", default_ip or None)

        default_user = existing_env.get("TARGET_USER", current_user)
        target_user = args.user or prompt("Enter SSH User on Target Host", default_user)

        default_alias = existing_env.get("TARGET_HOST", "sandbox-hypervisor")
        host_alias = args.alias or prompt("Enter SSH Config Host Alias", default_alias)

        default_key = existing_env.get("TARGET_SSH_KEY", "~/.ssh/id_sandbox_hypervisor_ed25519")
        key_path = os.path.expanduser(args.key or prompt("Enter SSH Key Path to use", default_key))

    pub_key_path = f"{key_path}.pub"
    ssh_dir = os.path.expanduser("~/.ssh")
    ssh_config = os.path.join(ssh_dir, "config")

    os.makedirs(ssh_dir, mode=0o700, exist_ok=True)

    # 1. Generate SSH Key if needed
    if not os.path.exists(key_path):
        print(f"\n==> Generating dedicated Ed25519 SSH keypair: {key_path}...")
        subprocess.run(
            ["ssh-keygen", "-t", "ed25519", "-f", key_path, "-C", f"{host_alias}-{target_user}", "-N", ""],
            check=True
        )
        os.chmod(key_path, 0o600)
        os.chmod(pub_key_path, 0o644)
        print(f"==> {GREEN}SSH keypair generated successfully.{RESET}")
    else:
        print(f"==> SSH key already exists at {key_path}.")

    # 2. Update ~/.ssh/config
    if not os.path.exists(ssh_config):
        open(ssh_config, "w").close()
        os.chmod(ssh_config, 0o600)

    with open(ssh_config, "r") as f:
        config_content = f.read()

    if f"Host {host_alias}" in config_content:
        print(f"==> SSH host alias '{host_alias}' already present in {ssh_config}.")
    else:
        print(f"==> Adding '{host_alias}' host entry to {ssh_config}...")
        entry = (
            f"\n# Air-Gapped Sandbox Hypervisor Target\n"
            f"Host {host_alias}\n"
            f"    HostName {target_ip}\n"
            f"    User {target_user}\n"
            f"    IdentityFile {key_path}\n"
            f"    IdentitiesOnly yes\n"
            f"    StrictHostKeyChecking accept-new\n"
        )
        with open(ssh_config, "a") as f:
            f.write(entry)
        print(f"==> {GREEN}Host entry added to {ssh_config}.{RESET}")

    # 3. Offer ssh-copy-id
    if not args.non_interactive:
        copy_ans = input(f"\n==> Copy SSH public key to {target_user}@{target_ip} via ssh-copy-id? [Y/n]: ").strip().lower()
        if copy_ans in ("", "y", "yes"):
            print(f"==> Copying public key to {target_user}@{target_ip} (enter remote password if prompted)...")
            subprocess.run(["ssh-copy-id", "-i", pub_key_path, f"{target_user}@{target_ip}"])

    # 4. Populate known_hosts for both IP and Host Alias (ensures OpenTofu Go SSH client trusts host)
    known_hosts = os.path.join(ssh_dir, "known_hosts")
    print(f"==> Registering host keys in {known_hosts}...")
    try:
        scan_res = subprocess.run(
            ["ssh-keyscan", "-t", "ed25519,ecdsa,rsa", host_alias, target_ip],
            capture_output=True, text=True, timeout=5
        )
        if scan_res.stdout:
            with open(known_hosts, "a") as f:
                f.write(scan_res.stdout)
    except Exception as e:
        print(f"==> {YELLOW}[WARN] ssh-keyscan encountered: {e}{RESET}")

    # 5. Add key to ssh-agent
    try:
        subprocess.run(["ssh-add", key_path], capture_output=True, timeout=3)
    except Exception:
        pass

    # 6. Test SSH Connectivity
    print(f"\n==> Testing passwordless SSH connection to '{host_alias}'...")
    res = run_remote(host_alias, "hostname", timeout=6)
    if res.returncode == 0:
        remote_host = res.stdout.strip()
        print(f"==> {GREEN}{BOLD}[PASS] SSH connection established to {host_alias} (Remote host: {remote_host}){RESET}")
    else:
        print(f"==> {YELLOW}[WARN] Could not connect to {host_alias} passwordlessly.{RESET}")
        print(f"    Manual fix: ssh-copy-id -i {pub_key_path} {target_user}@{target_ip}")

    # 7. Save target.env
    repo_root = get_repo_root()
    libvirt_uri = f"qemu+ssh://{target_user}@{target_ip}/system"
    env_data = {
        "TARGET_HOST": host_alias,
        "TARGET_IP": target_ip,
        "TARGET_USER": target_user,
        "TARGET_SSH_KEY": key_path,
        "LIBVIRT_URI": libvirt_uri,
    }
    save_target_env(env_data, os.path.join(repo_root, "target.env"))
    print(f"==> Saved environment settings to target.env.")

    # 8. Generate terraform.tfvars
    tfvars_path = os.path.join(repo_root, "terraform.tfvars")
    tfvars_example = os.path.join(repo_root, "terraform.tfvars.example")

    tfvars_content = (
        f'# Generated by make configure\n'
        f'libvirt_uri             = "{libvirt_uri}"\n'
        f'vm_name                 = "airgapped-sandbox-hypervisor"\n'
        f'vm_memory_mb            = 32768\n'
        f'vm_vcpu                 = 8\n'
        f'storage_pool_name       = "default"\n'
        f'base_image_source       = "https://cloud-images.ubuntu.com/releases/22.04/release/ubuntu-22.04-server-cloudimg-amd64.img"\n'
        f'disk_size_bytes         = 64424509440 # 60 GB\n'
        f'create_isolated_network = true\n'
        f'network_name            = "airgap-sandbox-net"\n'
        f'network_cidr            = "10.160.0.0/24"\n'
        f'network_domain          = "sandbox.local"\n'
        f'admin_username          = "{target_user}"\n'
        f'enable_nested_kvm       = true\n'
        f'enable_qemu_agent       = false\n'
        f'wait_for_lease          = false\n'
    )

    if not os.path.exists(tfvars_path):
        with open(tfvars_path, "w") as f:
            f.write(tfvars_content)
        print(f"==> Generated terraform.tfvars configured for {host_alias}.")
    else:
        print(f"==> terraform.tfvars already exists. (Leave as-is or update as needed).")

    print(f"\n{BLUE}{BOLD}======================================================================={RESET}")
    print(f"{BLUE}{BOLD} Configuration Complete! Next Steps:                                   {RESET}")
    print(f"{BLUE}{BOLD}   1. make doctor      - Validate workstation tools                    {RESET}")
    print(f"{BLUE}{BOLD}   2. make preflight   - Validate target hypervisor & nested KVM       {RESET}")
    print(f"{BLUE}{BOLD}   3. make plan        - Generate OpenTofu execution plan              {RESET}")
    print(f"{BLUE}{BOLD}   4. make apply       - Provision the air-gapped sandbox VM           {RESET}")
    print(f"{BLUE}{BOLD}======================================================================={RESET}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
