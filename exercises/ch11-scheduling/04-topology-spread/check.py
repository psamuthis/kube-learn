from collections import Counter

from kube import pod_spec



def check(k):
    nodes = k.node_names()
    tsc = pod_spec(k.get("deployment", "spread")).get("topologySpreadConstraints", [])
    k.require(tsc, "the pod template has topologySpreadConstraints")
    c = tsc[0]
    k.expect(c.get("maxSkew") == 1 and c.get("topologyKey") == "kubernetes.io/hostname"
             and c.get("whenUnsatisfiable") == "DoNotSchedule", "maxSkew 1 on hostname, DoNotSchedule", f"{c}")
    k.require(k.rollout("spread", timeout=90), "the Deployment is rolled out")
    counts = Counter(p["spec"]["nodeName"] for p in k.pods("app=spread"))
    k.expect(max(counts.values()) - min(counts.get(n, 0) for n in nodes) <= 1,
             "the pods are spread with a skew of at most 1", f"{dict(counts)}")
