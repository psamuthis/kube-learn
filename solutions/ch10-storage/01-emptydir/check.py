import json

# HINT: `volumes: [{name: data, emptyDir: {}}]` and a matching `volumeMounts` entry.
# HINT: `minikube -p kube-learn ssh -n <node> -- sudo ls /var/lib/kubelet/pods/<uid>/volumes/`


def hits(k):
    ip = k.ready_pods("app=counter")[0]["status"]["podIP"]
    return json.loads(k.http(f"http://{ip}:8080/hits")[1])


def check(k):
    k.require(k.rollout("counter"), "the Deployment is rolled out")
    first = hits(k)
    k.require(first.get("stored_in") == "/data/hits", "kubeapp stores its counter in /data/hits", f"{first}")
    n = hits(k)["hits"]
    pod = k.ready_pods("app=counter")[0]
    k.http(f"http://{pod['status']['podIP']}:8080/crash")
    k.wait_for(lambda: k.jp("pod", pod["metadata"]["name"], "{.status.containerStatuses[0].restartCount}") not in ("", "0"), timeout=30)
    k.require(k.wait_for(lambda: k.ready_pods("app=counter"), timeout=60), "the container comes back")
    after = hits(k)["hits"]
    k.expect(after == n + 1, "the counter survived the container restart", f"{n} → {after}")
    a = k.answers()
    k.expect(a.get("survives_container_restart", "").lower() in ("yes", "y"), "survives_container_restart")
    k.expect(a.get("survives_pod_deletion", "").lower() in ("no", "n"), "survives_pod_deletion")
    k.expect_eq(a.get("plugin_dir"), "kubernetes.io~empty-dir", "plugin_dir")
