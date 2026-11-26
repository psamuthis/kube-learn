#!/usr/bin/env bash
# Creates a ConfigMap through the raw REST API (needs `kubectl proxy --port 8001` running).
set -euo pipefail
NS=ex-2-3
# TODO: curl -X POST … the right URL, with a JSON body and Content-Type: application/json
echo
