
SA = "system:serviceaccount:ex-12-1:reader"

MATRIX = [
    ("get", "pods", True), ("list", "pods", True), ("watch", "pods", True), ("get", "pods/log", True),
    ("delete", "pods", False), ("create", "pods", False), ("create", "pods/exec", False),
    ("get", "secrets", False), ("list", "deployments.apps", False), ("get", "configmaps", False),
]


def can(k, verb, res, ns=None):
    code, out, _ = k.try_kubectl("auth", "can-i", verb, res, f"--as={SA}", "-n", ns or k.ns, ns=False)
    return out.strip() == "yes"


def check(k):
    k.require(k.get("serviceaccount", "reader"), "a ServiceAccount `reader` exists")
    for verb, res, want in MATRIX:
        k.expect(can(k, verb, res) == want, f"reader {'can' if want else 'cannot'} {verb} {res}")
    k.expect(not can(k, "list", "pods", "default"), "reader cannot list pods in another namespace")
