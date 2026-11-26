import json
import time

from kube import container, cpu_millis

# HINT: Utilization is a percentage of the CPU *request*: without one, the HPA shows <unknown>.
# HINT: `scaleTargetRef: {apiVersion: apps/v1, kind: Deployment, name: web}`
# HINT: If `replicas:` stays in the file, every apply resets the HPA's decision.

LOAD = """
apiVersion: apps/v1
kind: Deployment
metadata: {name: load}
spec:
  replicas: 1
  selector: {matchLabels: {app: load}}
  template:
    metadata: {labels: {app: load}}
    spec:
      terminationGracePeriodSeconds: 0
      containers:
        - name: load
          image: busybox:1.37
          command: ["sh", "-c", "for i in 1 2 3 4 5 6; do (while :; do wget -q -O /dev/null -T 5 'http://web/cpu?ms=100'; done) & done; wait"]
          resources: {requests: {cpu: 10m, memory: 16Mi}}
"""


def check(k):
    d = k.get("deployment", "web")
    last = json.loads(d["metadata"].get("annotations", {}).get("kubectl.kubernetes.io/last-applied-configuration", "{}"))
    k.expect("replicas" not in last.get("spec", {}), "deployment.yaml doesn't set replicas")
    k.expect(cpu_millis(container(d).get("resources", {}).get("requests", {}).get("cpu", "0")) == 50, "the CPU request is 50m")
    hpa = k.get("hpa", "web")
    k.require(hpa is not None, "an HPA `web` exists")
    s = hpa["spec"]
    k.expect(s.get("minReplicas") == 1 and s.get("maxReplicas") == 5, "min 1, max 5")
    m = s.get("metrics", [{}])[0].get("resource", {})
    k.expect(m.get("name") == "cpu" and m.get("target", {}).get("averageUtilization") == 50, "target: 50% CPU")
    k.require(k.rollout("web"), "the Deployment is rolled out")
    k.info("waiting for the HPA to read metrics…")
    util = "{.status.currentMetrics[0].resource.current.averageUtilization}"
    k.require(k.wait_for(lambda: k.jp("hpa", "web", util) != "", timeout=240, interval=5),
              "the HPA gets CPU metrics (metrics-server)")
    k.apply(LOAD)
    k.info("load generator started; waiting for a scale-up (up to 3 minutes)…")
    try:
        up = k.wait_for(lambda: int(k.jp("hpa", "web", "{.status.desiredReplicas}") or 0) > 1, timeout=180, interval=5)
        k.expect(up, "the HPA scales web beyond 1 replica under load",
                 k.kubectl("describe", "hpa", "web")[-600:])
        if up:
            k.info(f"desired replicas: {k.jp('hpa', 'web', '{.status.desiredReplicas}')}")
    finally:
        k.delete("deployment", "load", wait=False)
