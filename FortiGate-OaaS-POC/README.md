# FortiGate OaaS POC - AWS Spoke Deployment

Deploy 2x FortiGate BYOL spokes in AWS for a **FortiCloud Overlay-as-a-Service** proof-of-concept demo.

## What Gets Deployed

| Resource | Details |
|----------|---------|
| VPC | 10.200.0.0/16 with Internet Gateway |
| FortiOS-1 | WAN: 10.200.1.10 + Elastic IP, LAN: 10.200.10.0/24 |
| FortiOS-2 | WAN: 10.200.2.10 + Elastic IP, LAN: 10.200.20.0/24 |
| Instance Type | t4g.small (ARM Graviton) - ~$0.52/day for both |
| FortiOS Version | 7.6.6 BYOL (ARM64) |
| Security Groups | HTTPS, SSH, IKE/IPsec, FGFM (FortiCloud) |

## Prerequisites

- **AWS CLI** configured with valid credentials (`aws configure`)
- **Terraform** >= 1.5 installed
- **AWS Marketplace**: Accept the [FortiGate BYOL ARM64 subscription](https://aws.amazon.com/marketplace/pp?sku=33ndn84xbrajb9vmu5lxnfpjq) (free - BYOL means you bring your own FortiFlex license)
- **AWS Key Pair**: An existing EC2 key pair in your target region for SSH access
- **FortiFlex License**: 2x FortiGate VM BYOL entitlements

> **New to AWS?** Follow our step-by-step [AWS Setup Guide](docs/AWS-SETUP-GUIDE.md) to create an account, get your API keys, and install all the tools.

## Quick Start (5 minutes)

### Step 1: Configure

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` with your values:

```hcl
aws_region     = "us-east-1"          # Your preferred region
key_pair_name  = "my-key"             # Your existing EC2 key pair
admin_password = "MySecurePass123!"   # FortiGate admin password (change this!)
admin_cidr     = "203.0.113.50/32"    # Your public IP for admin access (recommended)
```

> **Security Tip**: Set `admin_cidr` to your public IP (`curl ifconfig.me`) instead of `0.0.0.0/0` to restrict admin access.

### Step 2: Deploy

```bash
terraform init
terraform plan
terraform apply
```

Terraform will output the public IPs when complete (~2 minutes).

### Step 3: Access FortiGates

1. Browse to **https://\<FortiOS-1-Public-IP\>** (accept the self-signed certificate)
2. Login: `admin` / your `admin_password`
3. Upload your FortiFlex BYOL license via **System > FortiGuard > Upload License**
4. Repeat for FortiOS-2

### Step 4: Register as OaaS Spokes

1. Login to [FortiCloud](https://support.fortinet.com)
2. Navigate to **Overlay-as-a-Service**
3. Run the spoke registration wizard using each FortiGate's public EIP
4. The bootstrap config already has `central-management` pointed to FortiCloud

### Step 5: Verify Overlay Connectivity

From FortiOS-1 CLI:
```
execute ping 10.200.20.10
```
From FortiOS-2 CLI:
```
execute ping 10.200.10.10
```

## Cost Management

Estimated running cost: **~$0.52/day** (~$16/month) for both instances.

**Stop instances when not in use:**
```bash
terraform output -json instance_ids
aws ec2 stop-instances --instance-ids <id1> <id2>
```

**Restart when ready:**
```bash
aws ec2 start-instances --instance-ids <id1> <id2>
```

**Tear down completely:**
```bash
terraform destroy
```

## Changing AWS Region

The default AMI (`ami-0b7030b7e5c00882e`) is for **us-east-1** only. If you deploy to a different region, find the correct FortiGate 7.6.6 BYOL ARM64 AMI:

```bash
aws ec2 describe-images \
  --owners aws-marketplace \
  --filters "Name=name,Values=*FortiGate-VM64-AWSONDEMAND-ARM64*7.6.6*" \
  --query 'Images[*].[ImageId,Name]' \
  --output table \
  --region YOUR-REGION
```

Then set `fortios_ami` in your `terraform.tfvars`.

## Architecture

```
                    ┌──────────────────────────────────────────┐
                    │          FortiCloud OaaS Hub             │
                    └──────────┬──────────────┬────────────────┘
                         IPsec │              │ IPsec
                    ┌──────────┴──┐     ┌─────┴────────┐
                    │  EIP (auto) │     │  EIP (auto)   │
    ┌───────────────┼─────────────┼─────┼───────────────┼──────┐
    │ VPC           │             │     │               │      │
    │ 10.200.0.0/16 │             │     │               │      │
    │               │             │     │               │      │
    │  ┌────────────┴──────┐  ┌──┴─────────────────┐          │
    │  │ FortiOS-1         │  │ FortiOS-2          │          │
    │  │ WAN: 10.200.1.10  │  │ WAN: 10.200.2.10   │          │
    │  │ LAN: 10.200.10.10 │  │ LAN: 10.200.20.10  │          │
    │  └────────┬──────────┘  └──┬─────────────────┘          │
    │           │                │                             │
    │  ┌────────┴──────┐  ┌─────┴──────────┐                  │
    │  │ LAN Subnet    │  │ LAN Subnet     │                  │
    │  │ 10.200.10.0/24│  │ 10.200.20.0/24 │                  │
    │  └───────────────┘  └────────────────┘                  │
    └─────────────────────────────────────────────────────────┘
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "OptInRequired" error | Accept the [AWS Marketplace subscription](https://aws.amazon.com/marketplace/pp?sku=33ndn84xbrajb9vmu5lxnfpjq) and wait 2-3 minutes |
| Can't reach admin HTTPS | Wait 2-3 min after deploy for FortiOS to boot. Check `admin_cidr` allows your IP |
| License warning on login | Expected for BYOL - upload your FortiFlex license |
| Overlay tunnel not coming up | Ensure FGFM (TCP 541) and IPsec (UDP 500/4500) are not blocked upstream |
