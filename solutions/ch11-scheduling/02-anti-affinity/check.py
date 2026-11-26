import time

from kube import pod_spec

# HINT: `affinity: {podAntiAffinity: {requiredDuringSchedulingIgnoredDuringExecution: [{labelSelector: …, topologyKey: kubernetes.io/hostname}]}}`
# HINT: Preferred terms wrap the term: `[{weight: 100, podAffinityTerm: {labelSelector: …, topologyKey: …}}]`.


def check(k):
    if len(k.node_names()) < 3:
        k.require(False, "this exercise needs the 3-node cluster (./course cluster up)")
    aff = pod_spec(k.get("deployment", "web")).get("affinity", {})
    req = aff.get("podAntiAffinity", {}).get("requiredDuringSchedulingIgnoredDuringExecution", [])
    k.expect(req and req[0].get("topologyKey") == "kubernetes.io/hostname", "required anti-affinity per hostname")
    pref = aff.get("podAffinity", {}).get("preferredDuringSchedulingIgnoredDuringExecution", [])
    k.expect(pref and pref[0].get("weight") == 100
             and pref[0]["podAffinityTerm"]["labelSelector"].get("matchLabels") == {"app": "cache"},
             "preferred affinity (weight 100) to app=cache")
    k.require(k.rollout("web", timeout=90) and k.rollout("cache"), "both Deployments are rolled out")
    nodes = [p["spec"]["nodeName"] for p in k.pods("app=web")]
    k.expect(len(set(nodes)) == 3, "the 3 web replicas are on 3 different nodes", f"{nodes}")
    k.kubectl("scale", "deployment/web", "--replicas=4")
    time.sleep(8)
    pending = [p for p in k.pods("app=web") if p["status"].get("phase") == "Pending"]
    k.expect(len(pending) == 1, "a 4th replica stays Pending", f"{len(pending)} pending")
    if pending:
        ev = [e.get("message", "") for e in k.events(pending[0]["metadata"]["name"]) if e.get("reason") == "FailedScheduling"]
        k.info(ev[0] if ev else "(no FailedScheduling event yet)")
    k.kubectl("scale", "deployment/web", "--replicas=3")
