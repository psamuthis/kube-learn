import base64
import json
import subprocess
import tempfile
from pathlib import Path

from ingress import fetch, peer_cert


HOST = "secure.ex83.kube-learn.test"


def make_secret(k):
    with tempfile.TemporaryDirectory() as d:
        subprocess.run(["openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "30",
                        "-keyout", f"{d}/tls.key", "-out", f"{d}/tls.crt", "-subj", f"/CN={HOST}",
                        "-addext", f"subjectAltName=DNS:{HOST}"], capture_output=True, check=True)
        k.kubectl("create", "secret", "tls", "secure-tls", f"--cert={d}/tls.crt", f"--key={d}/tls.key")


def fingerprint(pem: str) -> str:
    return subprocess.run(["openssl", "x509", "-noout", "-fingerprint", "-sha256"], input=pem,
                          capture_output=True, text=True).stdout.strip()


def check(k):
    if k.solution and k.get("secret", "secure-tls") is None:
        make_secret(k)
    sec = k.get("secret", "secure-tls")
    k.require(sec is not None, "a Secret `secure-tls` exists")
    k.expect_eq(sec.get("type"), "kubernetes.io/tls", "the Secret's type")
    crt = base64.b64decode(sec["data"]["tls.crt"]).decode()
    k.require(k.get("ingress", "secure") is not None, "an Ingress `secure` exists")
    k.require(k.rollout("secure"), "the app is rolled out")
    status, body = fetch(k, HOST, "/", https=True)
    k.expect(status == 200 and json.loads(body).get("message") == "secret garden", "https://secure.ex83.kube-learn.test/ works",
             f"HTTP {status} {body[:150]}")
    want = fingerprint(crt)
    served = k.wait_for(lambda: (c := peer_cert(HOST)) and fingerprint(c["pem"]) == want and c, timeout=30) or peer_cert(HOST)
    k.expect(fingerprint(served["pem"]) == want, "the controller presents your certificate", served["text"])
    status, _ = fetch(k, HOST, "/", https=False)
    k.expect(status in (301, 302, 307, 308), "plain HTTP is redirected to HTTPS", f"HTTP {status}")
