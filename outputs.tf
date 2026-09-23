output "vm_name" {
  description = "Name of the nested hypervisor VM"
  value       = libvirt_domain.nested_hypervisor.name
}

output "network_name" {
  description = "Network to which the VM is connected"
  value       = var.create_isolated_network ? libvirt_network.isolated_net[0].name : var.network_name
}

output "console_command" {
  description = "Command to open the VM console"
  value       = "virsh console ${libvirt_domain.nested_hypervisor.name}"
}
