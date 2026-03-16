# =============================================================================
# FortiGate OaaS POC - AWS Spoke Deployment
# =============================================================================
# Deploys 2x FortiGate BYOL spokes for FortiCloud Overlay-as-a-Service demo.
#
# Quick start:
#   1. cp terraform.tfvars.example terraform.tfvars
#   2. Edit terraform.tfvars with your values
#   3. terraform init && terraform apply
# =============================================================================

terraform {
  required_version = ">= 1.5"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# =============================================================================
# VPC + NETWORKING
# =============================================================================

resource "aws_vpc" "oaas" {
  cidr_block           = var.vpc_cidr
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags = merge(var.tags, { Name = "${var.project_name}-vpc" })
}

resource "aws_internet_gateway" "igw" {
  vpc_id = aws_vpc.oaas.id
  tags = merge(var.tags, { Name = "${var.project_name}-igw" })
}

# --- WAN Subnets (public, one per FortiGate) ---

resource "aws_subnet" "public_1" {
  vpc_id                  = aws_vpc.oaas.id
  cidr_block              = var.public_subnet_1_cidr
  availability_zone       = var.availability_zone
  map_public_ip_on_launch = false
  tags = merge(var.tags, { Name = "${var.project_name}-public-1-wan" })
}

resource "aws_subnet" "public_2" {
  vpc_id                  = aws_vpc.oaas.id
  cidr_block              = var.public_subnet_2_cidr
  availability_zone       = var.availability_zone
  map_public_ip_on_launch = false
  tags = merge(var.tags, { Name = "${var.project_name}-public-2-wan" })
}

# --- LAN Subnets (private, one per FortiGate) ---

resource "aws_subnet" "private_1" {
  vpc_id            = aws_vpc.oaas.id
  cidr_block        = var.private_subnet_1_cidr
  availability_zone = var.availability_zone
  tags = merge(var.tags, { Name = "${var.project_name}-private-1-lan" })
}

resource "aws_subnet" "private_2" {
  vpc_id            = aws_vpc.oaas.id
  cidr_block        = var.private_subnet_2_cidr
  availability_zone = var.availability_zone
  tags = merge(var.tags, { Name = "${var.project_name}-private-2-lan" })
}

# --- Route Tables ---

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.oaas.id
  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.igw.id
  }
  tags = merge(var.tags, { Name = "${var.project_name}-public-rt" })
}

resource "aws_route_table_association" "public_1" {
  subnet_id      = aws_subnet.public_1.id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table_association" "public_2" {
  subnet_id      = aws_subnet.public_2.id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table" "private_1" {
  vpc_id = aws_vpc.oaas.id
  route {
    cidr_block           = "0.0.0.0/0"
    network_interface_id = aws_network_interface.fgt1_lan.id
  }
  tags = merge(var.tags, { Name = "${var.project_name}-private-1-rt" })
}

resource "aws_route_table" "private_2" {
  vpc_id = aws_vpc.oaas.id
  route {
    cidr_block           = "0.0.0.0/0"
    network_interface_id = aws_network_interface.fgt2_lan.id
  }
  tags = merge(var.tags, { Name = "${var.project_name}-private-2-rt" })
}

resource "aws_route_table_association" "private_1" {
  subnet_id      = aws_subnet.private_1.id
  route_table_id = aws_route_table.private_1.id
}

resource "aws_route_table_association" "private_2" {
  subnet_id      = aws_subnet.private_2.id
  route_table_id = aws_route_table.private_2.id
}

# =============================================================================
# SECURITY GROUPS
# =============================================================================

resource "aws_security_group" "fgt_wan" {
  name_prefix = "${var.project_name}-wan-"
  description = "FortiGate WAN - IPsec, FGFM, admin access"
  vpc_id      = aws_vpc.oaas.id

  # Admin access (restricted to your IP)
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = [var.admin_cidr]
    description = "HTTPS admin"
  }
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.admin_cidr]
    description = "SSH admin"
  }

  # IPsec (required for OaaS overlay)
  ingress {
    from_port   = 500
    to_port     = 500
    protocol    = "udp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "IKE"
  }
  ingress {
    from_port   = 4500
    to_port     = 4500
    protocol    = "udp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "IPsec NAT-T"
  }
  ingress {
    from_port   = 0
    to_port     = 0
    protocol    = "50"
    cidr_blocks = ["0.0.0.0/0"]
    description = "ESP"
  }

  # FortiCloud management
  ingress {
    from_port   = 541
    to_port     = 541
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "FGFM (FortiCloud)"
  }

  # Intra-VPC
  ingress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = [var.vpc_cidr]
    description = "Intra-VPC"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, { Name = "${var.project_name}-wan-sg" })
}

