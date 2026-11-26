
CRDS = "https://github.com/kubernetes-sigs/gateway-api/releases/download/v1.3.0/standard-install.yaml"


def setup(k):
    if k.try_kubectl("get", "crd", "httproutes.gateway.networking.k8s.io", ns=False)[0] != 0:
        k.kubectl("apply", "--server-side", "-f", CRDS, ns=False)
        k.kubectl("wait", "--for=condition=Established", "crd/httproutes.gateway.networking.k8s.io", "--timeout=60s", ns=False)


def check(k):
    gw = k.get("gateway", "public")
    k.require(gw is not None, "a Gateway `public` exists")
    k.expect_eq(gw["spec"].get("gatewayClassName"), "example", "gatewayClassName")
    ls = gw["spec"].get("listeners", [])
    k.expect(len(ls) == 1 and ls[0].get("port") == 80 and ls[0].get("protocol") == "HTTP"
             and ls[0].get("hostname") == "shop.ex84.kube-learn.test", "one HTTP listener on port 80 for the host", f"{ls}")
    rt = k.get("httproute", "shop")
    k.require(rt is not None, "an HTTPRoute `shop` exists")
    s = rt["spec"]
    k.expect([p.get("name") for p in s.get("parentRefs", [])] == ["public"], "it attaches to the Gateway `public`")
    k.expect_eq(s.get("hostnames"), ["shop.ex84.kube-learn.test"], "hostnames")
    weights, beta = {}, None
    for r in s.get("rules", []):
        for m in r.get("matches", []):
            if any(h.get("name") == "x-beta" and h.get("value") == "1" for h in m.get("headers", [])):
                beta = [b["name"] for b in r.get("backendRefs", [])]
            if m.get("path", {}).get("value") == "/" and not m.get("headers"):
                weights = {b["name"]: b.get("weight", 1) for b in r.get("backendRefs", [])}
    k.expect(weights == {"shop": 90, "shop-v2": 10}, "path / splits 90/10 between shop and shop-v2", f"{weights}")
    k.expect(beta == ["shop-v2"], "x-beta: 1 goes to shop-v2 only", f"{beta}")
