from kube import container, mem_bytes

# HINT: `resources: {requests: {cpu: 100m, memory: 64Mi}, limits: {cpu: 100m, memory: 64Mi}}`
# HINT: If you set only limits, Kubernetes copies them into requests, which is also Guaranteed.


def check(k):
    for name, want in (("guaranteed", "Guaranteed"), ("burstable", "Burstable"), ("besteffort", "BestEffort")):
        pod = k.get("pod", name)
        k.require(pod is not None, f"pod {name} exists")
        k.expect_eq(pod.get("status", {}).get("qosClass"), want, f"{name}'s QoS class")
    g = container(k.get("pod", "guaranteed"))["resources"]
    k.expect(g.get("limits", {}).get("cpu") == "100m" and mem_bytes(g.get("limits", {}).get("memory", "0")) == 64 * 2**20,
             "guaranteed uses 100m CPU and 64Mi memory")
    b = container(k.get("pod", "burstable"))["resources"]
    k.expect(mem_bytes(b.get("requests", {}).get("memory", "0")) == 32 * 2**20
             and mem_bytes(b.get("limits", {}).get("memory", "0")) == 128 * 2**20,
             "burstable requests 32Mi and is limited to 128Mi")
