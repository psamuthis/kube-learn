import json
import subprocess

# HINT: openssl req -new -key alice.key -out alice.csr -subj "/CN=alice/O=developers"
# HINT: The CSR's `spec.request` is the base64 of the PEM CSR file: `$(base64 -w0 alice.csr)`.
# HINT: `kubectl config set-cluster/set-credentials/set-context … --kubeconfig=alice.kubeconfig --embed-certs`.


def cleanup(k):
    k.try_kubectl("delete", "csr", "alice-ex162", "--ignore-not-found", ns=False)
    for f in ("alice.key", "alice.crt", "alice.kubeconfig"):
        if k.solution:
            (k.dir / f).unlink(missing_ok=True)


def as_alice(k, *args):
    p = subprocess.run(["kubectl", "--kubeconfig", str(k.dir / "alice.kubeconfig"), *args],
                       capture_output=True, text=True, timeout=30)
    return p.returncode, p.stdout + p.stderr


def check(k):
    if k.solution and not (k.dir / "alice.kubeconfig").exists():
        subprocess.run(["bash", str(k.dir / "make-alice.sh")], capture_output=True, timeout=120)
    csr = k.get("csr", "alice-ex162", ns=False)
    k.require(csr is not None, "a CertificateSigningRequest `alice-ex162` exists")
    conds = [c["type"] for c in csr.get("status", {}).get("conditions", [])]
    k.expect("Approved" in conds, "it was approved")
    k.expect_eq(csr["spec"].get("signerName"), "kubernetes.io/kube-apiserver-client", "the signer")
    k.require((k.dir / "alice.kubeconfig").exists(), "alice.kubeconfig exists in the exercise directory")
    code, out = as_alice(k, "auth", "whoami", "-o", "json")
    k.require(code == 0, "alice.kubeconfig authenticates", out[-500:])
    info = json.loads(out)["status"]["userInfo"]
    k.expect_eq(info.get("username"), "alice", "the username")
    k.expect("developers" in info.get("groups", []), "alice is in the group developers", f"{info.get('groups')}")
    code, out = as_alice(k, "get", "pods", "-n", k.ns)
    k.expect(code == 0, "alice can list pods in ex-16-2", out[-300:])
    code, out = as_alice(k, "auth", "can-i", "delete", "pods", "-n", k.ns)
    k.expect(out.strip().startswith("no"), "alice cannot delete pods")
    code, out = as_alice(k, "get", "pods", "-n", "default")
    k.expect(code != 0 and "forbidden" in out.lower(), "alice cannot list pods in `default`")
    code, out = as_alice(k, "get", "secrets", "-n", k.ns)
    k.expect(code != 0, "alice cannot read Secrets (`view` excludes them)")
