import re

APPLY = None

# HINT: `kubectl cluster-info` prints "Kubernetes control plane is running at https://…".
# HINT: CoreDNS pods are in kube-system and carry the label k8s-app=kube-dns: `kubectl -n kube-system get pods -l k8s-app=kube-dns -o yaml | grep image:`
# HINT: `kubectl get pods -n kube-system -o wide` has a NODE column.
# HINT: `kubectl get node kube-learn-m02 -o yaml` and look under `spec:`.


def check(k):
    a = k.answers()
    server = k.kubectl("config", "view", "--minify", "-o", "jsonpath={.clusters[0].cluster.server}", ns=False)
    k.expect(a.get("api_server", "").rstrip("/") == server.rstrip("/"), "api_server", f"you wrote {a.get('api_server')!r}")
    dns = k.items("pods", "k8s-app=kube-dns", ns="kube-system")
    images = {c["image"] for p in dns for c in p["spec"]["containers"]}
    k.expect(a.get("coredns_image") in images, "coredns_image", f"you wrote {a.get('coredns_image')!r}")
    sched = k.items("pods", "component=kube-scheduler", ns="kube-system")
    k.expect(a.get("scheduler_node") in {p["spec"].get("nodeName") for p in sched}, "scheduler_node",
             f"you wrote {a.get('scheduler_node')!r}")
    names = [n["metadata"]["name"] for n in k.items("namespaces", ns=False)]
    count = sum(1 for n in names if n.startswith("kube-"))
    k.expect(a.get("kube_namespaces") == str(count), "kube_namespaces", f"you wrote {a.get('kube_namespaces')!r}")
    nodes = k.node_names()
    if "kube-learn-m02" in nodes:
        cidr = k.jp("node", "kube-learn-m02", "{.spec.podCIDR}", ns=False)
        k.expect(a.get("m02_pod_cidr") == cidr, "m02_pod_cidr", f"you wrote {a.get('m02_pod_cidr')!r}")
