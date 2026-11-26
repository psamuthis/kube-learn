import random

APPLY = None

# HINT: `kubectl -n ex-13-7 top pods` shows CPU in millicores (m). If it says "metrics not available yet", wait a minute.
# HINT: kubectl -n ex-13-7 scale deployment <name> --replicas=0

SCRIPT = 'if [ "$MODE" = burn ]; then while :; do :; done; else sleep infinity; fi'


def setup(k):
    hog = random.choice(["alpha", "bravo", "charlie"])
    for name in ("alpha", "bravo", "charlie"):
        mode = "burn" if name == hog else "idle"
        k.kubectl("create", "configmap", f"{name}-mode", f"--from-literal=MODE={mode}")
        k.apply(f"""
apiVersion: apps/v1
kind: Deployment
metadata: {{name: {name}}}
spec:
  replicas: 1
  selector: {{matchLabels: {{app: {name}}}}}
  template:
    metadata: {{labels: {{app: {name}}}}}
    spec:
      terminationGracePeriodSeconds: 0
      containers:
        - name: app
          image: busybox:1.37
          command: ["sh", "-c", '{SCRIPT}']
          envFrom: [{{configMapRef: {{name: {name}-mode}}}}]
          resources: {{requests: {{cpu: 10m, memory: 8Mi}}, limits: {{cpu: 150m, memory: 16Mi}}}}
""")


def check(k):
    hog = next(n for n in ("alpha", "bravo", "charlie") if k.jp("configmap", f"{n}-mode", "{.data.MODE}") == "burn")
    if k.solution:
        k.wait_for(lambda: "m" in k.try_kubectl("top", "pods", "--no-headers")[1], timeout=120, interval=5)
    a = k.answers()
    k.expect_eq(a.get("hog"), hog, "hog")
    m = a.get("millicores", "").rstrip("m")
    k.expect(m.isdigit() and 100 <= int(m) <= 160, "millicores is about the hog's CPU limit (150m)", f"you wrote {m!r}")
    if k.solution:
        k.kubectl("scale", f"deployment/{hog}", "--replicas=0")
    k.expect(k.jp("deployment", hog, "{.spec.replicas}") == "0", f"the hog `{hog}` is scaled to 0")
    others = [n for n in ("alpha", "bravo", "charlie") if n != hog]
    k.expect(all(k.jp("deployment", n, "{.spec.replicas}") == "1" for n in others), "the other two are untouched")
