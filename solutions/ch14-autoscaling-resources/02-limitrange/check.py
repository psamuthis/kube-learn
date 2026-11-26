from kube import cpu_millis, mem_bytes

# HINT: `default` is for limits, `defaultRequest` is for requests.
# HINT: The LimitRange only affects pods created *after* it.

POD = """
apiVersion: v1
kind: Pod
metadata: {name: %s}
spec:
  containers:
    - name: app
      image: registry.k8s.io/pause:3.10
%s
"""


def check(k):
    k.require(k.get("limitrange", "defaults") is not None, "a LimitRange `defaults` exists")
    k.delete("pod", "naked")
    k.apply(POD % ("naked", ""))
    r = k.get("pod", "naked")["spec"]["containers"][0].get("resources", {})
    req, lim = r.get("requests", {}), r.get("limits", {})
    k.expect(cpu_millis(req.get("cpu", "0")) == 50 and mem_bytes(req.get("memory", "0")) == 64 * 2**20,
             "a pod without resources gets requests 50m / 64Mi", f"{r}")
    k.expect(cpu_millis(lim.get("cpu", "0")) == 200 and mem_bytes(lim.get("memory", "0")) == 128 * 2**20,
             "…and limits 200m / 128Mi", f"{r}")
    big = POD % ("greedy", "      resources: {limits: {memory: 512Mi}}")
    code, out, err = k.try_kubectl("apply", "--dry-run=server", "-f", "-", input=big)
    k.expect(code != 0 and "maximum" in err, "a pod with a 512Mi memory limit is rejected", err or out)
