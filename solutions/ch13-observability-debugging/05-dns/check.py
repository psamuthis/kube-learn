import json

from kube import pod_spec

APPLY = None

# HINT: `kubectl -n ex-13-5 exec deploy/resolver -- cat /etc/resolv.conf`, then `kubectl -n ex-13-5 get deploy resolver -o yaml | grep -A5 dns`.
# HINT: Remove `dnsPolicy: None` and the `dnsConfig` (or set dnsPolicy: ClusterFirst).


def setup(k):
    k.apply("""
apiVersion: apps/v1
kind: Deployment
metadata: {name: resolver}
spec:
  replicas: 1
  selector: {matchLabels: {app: resolver}}
  template:
    metadata: {labels: {app: resolver}}
    spec:
      dnsPolicy: None
      dnsConfig:
        nameservers: [10.96.0.99]
        searches: [svc.cluster.local]
      containers:
        - name: app
          image: busybox:1.37
          command: ["sleep", "infinity"]
          resources: {requests: {cpu: 5m, memory: 8Mi}}
""")


def check(k):
    if k.solution and pod_spec(k.get("deployment", "resolver")).get("dnsPolicy") == "None":
        k.kubectl("patch", "deployment", "resolver", "--type=json", "-p", json.dumps([
            {"op": "remove", "path": "/spec/template/spec/dnsConfig"},
            {"op": "replace", "path": "/spec/template/spec/dnsPolicy", "value": "ClusterFirst"}]))
    k.require(k.rollout("resolver", timeout=90), "the Deployment `resolver` is available")
    pod = k.ready_pods("app=resolver")[0]["metadata"]["name"]
    code, out = k.exec(pod, "nslookup", "kubernetes.default.svc.cluster.local", timeout=20)
    k.expect(code == 0 and "Address" in out.split("Name:")[-1], "kubernetes.default.svc.cluster.local resolves", out[-300:])
    a = k.answers()
    k.expect_eq(a.get("bad_nameserver"), "10.96.0.99", "bad_nameserver")
    k.expect_eq(a.get("good_policy"), "ClusterFirst", "good_policy")
