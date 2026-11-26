import json

from kube import container

APPLY = None


DEPLOY = """
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
  annotations: {kubernetes.io/change-cause: "%s"}
spec:
  replicas: 3
  progressDeadlineSeconds: 20
  strategy: {rollingUpdate: {maxSurge: 1, maxUnavailable: 0}}
  selector: {matchLabels: {app: web}}
  template:
    metadata: {labels: {app: web}}
    spec:
      containers:
        - name: app
          image: %s
          readinessProbe: {httpGet: {path: /ready, port: 8080}, periodSeconds: 2}
          resources: {requests: {cpu: 10m, memory: 32Mi}}
"""


def setup(k):
    k.apply(DEPLOY % ("first release", "kubeapp:1.0"))
    k.rollout("web", timeout=120)
    k.apply(DEPLOY % ("upgrade to 1.1", "kubeapp:1.1"))


def check(k):
    a = k.answers()
    k.expect(a.get("broken_pod_status") in ("ImagePullBackOff", "ErrImagePull"), "broken_pod_status",
             f"you wrote {a.get('broken_pod_status')!r}")
    k.expect_eq(a.get("progressing_reason"), "ProgressDeadlineExceeded", "progressing_reason")
    k.expect_eq(a.get("old_pods_running"), "3", "old_pods_running")
    if k.solution and container(k.get("deployment", "web"))["image"] != "kubeapp:1.0":
        k.wait_for(lambda: "ProgressDeadlineExceeded" in k.jp("deployment", "web", "{.status.conditions}"), timeout=60)
        k.kubectl("rollout", "undo", "deployment/web")
    d = k.get("deployment", "web")
    k.expect_eq(container(d)["image"], "kubeapp:1.0", "the image is back to kubeapp:1.0")
    k.require(k.rollout("web", timeout=90), "the Deployment is healthy again")
    rss = k.items("replicasets", "app=web")
    broken = [r for r in rss if container(r)["image"] == "kubeapp:1.1"]
    k.expect(broken and broken[0]["spec"]["replicas"] == 0, "the broken ReplicaSet still exists, scaled to 0",
             "did you delete and recreate instead of `rollout undo`?")
    rev = int(d["metadata"].get("annotations", {}).get("deployment.kubernetes.io/revision", "0"))
    k.expect(rev >= 3, "the rollback is a new revision (≥ 3)", f"revision {rev}")
