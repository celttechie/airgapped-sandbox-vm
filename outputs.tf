output "vm_name" {
  description = "Name of the nested hypervisor VM"
  value       = libvirt_domain.nested_hypervisor.name
}

output "network_name" {
  description = "Network to which the VM is connected"
  value       = var.create_isolated_network ? libvirt_network.isolated_net[0].name : var.network_name
}

output "libvirt_uri" {
  description = "Target hypervisor connection URI"
  value       = var.libvirt_uri
}

output "console_command" {
  description = "Command to open the VM console"
  value       = "virsh -c ${var.libvirt_uri} console ${libvirt_domain.nested_hypervisor.name}"
}

output "make_console_command" {
  description = "Convenient make command to open the VM console"
  value       = "make console"
}
