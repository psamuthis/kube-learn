#!/usr/bin/env bash
# Creates a ConfigMap through the raw REST API (needs `kubectl proxy --port 8001` running).
set -euo pipefail
NS=ex-2-3
#>>
#| # TODO: curl -X POST … the right URL, with a JSON body and Content-Type: application/json
curl -sS -X POST "http://localhost:8001/api/v1/namespaces/$NS/configmaps" \
  -H 'Content-Type: application/json' \
  -d '{
    "apiVersion": "v1",
    "kind": "ConfigMap",
    "metadata": {"name": "made-by-curl"},
    "data": {"greeting": "hello", "language": "http"}
  }'
#<<
echo
