import json

# HINT: `ports: [{name: http, port: 80, targetPort: http}]`: targetPort can be a port *name*.


def check(k):
    svc = k.get("service", "web")
    k.require(svc is not None, "a Service `web` exists")
    p = svc["spec"]["ports"][0]
    k.expect_eq(p.get("port"), 80, "the Service port")
    k.expect_eq(p.get("targetPort"), "http", "the targetPort (by name)")
    k.require(k.rollout("web"), "the Deployment is rolled out")
    slices = k.items("endpointslices", "kubernetes.io/service-name=web")
    eps = [e for s in slices for e in s.get("endpoints") or [] if e.get("conditions", {}).get("ready")]
    k.expect(len(eps) == 2, "the Service has 2 ready endpoints", f"{len(eps)} ready endpoints")
    hosts = set()
    for url in ["http://web/"] * 8 + ["http://web.ex-7-1.svc.cluster.local/"] * 2:
        status, body = k.http(url)
        k.require(status == 200, f"{url} answers", body[:200])
        hosts.add(json.loads(body)["hostname"])
    k.expect(len(hosts) == 2, "traffic reaches both pods", f"answered by {sorted(hosts)}")
