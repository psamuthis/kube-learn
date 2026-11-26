# HINT: To select pods in another namespace, put `namespaceSelector` and `podSelector` in the *same* `to:` item (AND).
# HINT: Every namespace carries the label `kubernetes.io/metadata.name: <name>`.
# HINT: CoreDNS listens on port 53 *of the pod* (the Service's port 53 maps to it).


def check(k):
    k.require(k.get("networkpolicy", "client-egress"), "a NetworkPolicy `client-egress` exists")
    k.require(k.rollout("backend"), "the backend is rolled out")
    client = k.toolbox(name="client")
    other = k.toolbox(name="other")
    fqdn = f"backend.{k.ns}.svc.cluster.local"
    ok = k.wait_for(lambda: "Address" in k.sh(f"nslookup {fqdn}", pod=client)[1].split("Name:")[-1], timeout=20)
    k.expect(ok, "client can resolve DNS names")
    ok = k.wait_for(lambda: k.http("http://backend/", pod=client, timeout=3)[0] == 200, timeout=20)
    k.expect(ok, "client → backend works")
    status, _ = k.http("http://ingress-nginx-controller.ingress-nginx/", pod=client, timeout=3)
    k.expect(status is None, "client → ingress controller is blocked", f"HTTP {status}")
    code, out = k.sh("nc -w 3 kubernetes.default.svc.cluster.local 443 </dev/null; echo rc=$?", pod=client)
    k.expect("rc=0" not in out, "client → API server is blocked", out[-200:])
    status, _ = k.http("http://ingress-nginx-controller.ingress-nginx/", pod=other, timeout=3)
    k.expect(status is not None, "other pods are not restricted (other → ingress controller works)", f"HTTP {status}")
