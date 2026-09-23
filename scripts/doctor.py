#!/usr/bin/env python3
"""
Air-Gapped Sandbox VM - Workstation Environment Doctor
Assesses local workstation developer tooling, OpenTofu / Terraform CLI, libvirt client, and git.
"""

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
    print_banner,
    print_table,
)

CHECKS = []


def check_local_tool(name, command, required=True, purpose=""):
    """Check if a local binary is installed and retrieve version info."""
    binary = command.split()[0]
    path = shutil.which(binary)
    if not path:
        status = f"{RED}MISSING{RESET}" if required else f"{YELLOW}OPTIONAL (NOT FOUND){RESET}"
        CHECKS.append((name, status, purpose))
        return False

    try:
        res = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=5)
        out = (res.stdout or res.stderr).strip()
        ver = out.splitlines()[0] if out else "Installed"
        status = f"{GREEN}OK{RESET} ({ver[:40]})"
        CHECKS.append((name, status, purpose))
        return True
    except Exception as e:
        status = f"{YELLOW}INSTALLED (Version check err: {e}){RESET}"
        CHECKS.append((name, status, purpose))
        return True


def check_pre_commit():
    """Check if pre-commit is installed and hooks are active."""
    has_precommit = shutil.which("pre-commit") is not None
    if has_precommit:
        hook_path = os.path.join(".git", "hooks", "pre-commit")
        if os.path.exists(hook_path):
            CHECKS.append(("Pre-Commit Git Hooks", f"{GREEN}INSTALLED{RESET}", "Secret Scanning & Quality Gates"))
        else:
            CHECKS.append(("Pre-Commit Git Hooks", f"{YELLOW}NOT INSTALLED (`pre-commit install`){RESET}", "Secret Scanning & Quality Gates"))
    else:
        CHECKS.append(("Pre-Commit Tool", f"{YELLOW}OPTIONAL (Run `pip install pre-commit`){RESET}", "Secret Scanning & Quality Gates"))


def check_git_repo():
    """Verify repository status."""
    is_git = os.path.exists(".git")
    if is_git:
        CHECKS.append(("Git Repository", f"{GREEN}OK{RESET} (.git present)", "Version Control"))
    else:
        CHECKS.append(("Git Repository", f"{YELLOW}NOT INITIALIZED{RESET}", "Version Control"))


def main():
    print_banner("Air-Gapped Sandbox VM - Workstation Environment Doctor")

    t1 = check_local_tool("OpenTofu / Terraform", "tofu version || terraform version", required=True, purpose="IaC Provisioning")
    t2 = check_local_tool("Libvirt CLI (virsh)", "virsh --version", required=True, purpose="Hypervisor & Console Management")
    t3 = check_local_tool("OpenSSH Client (ssh)", "ssh -V", required=True, purpose="Remote Host Access")
    has_keygen = shutil.which("ssh-keygen") is not None
    if has_keygen:
        keygen_path = shutil.which("ssh-keygen")
        CHECKS.append(("SSH Keygen (ssh-keygen)", f"{GREEN}OK{RESET} ({keygen_path})", "Keypair Generation"))
        t4 = True
    else:
        CHECKS.append(("SSH Keygen (ssh-keygen)", f"{RED}MISSING{RESET}", "Keypair Generation"))
        t4 = False
    has_iso = shutil.which("mkisofs") is not None or shutil.which("genisoimage") is not None
    if has_iso:
        iso_bin = shutil.which("mkisofs") or shutil.which("genisoimage")
        CHECKS.append(("Cloud-Init ISO (mkisofs/genisoimage)", f"{GREEN}OK{RESET} ({iso_bin})", "Cloud-Init ISO Creation"))
        t5 = True
    else:
        CHECKS.append(("Cloud-Init ISO (mkisofs/genisoimage)", f"{RED}MISSING{RESET} (`sudo apt install genisoimage`)", "Cloud-Init ISO Creation"))
        t5 = False
    t6 = check_local_tool("Python 3", "python3 --version", required=True, purpose="Automation & Verification Engine")
    t7 = check_local_tool("Make", "make --version", required=False, purpose="Workflow Automation")
    has_trivy = shutil.which("trivy") is not None
    if has_trivy:
        trivy_path = shutil.which("trivy")
        CHECKS.append(("Trivy Security Scanner", f"{GREEN}OK{RESET} ({trivy_path})", "IaC Security & Secret Auditing"))
    else:
        CHECKS.append(("Trivy Security Scanner", f"{YELLOW}OPTIONAL (`make security`){RESET}", "IaC Security & Secret Auditing"))
    check_git_repo()
    check_pre_commit()

    print_table(CHECKS, headers=("Workstation Tool / Check", "Status", "Purpose"))

    all_passed = all([t1, t2, t3, t4, t5, t6])
    if all_passed:
        print(f"\n{GREEN}{BOLD}==> All essential workstation developer tools are installed and ready.{RESET}\n")
        return 0
    else:
        print(f"\n{RED}{BOLD}==> Some required workstation tools are missing. Please install them before proceeding.{RESET}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
