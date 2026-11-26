import json
import time

APPLY = None

# HINT: `{.items[*].metadata.name}` lists names; pipe through `tr ' ' '\n' | sort | xargs` to sort them.
# HINT: `--sort-by=.metadata.creationTimestamp` sorts oldest first.
# HINT: Filters: `{.spec.containers[?(@.name=="sidecar")].image}`. Escape dots in keys: `{.metadata.annotations.kube-learn\.dev/owner}`.
# HINT: `--field-selector=status.phase!=Running`. Careful: the checker's toolbox pod may exist too. Filter with `-l kube-learn.dev/quiz`.

PAUSE = "registry.k8s.io/pause:3.10"


def pod(name, labels, containers, annotations=None, restart="Always"):
    return {"apiVersion": "v1", "kind": "Pod",
            "metadata": {"name": name, "labels": {"kube-learn.dev/quiz": "3.2", **labels},
                         "annotations": annotations or {}},
            "spec": {"restartPolicy": restart, "terminationGracePeriodSeconds": 0,
                     "containers": [{"name": n, "image": i, **({"command": c} if c else {})}
                                    for n, i, c in containers]}}


def setup(k):
    specs = [
        pod("db", {"tier": "backend", "app": "shop"}, [("main", PAUSE, None)]),
        pod("api", {"tier": "backend", "app": "shop"},
            [("main", PAUSE, None), ("sidecar", "busybox:1.37", ["sleep", "infinity"])]),
        pod("cache", {"tier": "backend", "app": "shop"}, [("main", PAUSE, None)],
            annotations={"kube-learn.dev/owner": "team-falcon"}),
        pod("web", {"tier": "frontend", "app": "shop"}, [("main", PAUSE, None)]),
        pod("migrate", {"tier": "batch", "app": "shop"}, [("main", "busybox:1.37", ["sh", "-c", "exit 3"])],
            restart="Never"),
    ]
    for s in specs:
        k.kubectl("apply", "-f", "-", input=json.dumps(s))
        time.sleep(1.1)  # distinct creation timestamps (1 s resolution)
    k.wait_for(lambda: k.jp("pod", "migrate", "{.status.phase}") == "Failed", timeout=90)


def check(k):
    a = k.answers()
    pods = k.pods("kube-learn.dev/quiz")
    backend = " ".join(sorted(p["metadata"]["name"] for p in pods if p["metadata"]["labels"].get("tier") == "backend"))
    k.expect_eq(a.get("backend_pods"), backend, "backend_pods")
    oldest = min(pods, key=lambda p: p["metadata"]["creationTimestamp"])["metadata"]["name"]
    k.expect_eq(a.get("oldest_pod"), oldest, "oldest_pod")
    k.expect_eq(a.get("api_sidecar_image"), "busybox:1.37", "api_sidecar_image")
    k.expect_eq(a.get("not_running"), "migrate", "not_running")
    k.expect_eq(a.get("cache_owner"), "team-falcon", "cache_owner")
    total = sum(len(p["spec"]["containers"]) for p in pods)
    k.expect_eq(a.get("total_containers"), str(total), "total_containers")
