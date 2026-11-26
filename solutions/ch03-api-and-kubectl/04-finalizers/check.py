APPLY = None

# HINT: Look at `metadata:` in `kubectl get cm stuck -o yaml`: there's a timestamp you didn't see on other objects, and a list.
# HINT: kubectl patch cm stuck --type=merge -p '{"metadata":{"finalizers":null}}'


def setup(k):
    k.kubectl("apply", "-f", "-", input="""
apiVersion: v1
kind: ConfigMap
metadata:
  name: stuck
  finalizers: [kube-learn.dev/never]
data:
  state: doomed
""")
    k.kubectl("delete", "configmap", "stuck", "--wait=false")


def cleanup(k):
    k.try_kubectl("patch", "configmap", "stuck", "--type=merge", "-p", '{"metadata":{"finalizers":null}}')


def check(k):
    a = k.answers()
    k.expect_eq(a.get("deletion_field"), "deletionTimestamp", "deletion_field")
    k.expect_eq(a.get("finalizer"), "kube-learn.dev/never", "finalizer")
    k.expect(a.get("data_editable", "").lower() in ("no", "n", "false"), "data_editable",
             "try: kubectl -n ex-3-4 patch cm stuck -p '{\"data\":{\"state\":\"saved\"}}'")
    if k.solution:
        cleanup(k)
    gone = k.wait_for(lambda: k.get("configmap", "stuck") is None, timeout=10)
    k.expect(gone, "the ConfigMap `stuck` is finally gone")
