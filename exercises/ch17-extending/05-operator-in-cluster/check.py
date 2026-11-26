import shutil
import subprocess
import tempfile

from kube import PROFILE


SA = "system:serviceaccount:ex-17-5:kv-operator"
KV = """
apiVersion: kube-learn.dev/v1
kind: KeyValueStore
metadata: {name: sessions}
spec: {replicas: 1, version: "7.4"}
"""


def cleanup(k):
    k.try_kubectl("delete", "kvs", "--all", "--ignore-not-found")


def can(k, verb, res):
    res, _, sub = res.partition("/")
    extra = [f"--subresource={sub}"] if sub else []
    return k.try_kubectl("auth", "can-i", verb, res, *extra, f"--as={SA}", "-n", k.ns, ns=False)[1].strip() == "yes"


def build(k):
    ch = k.dir.parent
    with tempfile.TemporaryDirectory() as ctx:
        shutil.copy(k.dir / "Dockerfile", ctx)
        shutil.copy(ch / "04-operator" / "kv_operator.py", ctx)
        shutil.copy(ch / "03-reconcile" / "reconcile.py", ctx)
        p = subprocess.run(["docker", "build", "-q", "-t", "kv-operator:dev", ctx], capture_output=True, text=True, timeout=600)
    k.require(p.returncode == 0, "the image kv-operator:dev builds", p.stderr[-1500:])
    p = subprocess.run(["minikube", "-p", PROFILE, "image", "load", "--overwrite", "kv-operator:dev"],
                       capture_output=True, text=True, timeout=300)
    k.require(p.returncode == 0, "the image loads into the cluster", p.stderr[-800:])


def check(k):
    k.kubectl("apply", "-f", str(k.dir.parent / "04-operator" / "crd.yaml"), ns=False)
    k.require(k.wait("crd/keyvaluestores.kube-learn.dev", "condition=Established", timeout=30), "the CRD is installed")
    build(k)
    k.kubectl("rollout", "restart", "deployment/kv-operator")
    k.require(k.rollout("kv-operator", timeout=90), "the operator Deployment is available",
              k.try_kubectl("logs", "deploy/kv-operator", "--tail=20")[1])
    for verb, res, want in [("watch", "keyvaluestores.kube-learn.dev", True), ("patch", "keyvaluestores.kube-learn.dev/status", True), ("patch", "keyvaluestores.kube-learn.dev", False),
                            ("create", "statefulsets.apps", True), ("delete", "pods", False), ("list", "secrets", False),
                            ("delete", "keyvaluestores.kube-learn.dev", False)]:
        k.expect(can(k, verb, res) == want, f"the operator {'can' if want else 'cannot'} {verb} {res}")
    k.apply(KV)
    k.require(k.wait_for(lambda: k.get("statefulset", "sessions"), timeout=40), "the in-cluster operator creates the StatefulSet",
              k.try_kubectl("logs", "deploy/kv-operator", "--tail=20")[1])
    k.require(k.rollout("sessions", kind="statefulset", timeout=180), "the Redis pod becomes Ready")
    ok = k.wait_for(lambda: k.jp("kvs", "sessions", "{.status.phase}") == "Ready", timeout=30)
    k.expect(ok, "the KeyValueStore's status is Ready", k.try_kubectl("logs", "deploy/kv-operator", "--tail=20")[1])
