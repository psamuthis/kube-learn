"""The capstone grader: one section per part of the specification (book/ch18-capstone.md, 18.3)."""
import json
import subprocess
import tempfile
import time

from ingress import fetch, node_ip
from kube import container, pod_spec

KUSTOMIZE = "overlays/prod"
HOST = "guestbook.ex18.kube-learn.test"

# HINT: Start small: base with redis.yaml + web.yaml, overlay with just `resources: [../../base]`. Get section 1 green first.
# HINT: Redis under `restricted`: runAsUser/runAsGroup/fsGroup 999, drop ALL, no privilege escalation, seccomp RuntimeDefault (chapter 12.4).
# HINT: The password: `secretGenerator` in the base, then `secretKeyRef: {name: redis-auth, key: password}`; kustomize rewrites the name to the hashed one.
# HINT: redis-server --requirepass needs the value: `command: ["sh", "-c", "exec redis-server --requirepass \"$REDIS_PASSWORD\" --appendonly yes"]`.
# HINT: NetworkPolicy from the ingress controller: `namespaceSelector: {matchLabels: {kubernetes.io/metadata.name: ingress-nginx}}` (chapter 12.5).


def setup(k):
    k.kubectl("label", "namespace", k.ns, "pod-security.kubernetes.io/enforce=restricted",
              "pod-security.kubernetes.io/warn=restricted", "--overwrite", ns=False)


def section(k, title):
    print(f"\n  \033[1m{title}\033[0m")


def make_tls(k):
    with tempfile.TemporaryDirectory() as d:
        subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "30", "-keyout", f"{d}/k",
                        "-out", f"{d}/c", "-subj", f"/CN={HOST}", "-addext", f"subjectAltName=DNS:{HOST}"],
                       capture_output=True, check=True)
        k.kubectl("create", "secret", "tls", "guestbook-tls", f"--cert={d}/c", f"--key={d}/k")


def post(k, text):
    import http.client
    import socket
    import ssl
    ctx = ssl.create_default_context()
    ctx.check_hostname, ctx.verify_mode = False, ssl.CERT_NONE
    conn = http.client.HTTPSConnection(HOST, 443, timeout=5, context=ctx)
    conn.sock = ctx.wrap_socket(socket.create_connection((node_ip(), 443), timeout=5), server_hostname=HOST)
    conn.request("POST", "/guestbook", body=text, headers={"Host": HOST})
    r = conn.getresponse()
    return r.status, r.read().decode()


def check(k):
    if k.solution and k.get("secret", "guestbook-tls") is None:
        make_tls(k)

    section(k, "1. objects")
    sts, web = k.get("statefulset", "redis"), k.get("deployment", "web")
    k.require(sts is not None and web is not None, "StatefulSet `redis` and Deployment `web` exist")
    for kind, name in [("service", "redis"), ("service", "web"), ("hpa", "web"), ("pdb", "web"), ("ingress", "guestbook")]:
        k.expect(k.get(kind, name) is not None, f"{kind} `{name}` exists")
    k.require(k.rollout("redis", kind="statefulset", timeout=180), "redis rolls out",
              "\n".join(e.get("message", "") for e in k.events() if e.get("type") == "Warning")[-800:])
    k.require(k.rollout("web", timeout=120), "web rolls out",
              "\n".join(e.get("message", "") for e in k.events() if e.get("type") == "Warning")[-800:])

    section(k, "2. app")
    k.require(k.get("secret", "guestbook-tls") is not None, "the TLS Secret guestbook-tls exists (see README)")
    stamp = f"signed at {int(time.time())}"
    status, body = 0, ""
    for _ in range(15):
        try:
            status, body = post(k, stamp)
            if status == 201:
                break
        except OSError as e:
            body = str(e)
        time.sleep(1)
    k.expect(status == 201, "POST https://…/guestbook adds an entry", f"HTTP {status} {body[:200]}")
    status, body = fetch(k, HOST, "/guestbook", https=True)
    entries = json.loads(body).get("entries", []) if status == 200 else []
    k.expect(stamp in entries, "GET https://…/guestbook lists it", f"HTTP {status} {body[:200]}")
    status, body = fetch(k, HOST, "/", https=True)
    k.expect(status == 200 and json.loads(body).get("version") == "2.0", "prod runs kubeapp 2.0", body[:200])

    section(k, "3. persistence")
    uid = k.jp("pod", "redis-0", "{.metadata.uid}")
    k.kubectl("delete", "pod", "redis-0")
    k.wait_for(lambda: k.jp("pod", "redis-0", "{.metadata.uid}") not in ("", uid), timeout=60)
    k.rollout("redis", kind="statefulset", timeout=120)
    status, body = 0, ""
    for _ in range(20):
        status, body = fetch(k, HOST, "/guestbook", https=True)
        if status == 200:
            break
        time.sleep(1)
    entries = json.loads(body).get("entries", []) if status == 200 else []
    k.expect(stamp in entries, "the entry survives deleting redis-0", f"HTTP {status} {body[:200]}")

    section(k, "4. security")
    k.expect(k.jp("namespace", k.ns, "{.metadata.labels.pod-security\\.kubernetes\\.io/enforce}", ns=False) == "restricted",
             "the namespace still enforces `restricted`")
    for obj, what in ((web, "web"), (sts, "redis")):
        ps = pod_spec(obj)
        k.expect(ps.get("automountServiceAccountToken") is False, f"{what} mounts no ServiceAccount token")
    k.expect(container(web).get("securityContext", {}).get("readOnlyRootFilesystem") is True, "web has a read-only root filesystem")
    intruder = k.toolbox(name="intruder")
    _, out = k.sh("nc -w 3 redis 6379 </dev/null; echo rc=$?", pod=intruder, timeout=20)
    k.expect("rc=0" not in out, "a non-web pod can't reach redis:6379", out[-200:])
    st, _ = k.http("http://web/", pod=intruder, timeout=3)
    k.expect(st is None, "a random pod can't reach web directly (only the ingress controller can)", f"HTTP {st}")

    section(k, "5. resilience")
    hpa = k.get("hpa", "web")["spec"]
    k.expect(hpa.get("minReplicas") == 2 and hpa.get("maxReplicas") == 5, "HPA web: 2–5 replicas")
    last = json.loads(web["metadata"].get("annotations", {}).get("kubectl.kubernetes.io/last-applied-configuration", "{}"))
    k.expect("replicas" not in last.get("spec", {}), "the Deployment doesn't set replicas (the HPA owns it)")
    k.expect(k.get("pdb", "web")["spec"].get("minAvailable") in (1, "1"), "PDB web: minAvailable 1")
    k.expect(pod_spec(web).get("topologySpreadConstraints"), "web pods are spread (topologySpreadConstraints)")
    k.expect(container(web).get("lifecycle", {}).get("preStop"), "web has a preStop hook")
    k.wait_for(lambda: len(k.ready_pods("app=web")) >= 2, timeout=60)
    k.expect(len(k.ready_pods("app=web")) >= 2, "at least 2 web pods are Ready")

    section(k, "6. config")
    for obj, what in ((web, "web"), (sts, "redis")):
        env = container(obj).get("env", [])
        pw = next((e for e in env if e["name"] == "REDIS_PASSWORD"), {})
        k.expect("secretKeyRef" in pw.get("valueFrom", {}), f"{what} gets REDIS_PASSWORD from a Secret")
    secret = pw.get("valueFrom", {}).get("secretKeyRef", {}).get("name", "")
    k.expect(secret.startswith("redis-auth-"), "the Secret is generated (hash suffix)", secret)
