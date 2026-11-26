

def check(k):
    svc = k.get("service", "peers")
    k.require(svc is not None, "a Service `peers` exists")
    k.expect_eq(svc["spec"].get("clusterIP"), "None", "clusterIP")
    k.require(k.rollout("peer"), "the Deployment is rolled out")
    ips = {p["status"]["podIP"] for p in k.ready_pods("app=peer")}
    def lookup():
        _, out = k.sh(f"nslookup peers.{k.ns}.svc.cluster.local")
        return out if all(ip in out for ip in ips) else None
    out = k.wait_for(lookup, timeout=20)
    k.expect(out, "DNS returns the IPs of all 3 pods", f"pods: {sorted(ips)}")
