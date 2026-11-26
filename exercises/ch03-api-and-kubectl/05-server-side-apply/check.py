import json

APPLY = None


PLATFORM = """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
spec:
  replicas: 2
  selector:
    matchLabels: {app: web}
  template:
    metadata:
      labels: {app: web}
    spec:
      containers:
        - name: kubeapp
          image: kubeapp:1.0
          resources:
            requests: {cpu: 10m, memory: 32Mi}
            limits: {memory: 64Mi}
"""


def setup(k):
    k.kubectl("apply", "--server-side", "--field-manager=team-platform", "-f", "-", input=PLATFORM)


def owns(entry, path):
    node = entry.get("fieldsV1", {})
    for step in path:
        if step not in node:
            return False
        node = node[step]
    return True


def check(k):
    if k.solution:
        k.kubectl("apply", "--server-side", "--field-manager=team-app", "--force-conflicts", "-f", str(k.dir / "image.yaml"))
    d = k.get("deployment", "web", managed=True)
    k.require(d is not None, "deployment web exists")
    img = d["spec"]["template"]["spec"]["containers"][0]["image"]
    k.expect_eq(img, "kubeapp:2.0", "the image")
    mf = {m["manager"]: m for m in d["metadata"].get("managedFields", []) if m.get("operation") == "Apply"}
    k.require("team-app" in mf, "team-app has applied fields (manager `team-app`, operation Apply)",
              f"Apply managers: {list(mf)}")
    c = 'k:{"name":"kubeapp"}'
    path = ["f:spec", "f:template", "f:spec", "f:containers", c, "f:image"]
    k.expect(owns(mf["team-app"], path), "team-app owns the container image")
    k.expect(not owns(mf.get("team-platform", {}), path), "team-platform no longer owns the image")
    k.expect(owns(mf.get("team-platform", {}), ["f:spec", "f:replicas"]), "team-platform still owns spec.replicas")
    k.expect(not owns(mf["team-app"], ["f:spec", "f:replicas"]), "team-app doesn't claim replicas")
    k.expect(not owns(mf["team-app"], ["f:spec", "f:template", "f:spec", "f:containers", c, "f:resources"]),
             "team-app doesn't claim resources")
    k.expect_eq(d["spec"]["replicas"], 2, "replicas")
