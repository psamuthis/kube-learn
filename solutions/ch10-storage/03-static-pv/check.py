import json

# HINT: In the PVC, `volumeName: archive-ex103` binds to that exact PV; `storageClassName: ""` must match the PV's.
# HINT: nodeAffinity: `{required: {nodeSelectorTerms: [{matchExpressions: [{key: kubernetes.io/hostname, operator: In, values: [kube-learn-m03]}]}]}}`

PV = "archive-ex103"


def node(k):
    names = k.node_names()
    return "kube-learn-m03" if "kube-learn-m03" in names else names[0]


def setup(k):
    k.ssh(node(k), "sudo mkdir -p /data/archive-ex103 && echo 'archived treasure' | sudo tee /data/archive-ex103/README.txt")


def cleanup(k):
    k.try_kubectl("delete", "pod", "reader", "--ignore-not-found")
    k.try_kubectl("delete", "pvc", "archive", "--ignore-not-found")
    k.try_kubectl("delete", "pv", PV, "--ignore-not-found", ns=False)


def check(k):
    pv = k.get("pv", PV, ns=False)
    k.require(pv is not None, f"a PersistentVolume `{PV}` exists")
    k.expect_eq(pv["spec"].get("persistentVolumeReclaimPolicy"), "Retain", "reclaim policy")
    k.expect_eq(pv["spec"].get("storageClassName", ""), "", "the PV's storage class")
    pvc = k.get("pvc", "archive")
    k.require(pvc is not None, "a PVC `archive` exists")
    k.expect_eq(pvc["spec"].get("volumeName"), PV, "the claim's volumeName")
    k.require(k.wait_for(lambda: k.jp("pvc", "archive", "{.status.phase}") == "Bound", timeout=30), "the claim is Bound")
    k.require(k.wait("pod/reader", timeout=90), "the pod `reader` is Ready")
    k.expect_eq(k.jp("pod", "reader", "{.spec.nodeName}"), node(k), "the node the pod was scheduled on")
    ip = k.jp("pod", "reader", "{.status.podIP}")
    files = json.loads(k.http(f"http://{ip}:8080/config")[1]).get("files", {})
    k.expect(files.get("README.txt", "").strip() == "archived treasure", "the pod reads the archived file", f"{files}")
