variable "aws_region" {
  description = "AWS region to deploy into (eu-north-1 = Stockholm)."
  type        = string
  default     = "eu-north-1"
}

variable "instance_type" {
  description = "EC2 instance type for the QUIC server."
  type        = string
  default     = "t3.micro"
}

variable "key_name" {
  description = "Optional EC2 key pair name for SSH access."
  type        = string
  default     = null
}

variable "admin_cidr" {
  description = "CIDR allowed to SSH to the instance. Restrict this to your IP."
  type        = string
  default     = "0.0.0.0/0"
}

variable "container_image" {
  description = "Container image the instance runs (build & push it first, e.g. to ECR)."
  type        = string
  default     = "ghcr.io/YOUR-ORG/quic-lab:latest"
}

variable "project_name" {
  description = "Resource tag prefix."
  type        = string
  default     = "quic-lab"
}
