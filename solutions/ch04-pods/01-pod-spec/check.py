import json

from kube import container, labels

# HINT: env values must be strings: `value: "9090"` (quoted), not `value: 9090`.
# HINT: `ports: [{name: http, containerPort: 9090}]`
# HINT: `command` replaces the image's ENTRYPOINT; `args` would replace its CMD.


def check(k):
    pod = k.get("pod", "app")
    k.require(pod is not None, "a Pod `app` exists")
    k.expect(labels(pod).get("app") == "kubeapp" and labels(pod).get("tier") == "demo", "labels app=kubeapp, tier=demo")
    c = container(pod)
    k.expect_eq(c.get("command"), ["python", "-u", "/app/app.py"], "command")
    ports = {p.get("name"): p.get("containerPort") for p in c.get("ports", [])}
    k.expect_eq(ports.get("http"), 9090, "the port named http")
    k.require(k.wait("pod/app", timeout=90), "the pod becomes Ready")
    ip = k.jp("pod", "app", "{.status.podIP}")
    status, body = k.http(f"http://{ip}:9090/")
    k.require(status == 200, "kubeapp answers on port 9090", body[:300])
    data = json.loads(body)
    k.expect_eq(data.get("message"), "hello pods", "the message")
    k.expect_eq(data.get("color"), "purple", "the color")
