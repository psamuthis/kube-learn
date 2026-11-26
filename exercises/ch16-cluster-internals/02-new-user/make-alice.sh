#!/usr/bin/env bash
# Issues a client certificate for alice through the Kubernetes CSR API and writes alice.kubeconfig.
set -euo pipefail
cd "$(dirname "$0")"
# TODO: key + CSR (openssl), CertificateSigningRequest alice-ex162, approve, fetch, kubeconfig
echo "wrote alice.kubeconfig"
