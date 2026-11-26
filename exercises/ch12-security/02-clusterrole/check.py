
SA = "system:serviceaccount:ex-12-2:ops"


def can(k, verb, res, ns="ex-12-2"):
    args = ["auth", "can-i", verb, res, f"--as={SA}"]
    args += ["-n", ns] if ns else []
    return k.try_kubectl(*args, ns=False)[1].strip() == "yes"


def cleanup(k):
    k.try_kubectl("delete", "clusterrole,clusterrolebinding", "node-viewer-ex122", "--ignore-not-found", ns=False)


def check(k):
    k.require(k.get("clusterrole", "node-viewer-ex122", ns=False), "a ClusterRole `node-viewer-ex122` exists")
    k.expect(can(k, "list", "nodes", None), "ops can list nodes")
    k.expect(not can(k, "delete", "nodes", None), "ops cannot delete nodes")
    k.expect(can(k, "create", "deployments.apps"), "ops can create Deployments in ex-12-2")
    k.expect(can(k, "delete", "pods"), "ops can delete pods in ex-12-2")
    k.expect(not can(k, "create", "deployments.apps", "default"), "ops cannot create Deployments in `default`")
    k.expect(not can(k, "create", "rolebindings.rbac.authorization.k8s.io"), "ops cannot create RoleBindings (edit excludes RBAC)")
    rb = k.get("rolebinding", "ops-edit")
    k.expect(rb and rb["roleRef"]["kind"] == "ClusterRole" and rb["roleRef"]["name"] == "edit",
             "ops-edit is a RoleBinding to the ClusterRole `edit`")
