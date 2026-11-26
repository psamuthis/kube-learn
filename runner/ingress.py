"""Helpers for the ingress chapter: talk to the ingress controller from the host."""

import http.client
import socket
import ssl
import subprocess

from kube import PROFILE


def node_ip() -> str:
    return subprocess.run(["minikube", "-p", PROFILE, "ip"], capture_output=True, text=True).stdout.strip()


def fetch(k, host: str, path: str, https: bool = False, timeout: int = 5, retries: int = 15):
    """GET http(s)://host/path through the ingress controller. Returns (status, body).
    The controller takes a few seconds to load new Ingresses, so 404/5xx answers are retried."""
    ip = node_ip()

    def once():
        if https:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            raw = socket.create_connection((ip, 443), timeout=timeout)
            sock = ctx.wrap_socket(raw, server_hostname=host)
            conn = http.client.HTTPSConnection(host, 443, timeout=timeout, context=ctx)
            conn.sock = sock
        else:
            conn = http.client.HTTPConnection(ip, 80, timeout=timeout)
        conn.request("GET", path, headers={"Host": host})
        r = conn.getresponse()
        return r.status, r.read().decode(errors="replace"), dict(r.getheaders())

    last = (None, "", {})
    for _ in range(retries):
        try:
            last = once()
            if last[0] not in (404, 502, 503, None):
                return last[0], last[1]
        except OSError as e:
            last = (None, str(e), {})
        import time
        time.sleep(1)
    return last[0], last[1]


def peer_cert(host: str) -> dict:
    """The certificate the ingress controller presents for `host` (SNI), decoded."""
    import tempfile
    import os
    ip = node_ip()
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    with socket.create_connection((ip, 443), timeout=5) as raw, ctx.wrap_socket(raw, server_hostname=host) as s:
        der = s.getpeercert(binary_form=True)
    pem = ssl.DER_cert_to_PEM_cert(der)
    with tempfile.NamedTemporaryFile("w", suffix=".pem", delete=False) as f:
        f.write(pem)
    try:
        out = subprocess.run(["openssl", "x509", "-in", f.name, "-noout", "-subject", "-fingerprint", "-sha256"],
                             capture_output=True, text=True).stdout
    finally:
        os.unlink(f.name)
    return {"text": out, "pem": pem}
