# Air-Gapped Sandbox VM Makefile
# Modular Python & OpenTofu automation adhering to talos-k8s-platform architecture

SHELL := /usr/bin/env bash
PYTHON := python3
TOFU  := tofu

.PHONY: help configure doctor preflight check-host init fmt validate plan apply destroy console status clean

## Show help and available targets
help:
	@echo "======================================================================="
	@echo " Air-Gapped Sandbox VM Management"
	@echo "======================================================================="
	@echo "Workflow Pipeline:"
	@echo "  1. make configure    - Setup SSH keys, target.env, and terraform.tfvars"
	@echo "  2. make doctor       - Validate local workstation developer tools"
	@echo "  3. make preflight    - Audit target hypervisor and nested KVM capability"
	@echo "  4. make plan / apply - Provision the nested hypervisor VM with OpenTofu"
	@echo ""
	@echo "Available Targets:"
	@echo "  make configure    - Interactive SSH key, host alias, and tfvars generation"
	@echo "  make doctor       - Audit workstation binaries (tofu, virsh, ssh, python3)"
	@echo "  make preflight    - Audit target server (CPU flags, nested KVM, libvirt)"
	@echo "  make check-host   - Alias for 'make preflight'"
	@echo "  make init         - Initialize OpenTofu / Terraform providers"
	@echo "  make fmt          - Format OpenTofu configuration files"
	@echo "  make validate     - Validate OpenTofu syntax and schema"
	@echo "  make plan         - Generate and inspect execution plan"
	@echo "  make apply        - Provision the nested hypervisor sandbox VM"
	@echo "  make destroy      - Tear down the sandbox VM and isolated network"
	@echo "  make console      - Connect to the VM serial console (virsh console)"
	@echo "  make status       - Inspect VM state, isolated network, and DHCP leases"
	@echo "  make security     - Run Trivy security and IaC misconfiguration scan"
	@echo "  make lint         - Run pre-commit secret scanning and formatting hooks"
	@echo "  make hook-install - Install pre-commit git hooks in .git/hooks"
	@echo "  make clean        - Remove local plan cache"
	@echo "======================================================================="

## Install Git Pre-Commit Hooks
hook-install:
	@pre-commit install

## Run Secret Scanning & Linting Gates
lint:
	@pre-commit run --all-files

## Run Trivy Security & IaC Misconfiguration Audit
security:
	@if command -v trivy >/dev/null 2>&1; then \
		echo "==> Running Trivy Security & IaC Misconfiguration Audit..."; \
		trivy config .; \
	else \
		echo "==> Trivy is not installed."; \
		echo "    Install with: curl -sfL https://raw.githubusercontent.com/aquasecurity/trivy/main/contrib/install.sh | sh -s -- -b ~/.local/bin"; \
		exit 1; \
	fi

## Step 1: Interactive Target Configuration & SSH Setup
configure:
	@$(PYTHON) scripts/configure.py

## Step 2: Workstation Developer Environment Doctor
doctor:
	@$(PYTHON) scripts/doctor.py

## Step 3: Target Server Hypervisor & Nested KVM Pre-Flight Check
preflight:
	@$(PYTHON) scripts/preflight_server.py

check-host: preflight

## Step 4: Initialize OpenTofu
init:
	@$(TOFU) init

## Format configuration files
fmt:
	@$(TOFU) fmt

## Validate configuration
validate:
	@$(TOFU) validate

## OpenTofu Plan
plan:
	@$(TOFU) plan -out=tfplan

## OpenTofu Apply
apply:
	@if [ -f tfplan ]; then \
		$(TOFU) apply tfplan && rm -f tfplan; \
	else \
		$(TOFU) apply; \
	fi

## OpenTofu Destroy
destroy:
	@$(TOFU) destroy

## Connect to serial console
console:
	@VM_NAME=$$($(TOFU) output -raw vm_name 2>/dev/null || echo "airgapped-sandbox-hypervisor"); \
	LIBVIRT_URI=$$(grep -E '^\s*libvirt_uri\s*=' terraform.tfvars 2>/dev/null | cut -d'=' -f2 | tr -d ' "' || echo ""); \
	if [ -n "$$LIBVIRT_URI" ]; then \
		echo "Connecting to serial console on $$LIBVIRT_URI for $$VM_NAME..."; \
		virsh -c "$$LIBVIRT_URI" console "$$VM_NAME"; \
	else \
		echo "Connecting to serial console for $$VM_NAME..."; \
		virsh console "$$VM_NAME"; \
	fi

## Check VM and Network status
status:
	@VM_NAME=$$($(TOFU) output -raw vm_name 2>/dev/null || echo "airgapped-sandbox-hypervisor"); \
	NET_NAME=$$($(TOFU) output -raw network_name 2>/dev/null || echo "airgap-sandbox-net"); \
	LIBVIRT_URI=$$(grep -E '^\s*libvirt_uri\s*=' terraform.tfvars 2>/dev/null | cut -d'=' -f2 | tr -d ' "' || echo ""); \
	VIRSH_CMD="virsh"; \
	if [ -n "$$LIBVIRT_URI" ]; then VIRSH_CMD="virsh -c $$LIBVIRT_URI"; fi; \
	echo "==> Domain Status ($$VM_NAME):"; \
	$$VIRSH_CMD dominfo "$$VM_NAME" 2>/dev/null || echo "VM not running or domain not found."; \
	echo ""; \
	echo "==> Network Status ($$NET_NAME):"; \
	$$VIRSH_CMD net-info "$$NET_NAME" 2>/dev/null || echo "Network not found or inactive."; \
	echo ""; \
	echo "==> DHCP Leases ($$NET_NAME):"; \
	$$VIRSH_CMD net-dhcp-leases "$$NET_NAME" 2>/dev/null || echo "No active DHCP leases."

## Clean temporary plan files
clean:
	@rm -f tfplan
