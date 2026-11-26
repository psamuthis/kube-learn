import json

APPLY = ["service.yaml"]  # endpointslice.yaml is applied by the check (see below)

# HINT: A Service without `selector:` gets no automatic endpoints; the EndpointSlice controller leaves it alone.
# HINT: The EndpointSlice's port *name* must equal the Service's port name, and its port is the target (8080).


def setup(k):
    k.apply("""
apiVersion: v1
kind: Pod
metadata:
  name: legacy-db
spec:
  containers:
    - name: db
      image: kubeapp:1.0
      env: [{name: MESSAGE, value: "legacy system online"}]
""")
    k.wait("pod/legacy-db", timeout=90)


def check(k):
    svc = k.get("service", "legacy")
    k.require(svc is not None, "a Service `legacy` exists")
    k.expect(not svc["spec"].get("selector"), "it has no selector")
    path = k.dir / "endpointslice.yaml"
    k.require(path.exists(), "endpointslice.yaml exists")
    text = path.read_text()
    if k.solution:
        text = text.replace("LEGACY_IP", k.jp("pod", "legacy-db", "{.status.podIP}"))
    code, out, err = k.try_kubectl("apply", "-f", "-", input=text)
    k.require(code == 0, "endpointslice.yaml applies", err)
    status, body = k.http("http://legacy/")
    k.expect(status == 200 and json.loads(body).get("message") == "legacy system online", "http://legacy/ reaches legacy-db",
             body[:300])
