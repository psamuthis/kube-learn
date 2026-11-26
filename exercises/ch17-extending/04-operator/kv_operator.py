#!/usr/bin/env python3
"""kv-operator: turns KeyValueStore objects into a Redis StatefulSet + Service.

Standard library only. Talks to the API server either through `kubectl proxy` (--api URL, for
development) or, when running in a pod, with the ServiceAccount token (in-cluster config).
"""

import argparse
import json
import os
import ssl
import sys
import time
import traceback
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))                                   # in the image: reconcile.py next to us
sys.path.insert(1, str(HERE.parent / "03-reconcile"))           # in the course: your solution to 17.3
from reconcile import MANAGER, compute_status, reconcile  # noqa: E402

GROUP, VERSION, PLURAL = "kube-learn.dev", "v1", "keyvaluestores"
SA_DIR = Path("/var/run/secrets/kubernetes.io/serviceaccount")


def log(msg: str):
    print(f"{time.strftime('%H:%M:%S')} {msg}", flush=True)


class Api:
    """A minimal Kubernetes API client."""

    def __init__(self, base: str, token: str | None = None, ca: str | None = None):
        self.base = base.rstrip("/")
        self.headers = {"Authorization": f"Bearer {token}"} if token else {}
        self.ctx = ssl.create_default_context(cafile=ca) if ca else None

    @classmethod
    def from_env(cls, api_url: str | None) -> "Api":
        if api_url:
            return cls(api_url)
        host, port = os.environ.get("KUBERNETES_SERVICE_HOST"), os.environ.get("KUBERNETES_SERVICE_PORT", "443")
        if not host:
            sys.exit("not in a cluster: pass --api http://127.0.0.1:8001 (and run `kubectl proxy --port 8001`)")
        return cls(f"https://{host}:{port}", (SA_DIR / "token").read_text(), str(SA_DIR / "ca.crt"))

    def request(self, method: str, path: str, body=None, content_type: str = "application/json", timeout: float = 10):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(self.base + path, data=data, method=method,
                                     headers={**self.headers, "Content-Type": content_type, "Accept": "application/json"})
        with urllib.request.urlopen(req, context=self.ctx, timeout=timeout) as r:
            return json.load(r)

    def get(self, path: str) -> dict | None:
        """GET an object; None if it doesn't exist."""
        try:
            return self.request("GET", path)
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            raise

    def apply(self, obj: dict) -> dict:
        """Server-side apply `obj` (create or update), owning the fields it sets."""
        return self.request("PATCH", f"{object_path(obj)}?fieldManager={MANAGER}&force=true", obj,
                            content_type="application/apply-patch+yaml")   # JSON is valid YAML

    def patch_status(self, kv: dict, status: dict) -> dict:
        """Merge-patch the status subresource of a KeyValueStore."""
        return self.request("PATCH", object_path(kv) + "/status", {"status": status},
                            content_type="application/merge-patch+json")

    def watch(self, path: str, resource_version: str, timeout: int):
        """Yields watch events ({"type": ADDED|MODIFIED|DELETED|ERROR, "object": …}) until the server ends the stream."""
        url = f"{self.base}{path}?watch=true&resourceVersion={resource_version}&timeoutSeconds={timeout}"
        req = urllib.request.Request(url, headers={**self.headers, "Accept": "application/json"})
        with urllib.request.urlopen(req, context=self.ctx, timeout=timeout + 10) as r:
            for line in r:
                if line.strip():
                    yield json.loads(line)


def object_path(obj: dict) -> str:
    """REST path of an object: /api/v1/namespaces/ns/services/x, /apis/apps/v1/namespaces/ns/statefulsets/x, …"""
    api_version, kind = obj["apiVersion"], obj["kind"]
    prefix = f"/api/{api_version}" if "/" not in api_version else f"/apis/{api_version}"
    plural = {"Service": "services", "StatefulSet": "statefulsets", "KeyValueStore": PLURAL}[kind]
    md = obj["metadata"]
    return f"{prefix}/namespaces/{md['namespace']}/{plural}/{md['name']}"


def sts_path(ns: str, name: str) -> str:
    return f"/apis/apps/v1/namespaces/{ns}/statefulsets/{name}"


def svc_path(ns: str, name: str) -> str:
    return f"/api/v1/namespaces/{ns}/services/{name}"


def reconcile_one(api: Api, kv: dict):
    """Make the world match one KeyValueStore, then report its status."""
    md = kv["metadata"]
    ns, name = md["namespace"], md["name"]
    # TODO (see README): skip if deleting; observe; apply what reconcile() returns; patch status
    raise NotImplementedError


def safe_reconcile(api: Api, kv: dict):
    try:
        reconcile_one(api, kv)
    except Exception:
        log(f"reconcile of {kv['metadata'].get('name')} failed:\n{traceback.format_exc()}")


def run(api: Api, ns: str, resync: int):
    path = f"/apis/{GROUP}/{VERSION}/namespaces/{ns}/{PLURAL}"
    log(f"kv-operator watching {PLURAL}.{GROUP} in namespace {ns}")
    while True:
        try:
            listing = api.request("GET", path)                     # 1. list: the full current state…
            for kv in listing["items"]:
                kv.setdefault("apiVersion", f"{GROUP}/{VERSION}")
                kv.setdefault("kind", "KeyValueStore")
                safe_reconcile(api, kv)
            rv = listing["metadata"]["resourceVersion"]
            for event in api.watch(path, rv, timeout=resync):      # 2. …then watch changes from there
                if event["type"] in ("ADDED", "MODIFIED"):
                    safe_reconcile(api, event["object"])
                elif event["type"] == "ERROR":                      # e.g. 410 Gone: resourceVersion too old
                    break
            # 3. the watch timed out: loop, re-list and reconcile everything (resync: level-triggered!)
        except Exception as e:
            log(f"API error: {e}; retrying in 2 s")
            time.sleep(2)


def default_namespace() -> str | None:
    if os.environ.get("WATCH_NAMESPACE"):
        return os.environ["WATCH_NAMESPACE"]
    f = SA_DIR / "namespace"
    return f.read_text().strip() if f.exists() else None


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--namespace", default=default_namespace(), help="namespace to watch (default: the pod's own)")
    p.add_argument("--api", help="API base URL, e.g. http://127.0.0.1:8001 (kubectl proxy). Default: in-cluster config")
    p.add_argument("--resync", type=int, default=5, help="seconds between full resyncs")
    args = p.parse_args()
    if not args.namespace:
        sys.exit("--namespace is required outside a cluster")
    run(Api.from_env(args.api), args.namespace, args.resync)


if __name__ == "__main__":
    main()
