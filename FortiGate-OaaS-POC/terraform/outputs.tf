output "fortios_1_public_ip" {
  description = "FortiOS-1 public IP"
  value       = aws_eip.fgt1_wan.public_ip
}

output "fortios_2_public_ip" {
  description = "FortiOS-2 public IP"
  value       = aws_eip.fgt2_wan.public_ip
}

output "fortios_1_admin_url" {
  description = "FortiOS-1 admin URL"
  value       = "https://${aws_eip.fgt1_wan.public_ip}"
}

output "fortios_2_admin_url" {
  description = "FortiOS-2 admin URL"
  value       = "https://${aws_eip.fgt2_wan.public_ip}"
}

output "fortios_1_lan_subnet" {
  description = "FortiOS-1 LAN subnet"
  value       = var.private_subnet_1_cidr
}

output "fortios_2_lan_subnet" {
  description = "FortiOS-2 LAN subnet"
  value       = var.private_subnet_2_cidr
}

output "instance_ids" {
  description = "Instance IDs (use with 'aws ec2 stop-instances' to save costs)"
  value = {
    fortios_1 = aws_instance.fgt1.id
    fortios_2 = aws_instance.fgt2.id
  }
}

output "ssh_commands" {
  description = "SSH commands for each FortiGate"
  value = {
    fortios_1 = "ssh -i ~/.ssh/${var.key_pair_name}.pem admin@${aws_eip.fgt1_wan.public_ip}"
    fortios_2 = "ssh -i ~/.ssh/${var.key_pair_name}.pem admin@${aws_eip.fgt2_wan.public_ip}"
  }
}

output "next_steps" {
  value = <<-EOT

    =============================================
     OaaS POC Deployed Successfully!
    =============================================

     FortiOS-1: https://${aws_eip.fgt1_wan.public_ip}
     FortiOS-2: https://${aws_eip.fgt2_wan.public_ip}
     Login:     admin / <your admin_password>

     Next steps:
      1. Login to each FortiGate (accept self-signed cert)
      2. Upload your FortiFlex BYOL license
      3. Open FortiCloud > Overlay-as-a-Service
      4. Register each spoke using its public EIP

     Verify overlay:
      FortiOS-1 CLI: execute ping 10.200.20.10
      FortiOS-2 CLI: execute ping 10.200.10.10

     Save costs when not in use:
      aws ec2 stop-instances --instance-ids ${aws_instance.fgt1.id} ${aws_instance.fgt2.id}

     Tear down:
      terraform destroy

    =============================================
  EOT
}
