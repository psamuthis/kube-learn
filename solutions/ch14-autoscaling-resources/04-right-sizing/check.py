import json

from kube import container, cpu_millis, mem_bytes

# HINT: `kubectl -n ex-14-4 top pods` shows MEMORY(bytes) like 21Mi.
# HINT: Round the request up a little: requests are what the scheduler reserves; usage fluctuates.


def usage(k):
    data = json.loads(k.kubectl("get", "--raw", f"/apis/metrics.k8s.io/v1beta1/namespaces/{k.ns}/pods", ns=False))
    return [mem_bytes(c["usage"]["memory"]) for p in data["items"] if p["metadata"]["name"].startswith("sized-")
            for c in p["containers"]]


def check(k):
    k.require(k.rollout("sized", timeout=90), "the Deployment is rolled out")
    r = container(k.get("deployment", "sized")).get("resources", {})
    req = mem_bytes(r.get("requests", {}).get("memory", "0"))
    lim = mem_bytes(r.get("limits", {}).get("memory", "0"))
    k.expect(cpu_millis(r.get("requests", {}).get("cpu", "0")) <= 50, "the CPU request is at most 50m", f"{r}")
    k.expect(req <= lim <= 256 * 2**20, "a memory limit between the request and 256Mi", f"{r}")
    k.info("waiting for metrics of the new pods…")
    used = k.wait_for(lambda: (u := usage(k)) and len(u) >= 2 and u, timeout=120, interval=5)
    k.require(used, "metrics-server reports the pods' memory")
    peak = max(used)
    k.expect(peak <= req <= 2 * peak + 16 * 2**20, f"the memory request fits the measured usage ({peak // 2**20}Mi)",
             f"request {req // 2**20}Mi, allowed {peak // 2**20}–{(2 * peak + 16 * 2**20) // 2**20}Mi")
