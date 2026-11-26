import json
import re

APPLY = None

# HINT: staticPodPath is a line in /var/lib/kubelet/config.yaml on the node (`minikube -p kube-learn ssh`).
# HINT: The API server's flags are in its pod spec: `kubectl -n kube-system get pod kube-apiserver-kube-learn -o yaml | grep -- --secure-port`.
# HINT: `kubectl -n kube-system get lease kube-scheduler -o yaml` → spec.holderIdentity.
# HINT: Static pods are owned by the Node they run on: look at metadata.ownerReferences of the apiserver pod.


def flag(pod, name):
    for arg in pod["spec"]["containers"][0].get("command", []) + pod["spec"]["containers"][0].get("args", []):
        if arg.startswith(f"--{name}="):
            return arg.split("=", 1)[1]
    return None


def check(k):
    a = k.answers()
    cp = k.kubectl("get", "nodes", "-l", "node-role.kubernetes.io/control-plane", "-o", "name", ns=False).split()[0].split("/")[1]
    code, cfg = k.ssh(cp, "sudo cat /var/lib/kubelet/config.yaml")
    m = re.search(r"staticPodPath:\s*(\S+)", cfg)
    k.expect(m and a.get("static_pod_path", "").rstrip("/") == m.group(1).rstrip("/"), "static_pod_path",
             f"you wrote {a.get('static_pod_path')!r}")
    api = k.items("pods", "component=kube-apiserver", ns="kube-system")[0]
    etcd = k.items("pods", "component=etcd", ns="kube-system")[0]
    k.expect(a.get("apiserver_port") == flag(api, "secure-port"), "apiserver_port", f"you wrote {a.get('apiserver_port')!r}")
    k.expect(a.get("etcd_data_dir", "").rstrip("/") == (flag(etcd, "data-dir") or "").rstrip("/"), "etcd_data_dir",
             f"you wrote {a.get('etcd_data_dir')!r}")
    rt = k.jp("node", cp, "{.status.nodeInfo.containerRuntimeVersion}", ns=False)
    k.expect(a.get("runtime") == rt, "runtime", f"you wrote {a.get('runtime')!r}")
    holder = k.jp("lease", "kube-scheduler", "{.spec.holderIdentity}", ns="kube-system")
    k.expect(a.get("scheduler_leader") == holder, "scheduler_leader", f"you wrote {a.get('scheduler_leader')!r}")
    owner = api["metadata"].get("ownerReferences", [{}])[0].get("kind")
    k.expect(a.get("apiserver_owner_kind") == owner, "apiserver_owner_kind", f"you wrote {a.get('apiserver_owner_kind')!r}")
