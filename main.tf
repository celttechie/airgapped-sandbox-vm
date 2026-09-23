terraform {
  required_version = ">= 1.6.0"
  required_providers {
    libvirt = {
      source  = "dmacvicar/libvirt"
      version = "~> 0.7.0"
    }
  }
}

# Construct provider URI (supports local qemu:///system or remote qemu+ssh://)
provider "libvirt" {
  uri = var.libvirt_uri
}

# 1. Base OS Cloud Image Volume
resource "libvirt_volume" "base_image" {
  name   = "${var.vm_name}-base-image.qcow2"
  pool   = var.storage_pool_name
  source = var.base_image_source
  format = "qcow2"
}

# 2. Copy-on-write Root Disk Volume for Nested Hypervisor Workloads
resource "libvirt_volume" "vm_disk" {
  name           = "${var.vm_name}-disk.qcow2"
  pool           = var.storage_pool_name
  base_volume_id = libvirt_volume.base_image.id
  format         = "qcow2"
  size           = var.disk_size_bytes
}

# 3. Cloud-Init Seed ISO
resource "libvirt_cloudinit_disk" "cloudinit" {
  name = "${var.vm_name}-cloudinit.iso"
  pool = var.storage_pool_name
  user_data = templatefile("${path.module}/templates/cloud_init.cfg", {
    hostname          = var.vm_name
    admin_username    = var.admin_username
    ssh_public_key    = file(pathexpand(var.ssh_public_key_path))
    enable_nested_kvm = var.enable_nested_kvm
  })
}

# 4. Isolated Libvirt Network (Optional: created if create_isolated_network is true)
resource "libvirt_network" "isolated_net" {
  count     = var.create_isolated_network ? 1 : 0
  name      = var.network_name
  mode      = "none" # Isolated air-gap network
  domain    = var.network_domain
  addresses = [var.network_cidr]
  autostart = true

  dhcp {
    enabled = true
  }

  dns {
    enabled    = true
    local_only = true
  }
}

# 5. Nested Sandbox Hypervisor Domain
resource "libvirt_domain" "nested_hypervisor" {
  name   = var.vm_name
  memory = var.vm_memory_mb
  vcpu   = var.vm_vcpu

  # Pass host CPU virtualization flags (/dev/kvm) into guest VM for nested virtualization
  cpu {
    mode = "host-passthrough"
  }

  cloudinit  = libvirt_cloudinit_disk.cloudinit.id
  qemu_agent = var.enable_qemu_agent

  network_interface {
    network_name   = var.create_isolated_network ? libvirt_network.isolated_net[0].name : var.network_name
    wait_for_lease = var.wait_for_lease
  }

  disk {
    volume_id = libvirt_volume.vm_disk.id
  }

  console {
    type        = "pty"
    target_port = "0"
    target_type = "serial"
  }

  graphics {
    type        = "spice"
    listen_type = "address"
    autoport    = true
  }
}
