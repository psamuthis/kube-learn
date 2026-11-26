import json

APPLY = None

# HINT: `kubectl -n ex-13-4 describe pod …` → "couldn't find key … in ConfigMap …".
# HINT: Keys are case-sensitive. Fix either the Deployment's configMapKeyRef or the ConfigMap.


def setup(k):
    k.apply("""
apiVersion: v1
kind: ConfigMap
metadata: {name: shop-settings}
data: {log_level: info}
---
apiVersion: apps/v1
kind: Deployment
metadata: {name: shop}
spec:
  replicas: 1
  selector: {matchLabels: {app: shop}}
  template:
    metadata: {labels: {app: shop}}
    spec:
      containers:
        - name: app
          image: kubeapp:1.0
          env:
            - name: LOG_LEVEL
              valueFrom: {configMapKeyRef: {name: shop-settings, key: LOG_LEVEL}}
          readinessProbe: {httpGet: {path: /ready, port: 8080}, periodSeconds: 2}
          resources: {requests: {cpu: 10m, memory: 32Mi}}
""")


def check(k):
    if k.solution:
        k.kubectl("patch", "deployment", "shop", "--type=json", "-p", json.dumps([
            {"op": "replace", "path": "/spec/template/spec/containers/0/env/0/valueFrom/configMapKeyRef/key", "value": "log_level"}]))
    k.require(k.rollout("shop", timeout=90), "the Deployment `shop` is available")
    ip = k.ready_pods("app=shop")[0]["status"]["podIP"]
    env = json.loads(k.http(f"http://{ip}:8080/env")[1])
    k.expect_eq(env.get("LOG_LEVEL"), "info", "LOG_LEVEL in the container")
    a = k.answers()
    k.expect_eq(a.get("status"), "CreateContainerConfigError", "status")
    k.expect_eq(a.get("wanted_key"), "LOG_LEVEL", "wanted_key")
    k.expect_eq(a.get("actual_key"), "log_level", "actual_key")
