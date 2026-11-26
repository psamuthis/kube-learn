import json

from ingress import fetch


HOST = "shop.ex82.kube-learn.test"


def check(k):
    k.require(k.get("ingress", "web") and k.get("ingress", "api"), "Ingresses `web` and `api` exist")
    k.require(k.rollout("web") and k.rollout("api"), "both apps are rolled out")
    status, body = fetch(k, HOST, "/")
    k.expect(status == 200 and json.loads(body).get("message") == "shop frontend", "/ reaches web", f"HTTP {status} {body[:150]}")
    status, body = fetch(k, HOST, "/env")
    k.expect(status == 200 and json.loads(body).get("MESSAGE") == "shop frontend", "/env reaches web, unchanged",
             f"HTTP {status} {body[:150]}")
    status, body = fetch(k, HOST, "/api/")
    k.expect(status == 200 and json.loads(body).get("message") == "shop api", "/api/ reaches api's /", f"HTTP {status} {body[:150]}")
    status, body = fetch(k, HOST, "/api/hostname")
    k.expect(status == 200 and body.strip().startswith("api-"), "/api/hostname reaches api's /hostname", f"HTTP {status} {body[:150]}")
