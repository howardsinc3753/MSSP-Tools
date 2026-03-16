#!/bin/bash
# =============================================================================
# FortiGate OaaS POC - Guided Deployment
# =============================================================================
# Just run: bash deploy.sh
# It will walk you through everything step by step.
# =============================================================================

set -e

BOLD='\033[1m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

banner() {
  echo ""
  echo -e "${CYAN}╔══════════════════════════════════════════════════════════╗${NC}"
  echo -e "${CYAN}║${NC}  ${BOLD}FortiGate OaaS POC - Guided Deployment${NC}                  ${CYAN}║${NC}"
  echo -e "${CYAN}║${NC}  Deploy 2x FortiGate BYOL spokes to AWS in ~5 minutes   ${CYAN}║${NC}"
  echo -e "${CYAN}╚══════════════════════════════════════════════════════════╝${NC}"
  echo ""
}

step() {
  echo ""
  echo -e "${GREEN}━━━ Step $1: $2 ━━━${NC}"
  echo ""
}

warn() {
  echo -e "${YELLOW}⚠  $1${NC}"
}

fail() {
  echo -e "${RED}✖  $1${NC}"
  exit 1
}

ok() {
  echo -e "${GREEN}✔  $1${NC}"
}

banner

# ─────────────────────────────────────────────────────────────────────────────
# STEP 1: Check prerequisites
# ─────────────────────────────────────────────────────────────────────────────
step "1/6" "Checking prerequisites"

if ! command -v aws &> /dev/null; then
  fail "AWS CLI not found. Install it: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html"
fi
ok "AWS CLI found"

if ! command -v terraform &> /dev/null; then
  fail "Terraform not found. Install it: https://developer.hashicorp.com/terraform/install"
fi
ok "Terraform found ($(terraform version -json 2>/dev/null | grep -o '"[0-9]\+\.[0-9]\+\.[0-9]\+"' | head -1 || terraform version | head -1))"

echo ""
echo "Checking AWS credentials..."
AWS_IDENTITY=$(aws sts get-caller-identity 2>/dev/null) || fail "AWS credentials not configured. Run: aws configure"
AWS_ACCOUNT=$(echo "$AWS_IDENTITY" | grep -o '"Account": "[^"]*"' | cut -d'"' -f4)
AWS_ARN=$(echo "$AWS_IDENTITY" | grep -o '"Arn": "[^"]*"' | cut -d'"' -f4)
ok "AWS authenticated: $AWS_ARN (Account: $AWS_ACCOUNT)"

# ─────────────────────────────────────────────────────────────────────────────
# STEP 2: Collect configuration
# ─────────────────────────────────────────────────────────────────────────────
step "2/6" "Configuration"

# Region
echo -e "Which ${BOLD}AWS region${NC} do you want to deploy in?"
read -p "  Region [us-east-1]: " INPUT_REGION
AWS_REGION="${INPUT_REGION:-us-east-1}"
ok "Region: $AWS_REGION"

# Availability Zone
AZ_DEFAULT="${AWS_REGION}a"
read -p "  Availability Zone [$AZ_DEFAULT]: " INPUT_AZ
AZ="${INPUT_AZ:-$AZ_DEFAULT}"

# AMI - check if default region
if [ "$AWS_REGION" != "us-east-1" ]; then
  echo ""
  warn "Default AMI is for us-east-1. Looking up the correct AMI for $AWS_REGION..."
  AMI_ID=$(aws ec2 describe-images \
    --owners aws-marketplace \
    --filters "Name=name,Values=*FortiGate-VM64-AWSONDEMAND-ARM64*7.6*" \
    --query 'Images | sort_by(@, &CreationDate) | [-1].ImageId' \
    --output text \
    --region "$AWS_REGION" 2>/dev/null)
  if [ "$AMI_ID" = "None" ] || [ -z "$AMI_ID" ]; then
    fail "Could not find FortiGate BYOL ARM64 AMI in $AWS_REGION. Check that you've subscribed in AWS Marketplace."
  fi
  ok "Found AMI: $AMI_ID"
else
  AMI_ID="ami-0b7030b7e5c00882e"
  ok "Using default AMI: $AMI_ID"
fi

# Key pair
echo ""
echo -e "Available ${BOLD}EC2 key pairs${NC} in $AWS_REGION:"
aws ec2 describe-key-pairs --region "$AWS_REGION" --query 'KeyPairs[*].KeyName' --output table 2>/dev/null || true
echo ""
read -p "  Enter your key pair name: " KEY_PAIR
[ -z "$KEY_PAIR" ] && fail "Key pair name is required for SSH access."
# Validate key pair exists
aws ec2 describe-key-pairs --key-names "$KEY_PAIR" --region "$AWS_REGION" &>/dev/null || fail "Key pair '$KEY_PAIR' not found in $AWS_REGION"
ok "Key pair: $KEY_PAIR"

