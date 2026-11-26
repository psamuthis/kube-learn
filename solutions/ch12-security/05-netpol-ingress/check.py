# HINT: `podSelector: {}` selects every pod in the namespace; `policyTypes: [Ingress]` with no `ingress:` rules allows nothing.
# HINT: The port in a NetworkPolicy is the *pod's* port (8080), not the Service's (80): policies see traffic after kube-proxy's DNAT.


def check(k):
    k.require(k.get("networkpolicy", "default-deny-ingress") and k.get("networkpolicy", "backend-from-frontend"),
              "both NetworkPolicies exist")
    k.require(k.rollout("backend"), "the backend is rolled out")
    front = k.toolbox(name="frontend")
    intruder = k.toolbox(name="intruder")
    ok = k.wait_for(lambda: k.http("http://backend/", pod=front, timeout=3)[0] == 200, timeout=20)
    k.expect(ok, "frontend → backend works")
    status, _ = k.http("http://backend/", pod=intruder, timeout=3)
    k.expect(status is None, "intruder → backend is blocked", f"got HTTP {status}")
    ip = k.ready_pods("app=backend")[0]["status"]["podIP"]
    status, _ = k.http(f"http://{ip}:8080/", pod=intruder, timeout=3)
    k.expect(status is None, "intruder → backend pod IP directly is blocked too", f"got HTTP {status}")
