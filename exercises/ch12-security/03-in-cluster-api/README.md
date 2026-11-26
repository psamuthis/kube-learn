# Exercise 12.3 — Calling the API from a pod

The pod `lister` (in `pod.yaml`) needs to list the pods of its namespace through the API, using
its ServiceAccount token. Nothing else.

1. Write `rbac.yaml`: a ServiceAccount `lister` with `automountServiceAccountToken: false` (the
   secure default for the ServiceAccount), a Role allowing `list` on pods, and a RoleBinding.
2. Complete `pod.yaml`: run as that ServiceAccount, and opt **this pod** in to the token mount.

Then look inside: `kubectl -n ex-12-3 exec lister -- ls /var/run/secrets/kubernetes.io/serviceaccount/`.
The checker runs a small Python client inside the pod that calls `https://kubernetes.default.svc`
with that token, and expects listing pods to work (200) and listing Secrets to be forbidden (403).
Pods are immutable: use `--fresh` after editing `pod.yaml`.
