import json

from ingress import fetch

# HINT: One Ingress can have several `rules`, each with its own `host`.
# HINT: `path: /` with `pathType: Prefix` matches every path.


def check(k):
    ing = k.get("ingress", "colors")
    k.require(ing is not None, "an Ingress `colors` exists")
    k.expect_eq(ing["spec"].get("ingressClassName"), "nginx", "ingressClassName")
    k.require(k.rollout("blue") and k.rollout("green"), "both apps are rolled out")
    for color in ("blue", "green"):
        host = f"{color}.ex81.kube-learn.test"
        status, body = fetch(k, host, "/")
        msg = json.loads(body).get("message") if status == 200 else body[:200]
        k.expect(msg == f"this is {color}", f"http://{host}/ reaches {color}", f"HTTP {status}: {msg}")
    status, _ = fetch(k, "other.ex81.kube-learn.test", "/", retries=1)
    k.expect(status == 404, "an unknown host gets a 404", f"HTTP {status}")
