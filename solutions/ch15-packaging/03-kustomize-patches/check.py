import json

from kube import container, mem_bytes

KUSTOMIZE = "overlays/hardened"

# HINT: A strategic-merge patch looks like a partial object: the container is matched by `name: app`.
# HINT: Inline JSON patch: `patches: [{target: {kind: Deployment, name: shop}, patch: |- …}]` with a list of `- op: add` operations.


def check(k):
    d = k.get("deployment", "shop")
    k.require(d is not None, "the Deployment `shop` exists")
    c = container(d)
    k.expect(mem_bytes(c.get("resources", {}).get("limits", {}).get("memory", "0")) == 64 * 2**20, "memory limit 64Mi")
    k.expect(c.get("resources", {}).get("requests", {}).get("cpu") == "10m", "the base's requests are still there (merged, not replaced)")
    sc = c.get("securityContext", {})
    k.expect(sc.get("allowPrivilegeEscalation") is False and sc.get("readOnlyRootFilesystem") is True, "the securityContext")
    env = {e["name"]: e.get("value") for e in c.get("env", [])}
    k.expect_eq(env.get("HARDENED"), "true", "the env var HARDENED")
    k.require(k.rollout("shop", timeout=90), "the Deployment is rolled out")
    ip = k.ready_pods("app=shop")[0]["status"]["podIP"]
    k.expect(json.loads(k.http(f"http://{ip}:8080/env")[1]).get("HARDENED") == "true", "the running pod sees HARDENED=true")
