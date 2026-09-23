#!/usr/bin/env bash
# Source this file to configure your local shell session for the target hypervisor:
#   source scripts/env.sh
#
# Sets VIRSH_DEFAULT_CONNECT_URI so all standard `virsh` commands connect
# directly to the target environment without needing `-c` flags.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

TARGET_ENV="${REPO_ROOT}/target.env"
TFVARS="${REPO_ROOT}/terraform.tfvars"

URI=""

if [[ -f "${TARGET_ENV}" ]]; then
    URI=$(grep -E '^\s*LIBVIRT_URI\s*=' "${TARGET_ENV}" | cut -d'=' -f2 | tr -d ' "' || true)
fi

if [[ -z "${URI}" && -f "${TFVARS}" ]]; then
    URI=$(grep -E '^\s*libvirt_uri\s*=' "${TFVARS}" | cut -d'=' -f2 | tr -d ' "' || true)
fi

if [[ -z "${URI}" ]]; then
    URI="qemu:///system"
fi

export VIRSH_DEFAULT_CONNECT_URI="${URI}"
export LIBVIRT_DEFAULT_URI="${URI}"

echo "======================================================================="
echo " Environment configured for target hypervisor:"
echo "   VIRSH_DEFAULT_CONNECT_URI = ${VIRSH_DEFAULT_CONNECT_URI}"
echo "======================================================================="
echo " You can now run standard commands directly:"
echo "   virsh list --all"
echo "   virsh console airgapped-sandbox-hypervisor"
echo "   virsh dominfo airgapped-sandbox-hypervisor"
echo "======================================================================="
