#!/usr/bin/env bash
#
# Convenience wrapper: run terraform in local-validation mode.
# Usage:
#   scripts/tf-local.sh fmt
#   scripts/tf-local.sh validate
#   scripts/tf-local.sh init
#   scripts/tf-local.sh plan        # (uses environments/local/terraform.tfvars)
#
# This never contacts Azure. Real deploys live in environments/dev/.

set -euo pipefail

cd "$(dirname "$0")/.."

action="${1:-help}"

tf_bin="$(command -v terraform || true)"
if [[ -z "$tf_bin" ]]; then
  echo "terraform not found. Install via: brew install hashicorp/tap/terraform" >&2
  exit 127
fi

cd terraform

case "$action" in
  fmt)
    terraform fmt -recursive -diff
    ;;
  validate)
    [[ -d .terraform ]] || terraform init -backend=false -input=false
    terraform validate
    ;;
  init)
    terraform init -backend=false -input=false -upgrade
    ;;
  plan)
    [[ -d .terraform ]] || terraform init -backend=false -input=false
    terraform plan -var-file=environments/local/terraform.tfvars
    ;;
  help|*)
    cat <<EOF
Usage: scripts/tf-local.sh <command>

Commands:
  fmt       Run 'terraform fmt' recursively (with diff).
  validate  Run 'terraform validate' (auto-inits backend-less).
  init      'terraform init -backend=false' (no remote state).
  plan      'terraform plan' against environments/local/terraform.tfvars.
  help      Show this message.
EOF
    ;;
esac
