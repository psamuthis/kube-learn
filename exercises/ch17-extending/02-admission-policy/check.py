import time


DEPLOY = """apiVersion: apps/v1
kind: Deployment
metadata:
  name: probe
  labels: {%s}
spec:
  replicas: %d
  selector: {matchLabels: {app: probe}}
  template:
    metadata: {labels: {app: probe}}
    spec: {containers: [{name: c, image: registry.k8s.io/pause:3.10}]}
"""


def cleanup(k):
    k.try_kubectl("delete", "validatingadmissionpolicybinding,validatingadmissionpolicy", "team-and-size-ex172",
                  "--ignore-not-found", ns=False)


def dry(k, labels, replicas, ns=None):
    args = ["apply", "--dry-run=server", "-f", "-"]
    if ns:
        args = ["-n", ns, *args]
    return k.try_kubectl(*args, input=DEPLOY % (labels, replicas), ns=ns is None)


def check(k):
    k.require(k.get("validatingadmissionpolicy", "team-and-size-ex172", ns=False), "the policy exists")
    k.require(k.get("validatingadmissionpolicybinding", "team-and-size-ex172", ns=False), "the binding exists")
    time.sleep(2)  # policies take a moment to be loaded by the API server
    code, _, err = k.wait_for(lambda: (r := dry(k, "", 1)) and r[0] != 0 and r, timeout=20) or dry(k, "", 1)
    k.expect(code != 0 and "team label" in err, "a Deployment without a team label is denied", err or "accepted")
    code, _, err = dry(k, "team: core", 6)
    k.expect(code != 0 and "too many replicas: 6" in err, "6 replicas are denied, with the number in the message", err or "accepted")
    code, _, err = dry(k, "team: core", 3)
    k.expect(code == 0, "a labelled Deployment with 3 replicas is accepted", err)
    code, _, err = dry(k, "", 1, ns="default")
    k.expect(code == 0, "the policy doesn't apply in other namespaces", err)
