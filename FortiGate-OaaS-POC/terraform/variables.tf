# =============================================================================
# FortiGate OaaS POC - Variables
# =============================================================================
# Copy terraform.tfvars.example to terraform.tfvars and set your values.
# =============================================================================

# --- REQUIRED: You must set these in terraform.tfvars ---

variable "key_pair_name" {
  description = "Name of an existing EC2 key pair for SSH access"
  type        = string
}

variable "admin_password" {
  description = "FortiGate admin password (min 8 chars, use something strong)"
  type        = string
  sensitive   = true
}

# --- RECOMMENDED: Restrict admin access to your IP ---

variable "admin_cidr" {
  description = "CIDR allowed for HTTPS/SSH admin access (e.g. '203.0.113.50/32'). Use 'curl ifconfig.me' to find your public IP."
  type        = string
  default     = "0.0.0.0/0"
}

# --- OPTIONAL: Override defaults if needed ---

variable "aws_region" {
  description = "AWS region for deployment"
  type        = string
  default     = "us-east-1"
}

variable "availability_zone" {
  description = "Availability zone (same AZ for both = simpler + cheaper for POC)"
  type        = string
  default     = "us-east-1a"
}

variable "fortios_ami" {
  description = "FortiGate 7.6.6 BYOL ARM64 AMI (default is us-east-1; change if using a different region)"
  type        = string
  default     = "ami-0b7030b7e5c00882e"
}

variable "instance_type" {
  description = "EC2 instance type - t4g.small is the cheapest option for FortiGate"
  type        = string
  default     = "t4g.small"
}

variable "project_name" {
  description = "Name prefix for all resources (makes it easy to find/clean up)"
  type        = string
  default     = "oaas-poc"
}

# --- NETWORK: Defaults work out of the box, change only if conflicts ---

variable "vpc_cidr" {
  description = "VPC CIDR block"
  type        = string
  default     = "10.200.0.0/16"
}

variable "public_subnet_1_cidr" {
  description = "WAN subnet for FortiOS-1"
  type        = string
  default     = "10.200.1.0/24"
}

variable "public_subnet_2_cidr" {
  description = "WAN subnet for FortiOS-2"
  type        = string
  default     = "10.200.2.0/24"
}

variable "private_subnet_1_cidr" {
  description = "LAN subnet behind FortiOS-1"
  type        = string
  default     = "10.200.10.0/24"
}

variable "private_subnet_2_cidr" {
  description = "LAN subnet behind FortiOS-2"
  type        = string
  default     = "10.200.20.0/24"
}

variable "tags" {
  description = "Tags applied to all resources"
  type        = map(string)
  default = {
    Project     = "OaaS-POC"
    Environment = "lab"
    ManagedBy   = "terraform"
  }
}
