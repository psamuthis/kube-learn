
CLIENT = r'''
import json, ssl, sys, urllib.request
base = "/var/run/secrets/kubernetes.io/serviceaccount/"
token = open(base + "token").read()
ns = open(base + "namespace").read()
ctx = ssl.create_default_context(cafile=base + "ca.crt")
for res in ("pods", "secrets"):
    req = urllib.request.Request(f"https://kubernetes.default.svc/api/v1/namespaces/{ns}/{res}",
                                 headers={"Authorization": "Bearer " + token})
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=5) as r:
            print(res, r.status, len(json.load(r)["items"]))
    except urllib.error.HTTPError as e:
        print(res, e.code, 0)
'''


def check(k):
    sa = k.get("serviceaccount", "lister")
    k.require(sa is not None, "a ServiceAccount `lister` exists")
    k.expect(sa.get("automountServiceAccountToken") is False, "the ServiceAccount doesn't automount tokens by default")
    pod = k.get("pod", "lister")
    k.expect_eq(pod["spec"].get("serviceAccountName"), "lister", "the pod's serviceAccountName")
    k.require(k.wait("pod/lister", timeout=90), "the pod is Ready")
    code, out = k.exec("lister", "python", "-c", CLIENT)
    k.require(code == 0, "the in-pod client runs (is the token mounted?)", out[-500:])
    res = {l.split()[0]: l.split()[1:] for l in out.strip().splitlines()}
    k.expect(res.get("pods", ["?"])[0] == "200", "listing pods from inside the pod returns 200", out)
    k.expect(res.get("secrets", ["?"])[0] == "403", "listing secrets from inside the pod returns 403", out)
