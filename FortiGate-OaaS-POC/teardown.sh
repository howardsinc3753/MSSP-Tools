#!/bin/bash
# =============================================================================
# FortiGate OaaS POC - Teardown
# =============================================================================
# Destroys all resources created by deploy.sh
# Run: bash teardown.sh
# =============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BOLD='\033[1m'
NC='\033[0m'

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TF_DIR="$SCRIPT_DIR/terraform"
cd "$TF_DIR"

echo ""
echo -e "${RED}╔══════════════════════════════════════════════════════════╗${NC}"
echo -e "${RED}║${NC}  ${BOLD}FortiGate OaaS POC - Teardown${NC}                            ${RED}║${NC}"
echo -e "${RED}╚══════════════════════════════════════════════════════════╝${NC}"
echo ""

if [ ! -f terraform.tfstate ]; then
  echo "No terraform.tfstate found - nothing to destroy."
  exit 0
fi

echo "This will destroy ALL OaaS POC resources:"
echo ""
terraform output fortios_1_admin_url 2>/dev/null && true
terraform output fortios_2_admin_url 2>/dev/null && true
echo ""

read -p "Are you sure? Type 'destroy' to confirm: " CONFIRM
if [ "$CONFIRM" != "destroy" ]; then
  echo "Cancelled."
  exit 0
fi

echo ""
terraform destroy -auto-approve

echo ""
echo -e "${GREEN}All OaaS POC resources have been destroyed.${NC}"
echo ""
