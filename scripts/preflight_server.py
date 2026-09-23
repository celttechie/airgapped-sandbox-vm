#!/usr/bin/env python3
"""
Air-Gapped Sandbox VM - Target Hypervisor Pre-Flight Validator
Audits the remote target server for hardware virtualization extensions (VT-x/AMD-V),
kernel nested KVM enablement, /dev/kvm access, libvirt service health, and storage readiness.
"""

import argparse
import os
import subprocess
import sys

from common import (
    BLUE,
    BOLD,
    GREEN,
    RED,
    RESET,
    YELLOW,
    build_ssh_command,
    get_target_host,
    load_target_env,
    print_banner,
    print_table,
    run_remote,
)

CHECKS = []


def record(name, passed, status, purpose):
    CHECKS.append((name, status, purpose))
    return passed


def main():
    target_env = load_target_env()
    default_host = target_env.get("TARGET_HOST") or get_target_host() or ""
    default_user = target_env.get("TARGET_USER")
    default_key = target_env.get("TARGET_SSH_KEY")

    parser = argparse.ArgumentParser(description="Target Hypervisor Server Pre-Flight Diagnostics")
    parser.add_argument("--host", default=default_host, help=f"SSH host or alias (default: {default_host or 'target.env'})")
    parser.add_argument("--user", default=default_user, help="SSH user on target server")
    parser.add_argument("--key", default=default_key, help="Path to SSH private key")
    parser.add_argument("--pool", default="default", help="Storage pool name to verify (default: default)")
    parser.add_argument("--image", default="/var/lib/libvirt/images/ubuntu-22.04-server-cloudimg-amd64.img", help="Base cloud image path")
    args = parser.parse_args()

    server_host = args.host
    if not server_host:
        print(f"\n{RED}{BOLD}Error: No target host specified. Run 'make configure' or pass --host <server>{RESET}\n")
        return 1

    target_spec = f"{args.user}@{server_host}" if args.user else server_host
    print_banner(f"Target Hypervisor Server Pre-Flight Check ({target_spec})")

    all_passed = True

    # 1. SSH Reachability & Hostname
    res = run_remote(server_host, "hostname", user=args.user, key_path=args.key, timeout=5)
    if res.returncode == 0:
        remote_hostname = res.stdout.strip()
        record(f"SSH Reachability ({server_host})", True, f"{GREEN}OK{RESET} (Host: {remote_hostname})", "Remote Orchestration")
    else:
        record(f"SSH Reachability ({server_host})", False, f"{RED}FAILED{RESET}", "Remote Orchestration")
        print_table(CHECKS)
        print(f"\n{RED}{BOLD}Cannot reach target host '{server_host}' via SSH. Run 'make configure' first.{RESET}\n")
        return 1

    # 2. Hardware KVM (/dev/kvm)
    res = run_remote(server_host, "[ -e /dev/kvm ] && echo OK || echo MISSING", user=args.user, key_path=args.key)
    has_kvm = "OK" in res.stdout
    if not record("Hardware KVM (/dev/kvm)", has_kvm, f"{GREEN}OK{RESET} (/dev/kvm present)" if has_kvm else f"{RED}MISSING{RESET}", "Virtualization Engine"):
        all_passed = False

    # 3. CPU Virtualization Extensions
    res = run_remote(server_host, "grep -E -c '(vmx|svm)' /proc/cpuinfo || echo 0", user=args.user, key_path=args.key)
    cpu_cores = res.stdout.strip()
    has_vmx = cpu_cores.isdigit() and int(cpu_cores) > 0
    if not record("CPU Virtualization Flags", has_vmx, f"{GREEN}OK{RESET} ({cpu_cores} VMX/SVM threads)" if has_vmx else f"{RED}DISABLED IN BIOS{RESET}", "Hypervisor Hardware"):
        all_passed = False

    # 4. Nested KVM Kernel Parameter
    res_intel = run_remote(server_host, "cat /sys/module/kvm_intel/parameters/nested 2>/dev/null || true", user=args.user, key_path=args.key)
    res_amd = run_remote(server_host, "cat /sys/module/kvm_amd/parameters/nested 2>/dev/null || true", user=args.user, key_path=args.key)
    nested_intel = res_intel.stdout.strip()
    nested_amd = res_amd.stdout.strip()

    is_nested = nested_intel in ("Y", "y", "1") or nested_amd in ("Y", "y", "1")
    if is_nested:
        val = f"Intel ({nested_intel})" if nested_intel in ("Y", "y", "1") else f"AMD ({nested_amd})"
        record("Nested KVM Kernel Parameter", True, f"{GREEN}ENABLED{RESET} ({val})", "Nested Guest Virtualization")
    else:
        record("Nested KVM Kernel Parameter", False, f"{RED}DISABLED{RESET} (nested=N/0)", "Nested Guest Virtualization")
        all_passed = False

    # 5. Host Memory Capacity
    res = run_remote(server_host, "free -h | awk '/Mem:/ {print $2, \"total,\", $7, \"avail\"}'", user=args.user, key_path=args.key)
    mem_info = res.stdout.strip()
    record("Memory Capacity", bool(mem_info), f"{GREEN}OK{RESET} ({mem_info})", "VM Allocations")

    # 6. Remote Libvirtd Daemon
    res = run_remote(server_host, "virsh -c qemu:///system list --all >/dev/null 2>&1 && echo OK || echo FAIL", user=args.user, key_path=args.key)
    libvirtd_ok = "OK" in res.stdout
    if not record("Libvirtd System Daemon", libvirtd_ok, f"{GREEN}OK{RESET} (Responsive)" if libvirtd_ok else f"{RED}UNRESPONSIVE{RESET}", "Hypervisor Daemon"):
        all_passed = False

    # 7. Storage Pool
    pool_cmd = f"virsh -c qemu:///system pool-info '{args.pool}' 2>/dev/null | awk '/State:/ {{print $2}}'"
    res = run_remote(server_host, pool_cmd, user=args.user, key_path=args.key)
    pool_state = res.stdout.strip()
    if pool_state == "running":
        record(f"Storage Pool ('{args.pool}')", True, f"{GREEN}RUNNING{RESET}", "VM Disk Volumes")
    elif pool_state:
        record(f"Storage Pool ('{args.pool}')", False, f"{YELLOW}{pool_state.upper()}{RESET}", "VM Disk Volumes")
    else:
        record(f"Storage Pool ('{args.pool}')", False, f"{RED}NOT FOUND{RESET}", "VM Disk Volumes")
        all_passed = False

    # 8. Base Cloud Image Check
    res = run_remote(server_host, f"test -f '{args.image}' && echo OK || echo MISSING", user=args.user, key_path=args.key)
    has_image = "OK" in res.stdout
    if has_image:
        record("Base Cloud Image", True, f"{GREEN}FOUND{RESET} ({os.path.basename(args.image)})", "OS Image Source")
    else:
        record("Base Cloud Image", True, f"{YELLOW}NOT FOUND ON TARGET{RESET}", "OS Image Source")

    print_table(CHECKS)

    if all_passed:
        print(f"\n{GREEN}{BOLD}==> Pre-flight check PASSED! Target hypervisor is ready for OpenTofu provisioning.{RESET}\n")
        return 0
    else:
        print(f"\n{RED}{BOLD}==> Pre-flight check FAILED. Please resolve the issues marked in RED above.{RESET}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
