variable "libvirt_uri" {
  type        = string
  description = "Libvirt connection URI"
  default     = "qemu:///system"
}

variable "vm_name" {
  type        = string
  description = "Name of the nested hypervisor sandbox VM"
  default     = "airgapped-sandbox-hypervisor"
}

variable "vm_memory_mb" {
  type        = number
  description = "Memory allocated to the VM in MB"
  default     = 32768
}

variable "vm_vcpu" {
  type        = number
  description = "Number of vCPUs allocated to the VM"
  default     = 8
}

variable "storage_pool_name" {
  type        = string
  description = "Libvirt storage pool name"
  default     = "default"
}

variable "base_image_source" {
  type        = string
  description = "Path or URL to the base cloud image"
  default     = "https://cloud-images.ubuntu.com/releases/22.04/release/ubuntu-22.04-server-cloudimg-amd64.img"
}

variable "disk_size_bytes" {
  type        = number
  description = "Size of VM disk volume in bytes (e.g. 64424509440 = 60GB)"
  default     = 64424509440
}

variable "create_isolated_network" {
  type        = bool
  description = "Whether to create a dedicated isolated network or attach to an existing one"
  default     = true
}

variable "network_name" {
  type        = string
  description = "Libvirt network name"
  default     = "airgap-sandbox-net"
}

variable "network_cidr" {
  type        = string
  description = "Network CIDR block"
  default     = "10.160.0.0/24"
}

variable "network_domain" {
  type        = string
  description = "Domain name for network DNS"
  default     = "sandbox.local"
}

variable "admin_username" {
  type        = string
  description = "Default user in the VM"
  default     = "sandboxadmin"
}

variable "ssh_public_key_path" {
  type        = string
  description = "Path to SSH public key for authentication"
  default     = "~/.ssh/id_sandbox_hypervisor_ed25519.pub"
}

variable "enable_nested_kvm" {
  type        = bool
  description = "Enable nested KVM hypervisor tools and libvirt daemon in guest"
  default     = true
}

variable "enable_qemu_agent" {
  type        = bool
  description = "Enable QEMU guest agent communication channel in the domain"
  default     = false
}

variable "wait_for_lease" {
  type        = bool
  description = "Whether OpenTofu should block and wait for a DHCP lease on the interface"
  default     = false
}
