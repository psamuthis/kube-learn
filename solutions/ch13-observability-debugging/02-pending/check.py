import json

from kube import container, cpu_millis, pod_spec

APPLY = None

# HINT: `kubectl -n ex-13-2 describe pod <pending pod>` → Events → "0/3 nodes are available: …".
# HINT: A request of "20" CPUs doesn't fit on any of your nodes.


def setup(k):
    k.apply("""
apiVersion: apps/v1
kind: Deployment
metadata: {name: worker}
spec:
  replicas: 2
  selector: {matchLabels: {app: worker}}
  template:
    metadata: {labels: {app: worker}}
    spec:
      nodeSelector: {disk: nvme}
      containers:
        - name: app
          image: registry.k8s.io/pause:3.10
          resources: {requests: {cpu: "20", memory: 64Mi}}
""")


def check(k):
    if k.solution and pod_spec(k.get("deployment", "worker")).get("nodeSelector"):
        k.kubectl("patch", "deployment", "worker", "--type=json", "-p", json.dumps([
            {"op": "remove", "path": "/spec/template/spec/nodeSelector"},
            {"op": "replace", "path": "/spec/template/spec/containers/0/resources/requests/cpu", "value": "100m"}]))
    d = k.get("deployment", "worker")
    req = container(d).get("resources", {}).get("requests", {})
    k.expect(cpu_millis(req.get("cpu", "0")) == 100, "the CPU request is 100m", f"{req}")
    k.require(k.rollout("worker", timeout=90), "both worker pods get scheduled and run")
    a = k.answers()
    k.expect_eq(a.get("event_reason"), "FailedScheduling", "event_reason")
    k.expect_eq(a.get("missing_label"), "disk", "missing_label")
