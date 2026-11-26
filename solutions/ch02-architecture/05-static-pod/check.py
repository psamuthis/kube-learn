import subprocess

from kube import PROFILE

APPLY = None

# HINT: The kubelet's staticPodPath on minikube nodes is /etc/kubernetes/manifests.
# HINT: Mirror pods are named <pod name>-<node name>.
# HINT: The kubelet owns a static pod; deleting the mirror only deletes the API's *copy*, and the kubelet re-creates it.


def node(k):
    names = k.node_names()
    return "kube-learn-m02" if "kube-learn-m02" in names else names[0]


def cleanup(k):
    k.ssh(node(k), "sudo rm -f /etc/kubernetes/manifests/static-web.yaml")


def check(k):
    n = node(k)
    name = f"static-web-{n}"
    if k.solution and k.get("pod", name) is None:
        subprocess.run(["minikube", "-p", PROFILE, "cp", str(k.dir / "static-web.yaml"), f"{n}:/tmp/static-web.yaml"],
                       capture_output=True, timeout=60)
        k.ssh(n, "sudo cp /tmp/static-web.yaml /etc/kubernetes/manifests/static-web.yaml")
    pod = k.wait_for(lambda: k.get("pod", name), timeout=60, what="mirror pod")
    k.require(pod is not None, f"a mirror pod `{name}` exists in {k.ns}",
              f"is static-web.yaml in /etc/kubernetes/manifests on {n}, with namespace: {k.ns}?")
    k.expect("kubernetes.io/config.mirror" in pod["metadata"].get("annotations", {}), "it's a mirror pod")
    k.expect(k.wait(f"pod/{name}", timeout=90), "it becomes Ready")
    a = k.answers()
    k.expect_eq(a.get("mirror_pod_name"), name, "mirror_pod_name")
    k.expect(a.get("gone_after_delete", "").lower() in ("no", "n", "false"), "gone_after_delete",
             "try it and watch `kubectl get pods -w`")
    k.expect_eq(a.get("mirror_annotation"), "kubernetes.io/config.mirror", "mirror_annotation")