# Admin password
echo ""
echo -e "Choose a ${BOLD}FortiGate admin password${NC} (min 8 characters):"
read -sp "  Password: " ADMIN_PASS
echo ""
[ ${#ADMIN_PASS} -lt 8 ] && fail "Password must be at least 8 characters."
read -sp "  Confirm:  " ADMIN_PASS_CONFIRM
echo ""
[ "$ADMIN_PASS" != "$ADMIN_PASS_CONFIRM" ] && fail "Passwords don't match."
ok "Password set"

# Admin CIDR
echo ""
echo -e "Restrict admin access to ${BOLD}your IP only${NC}? (recommended)"
MY_IP=$(curl -s ifconfig.me 2>/dev/null || echo "")
if [ -n "$MY_IP" ]; then
  echo "  Your public IP appears to be: $MY_IP"
  read -p "  Lock admin to $MY_IP/32? [Y/n]: " LOCK_IP
  if [ "${LOCK_IP,,}" != "n" ]; then
    ADMIN_CIDR="$MY_IP/32"
  else
    ADMIN_CIDR="0.0.0.0/0"
    warn "Admin access open to all IPs - not recommended for production"
  fi
else
  warn "Could not detect your public IP"
  read -p "  Enter admin CIDR (or press Enter for 0.0.0.0/0): " ADMIN_CIDR
  ADMIN_CIDR="${ADMIN_CIDR:-0.0.0.0/0}"
fi
ok "Admin CIDR: $ADMIN_CIDR"

# ─────────────────────────────────────────────────────────────────────────────
# STEP 3: Check Marketplace subscription
# ─────────────────────────────────────────────────────────────────────────────
step "3/6" "AWS Marketplace subscription"

echo "Verifying FortiGate BYOL ARM64 Marketplace subscription..."
if aws ec2 describe-images --image-ids "$AMI_ID" --region "$AWS_REGION" &>/dev/null; then
  ok "Marketplace subscription active"
else
  echo ""
  warn "You need to accept the FortiGate BYOL ARM64 Marketplace subscription."
  echo "  Open this link and click 'Continue to Subscribe':"
  echo ""
  echo "    https://aws.amazon.com/marketplace/pp?sku=33ndn84xbrajb9vmu5lxnfpjq"
  echo ""
  read -p "  Press Enter once you've subscribed (may take 2-3 minutes to activate)..."
fi

# ─────────────────────────────────────────────────────────────────────────────
# STEP 4: Generate terraform.tfvars
# ─────────────────────────────────────────────────────────────────────────────
step "4/6" "Generating configuration"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TF_DIR="$SCRIPT_DIR/terraform"
cd "$TF_DIR"

cat > terraform.tfvars <<EOF
# Auto-generated by deploy.sh on $(date)
aws_region        = "$AWS_REGION"
availability_zone = "$AZ"
fortios_ami       = "$AMI_ID"
key_pair_name     = "$KEY_PAIR"
admin_password    = "$ADMIN_PASS"
admin_cidr        = "$ADMIN_CIDR"
EOF

ok "terraform.tfvars written"

# ─────────────────────────────────────────────────────────────────────────────
# STEP 5: Review and deploy
# ─────────────────────────────────────────────────────────────────────────────
step "5/6" "Review"

echo -e "  ${BOLD}Region:${NC}         $AWS_REGION ($AZ)"
echo -e "  ${BOLD}Instance Type:${NC}  t4g.small (ARM Graviton)"
echo -e "  ${BOLD}FortiOS AMI:${NC}    $AMI_ID"
echo -e "  ${BOLD}Key Pair:${NC}       $KEY_PAIR"
echo -e "  ${BOLD}Admin CIDR:${NC}     $ADMIN_CIDR"
echo -e "  ${BOLD}Est. Cost:${NC}      ~\$0.52/day (~\$16/month)"
echo ""
echo "  This will create: VPC, 4 subnets, 2 FortiGates, 2 Elastic IPs,"
echo "  Internet Gateway, route tables, and security groups."
echo ""
read -p "  Deploy now? [Y/n]: " CONFIRM
[ "${CONFIRM,,}" = "n" ] && { echo "Cancelled."; exit 0; }

step "6/6" "Deploying"

echo "Initializing Terraform..."
terraform init -input=false

echo ""
echo "Planning..."
terraform plan -input=false -out=oaas.tfplan

echo ""
echo "Applying..."
terraform apply -input=false oaas.tfplan

echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║${NC}  ${BOLD}Deployment Complete!${NC}                                    ${GREEN}║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""
terraform output next_steps
echo ""
echo -e "${YELLOW}Remember: Stop instances when not in use to save costs!${NC}"
echo -e "${YELLOW}  terraform output -json instance_ids${NC}"
echo ""