resource "aws_security_group" "fgt_lan" {
  name_prefix = "${var.project_name}-lan-"
  description = "FortiGate LAN - internal traffic"
  vpc_id      = aws_vpc.oaas.id

  ingress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = [var.vpc_cidr]
    description = "All internal"
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, { Name = "${var.project_name}-lan-sg" })
}

# =============================================================================
# NETWORK INTERFACES
# =============================================================================

resource "aws_network_interface" "fgt1_wan" {
  subnet_id         = aws_subnet.public_1.id
  security_groups   = [aws_security_group.fgt_wan.id]
  source_dest_check = false
  private_ips       = ["10.200.1.10"]
  tags = merge(var.tags, { Name = "${var.project_name}-fgt1-wan" })
}

resource "aws_network_interface" "fgt1_lan" {
  subnet_id         = aws_subnet.private_1.id
  security_groups   = [aws_security_group.fgt_lan.id]
  source_dest_check = false
  private_ips       = ["10.200.10.10"]
  tags = merge(var.tags, { Name = "${var.project_name}-fgt1-lan" })
}

resource "aws_network_interface" "fgt2_wan" {
  subnet_id         = aws_subnet.public_2.id
  security_groups   = [aws_security_group.fgt_wan.id]
  source_dest_check = false
  private_ips       = ["10.200.2.10"]
  tags = merge(var.tags, { Name = "${var.project_name}-fgt2-wan" })
}

resource "aws_network_interface" "fgt2_lan" {
  subnet_id         = aws_subnet.private_2.id
  security_groups   = [aws_security_group.fgt_lan.id]
  source_dest_check = false
  private_ips       = ["10.200.20.10"]
  tags = merge(var.tags, { Name = "${var.project_name}-fgt2-lan" })
}

# =============================================================================
# ELASTIC IPs
# =============================================================================

resource "aws_eip" "fgt1_wan" {
  domain = "vpc"
  tags = merge(var.tags, { Name = "${var.project_name}-fgt1-eip" })
}

resource "aws_eip" "fgt2_wan" {
  domain = "vpc"
  tags = merge(var.tags, { Name = "${var.project_name}-fgt2-eip" })
}

resource "aws_eip_association" "fgt1_wan" {
  allocation_id        = aws_eip.fgt1_wan.id
  network_interface_id = aws_network_interface.fgt1_wan.id
}

resource "aws_eip_association" "fgt2_wan" {
  allocation_id        = aws_eip.fgt2_wan.id
  network_interface_id = aws_network_interface.fgt2_wan.id
}

# =============================================================================
# FORTIGATE INSTANCES
# =============================================================================

resource "aws_instance" "fgt1" {
  ami           = var.fortios_ami
  instance_type = var.instance_type
  key_name      = var.key_pair_name

  network_interface {
    network_interface_id = aws_network_interface.fgt1_wan.id
    device_index         = 0
  }
  network_interface {
    network_interface_id = aws_network_interface.fgt1_lan.id
    device_index         = 1
  }

  user_data = templatefile("${path.module}/bootstrap_fgt.tftpl", {
    hostname       = "FortiOS-1"
    admin_password = var.admin_password
    wan_ip         = "10.200.1.10"
    wan_mask       = "255.255.255.0"
    wan_gw         = "10.200.1.1"
    lan_ip         = "10.200.10.10"
    lan_mask       = "255.255.255.0"
  })

  tags = merge(var.tags, { Name = "${var.project_name}-FortiOS-1" })
}

resource "aws_instance" "fgt2" {
  ami           = var.fortios_ami
  instance_type = var.instance_type
  key_name      = var.key_pair_name

  network_interface {
    network_interface_id = aws_network_interface.fgt2_wan.id
    device_index         = 0
  }
  network_interface {
    network_interface_id = aws_network_interface.fgt2_lan.id
    device_index         = 1
  }

  user_data = templatefile("${path.module}/bootstrap_fgt.tftpl", {
    hostname       = "FortiOS-2"
    admin_password = var.admin_password
    wan_ip         = "10.200.2.10"
    wan_mask       = "255.255.255.0"
    wan_gw         = "10.200.2.1"
    lan_ip         = "10.200.20.10"
    lan_mask       = "255.255.255.0"
  })

  tags = merge(var.tags, { Name = "${var.project_name}-FortiOS-2" })
}
