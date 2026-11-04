output "instance_public_ip" {
  description = "Public IP of the QUIC lab server."
  value       = aws_instance.quic_lab.public_ip
}

output "quic_endpoint" {
  description = "QUIC endpoint for the client."
  value       = "${aws_instance.quic_lab.public_ip}:443/udp"
}

output "ssh_command" {
  description = "SSH hint (only if key_name was set)."
  value       = "ssh ubuntu@${aws_instance.quic_lab.public_ip}"
}
