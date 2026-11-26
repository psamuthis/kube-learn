import urllib.request

# HINT: `type: NodePort` and, in the port entry, `nodePort: 30080` (next to port and targetPort).


def check(k):
    svc = k.get("service", "web")
    k.require(svc is not None, "a Service `web` exists")
    k.expect_eq(svc["spec"].get("type"), "NodePort", "the type")
    k.expect_eq(svc["spec"]["ports"][0].get("nodePort"), 30080, "the nodePort")
    k.require(k.rollout("web"), "the Deployment is rolled out")
    for n in k.nodes():
        ip = next(a["address"] for a in n["status"]["addresses"] if a["type"] == "InternalIP")
        def get():
            with urllib.request.urlopen(f"http://{ip}:30080/", timeout=3) as r:
                return r.status == 200
        ok = k.wait_for(get, timeout=20)
        k.expect(ok, f"http://{ip}:30080/ answers from your machine ({n['metadata']['name']})")
