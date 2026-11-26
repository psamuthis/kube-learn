import json

APPLY = None

# HINT: Comma means AND. There's no OR across keys, but `key in (v1,v2)` is an OR on one key's values.
# HINT: `!key` means the label is absent; a bare `key` means it's present.
# HINT: `tier!=db` also matches pods that have no tier label at all.

PODS = {
    "a": {"app": "shop", "env": "prod", "tier": "web", "release": "stable", "team": "red"},
    "b": {"app": "shop", "env": "prod", "tier": "db", "release": "stable"},
    "c": {"app": "shop", "env": "staging", "tier": "web", "team": "blue"},
    "d": {"app": "blog", "env": "prod", "tier": "web", "team": "red"},
    "e": {"app": "blog", "env": "dev", "tier": "db", "release": "canary"},
    "f": {"app": "shop", "env": "dev", "tier": "web"},
}
EXPECTED = {"q1": "a b", "q2": "a c d", "q3": "c d f", "q4": "d", "q5": "a c"}


def setup(k):
    for name, labels in PODS.items():
        k.kubectl("apply", "-f", "-", input=json.dumps({
            "apiVersion": "v1", "kind": "Pod", "metadata": {"name": name, "labels": labels},
            "spec": {"terminationGracePeriodSeconds": 0,
                     "containers": [{"name": "main", "image": "registry.k8s.io/pause:3.10"}]}}))


def check(k):
    a = k.answers("selectors.txt")
    for q, want in EXPECTED.items():
        sel = a.get(q, "")
        if not sel:
            k.expect(False, f"{q} has a selector")
            continue
        code, out, err = k.try_kubectl("get", "pods", "-l", sel, "-o", "jsonpath={.items[*].metadata.name}")
        got = " ".join(sorted(n for n in out.split() if n in PODS)) if code == 0 else f"error: {err.strip()}"
        k.expect(got == want, f"{q}: `{sel}` selects {want}", f"it selects: {got or '(nothing)'}")
