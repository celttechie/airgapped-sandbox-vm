# Airgapped Sandbox VM (Nested Hypervisor)

A reusable OpenTofu / Terraform configuration and automation suite for provisioning nested KVM hypervisor VMs with isolated networking, hardware virtualization passthrough (`host-passthrough` CPU mode), and offline readiness.

## Purpose

Provides an isolated, air-gapped virtualization boundary for:
- UDS (Unicorn Delivery Service) air-gap deployments.
- Multi-node Kubernetes or Talos nested clusters.
- Zero-trust security testing and compliance experiments without risk of WAN leakage.

## Architecture

- **Hypervisor Extensions**: CPU `host-passthrough` exposes `/dev/kvm` directly to guest VMs for performant nested QEMU/KVM virtual machines.
- **Network Isolation**: Dedicated libvirt network with `mode="none"` preventing WAN egress routing while maintaining internal DHCP/DNS.
- **Offline Cloud-Init**: Pre-configures admin users and KVM kernel modules without triggering online package downloads.
- **Modular Python Automation**: Adheres to the `talos-k8s-platform` DRY architecture with [`common.py`](file:///home/bjarrett/Projects/airgapped-sandbox-vm/scripts/common.py), [`configure.py`](file:///home/bjarrett/Projects/airgapped-sandbox-vm/scripts/configure.py), [`doctor.py`](file:///home/bjarrett/Projects/airgapped-sandbox-vm/scripts/doctor.py), and [`preflight_server.py`](file:///home/bjarrett/Projects/airgapped-sandbox-vm/scripts/preflight_server.py).

## Deployment Workflow

### 1. Configure Target Server & SSH Access
Interactively generate dedicated SSH keys, configure `~/.ssh/config`, verify passwordless access, and generate `target.env` and `terraform.tfvars`:

```bash
make configure
```

### 2. Run Workstation Environment Doctor
Verify your local machine has the required binaries (`tofu`/`terraform`, `virsh`, `ssh`, `python3`):

```bash
make doctor
```

### 3. Pre-Flight Validate Remote Hypervisor & Nested KVM
Audit the remote hypervisor server before applying any infrastructure:

```bash
make preflight
```
Validates:
- [x] Passwordless SSH connectivity to target host.
- [x] Hardware virtualization CPU extensions (`vmx` / `svm`).
- [x] Host kernel nested KVM module parameters (`kvm_intel.nested` or `kvm_amd.nested` enabled).
- [x] `/dev/kvm` device existence and read/write permissions.
- [x] Libvirt system service and remote URI responsiveness.
- [x] Libvirt storage pool state and capacity.
- [x] Base cloud image presence.

### 4. Provision the Air-Gapped Sandbox VM
Once pre-flight checks pass:

```bash
make init
make plan
make apply
```

### 5. Inspect State & Connect to Console

```bash
# View domain status, isolated network info, and DHCP leases
make status

# Connect directly to the VM serial console
make console
```

## Available Make Commands

| Command | Description |
| :--- | :--- |
| `make help` | Display available targets and workflow pipeline |
| `make configure` | Interactive SSH key, host alias, `target.env`, and `terraform.tfvars` setup |
| `make doctor` | Audit workstation developer tools (`tofu`, `virsh`, `ssh`, `python3`) |
| `make preflight` | Audit remote target server (CPU flags, nested KVM, libvirt, storage) |
| `make check-host` | Alias for `make preflight` |
| `make init` | Initialize OpenTofu / Terraform providers |
| `make fmt` | Format all OpenTofu configuration files |
| `make validate` | Validate OpenTofu syntax and provider schema |
| `make plan` | Create execution plan saved to `tfplan` |
| `make apply` | Apply changes to provision or update the VM |
| `make status` | Inspect VM domain status, isolated network, and DHCP leases |
| `make console` | Connect to the VM serial console (`virsh console`) |
| `make security` | Run Trivy security and IaC misconfiguration audit |
| `make lint` | Run pre-commit secret scanning and formatting hooks |
| `make hook-install` | Install pre-commit git hooks in `.git/hooks` |
| `make destroy` | Tear down the sandbox VM and isolated network |
| `make clean` | Remove local plan cache |
