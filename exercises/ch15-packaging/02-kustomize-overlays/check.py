import json

from kube import container, labels

KUSTOMIZE = "overlays/prod"



def check(k):
    code, out, err = k.try_kubectl("kustomize", str(k.dir / "overlays/dev"), ns=False)
    k.require(code == 0, "`kubectl kustomize overlays/dev` renders", err)
    k.expect("name: dev-shop" in out and "env: dev" in out and "MESSAGE: hello from dev" in out,
             "dev renders dev-shop with env=dev and the dev message")
    d = k.get("deployment", "prod-shop")
    k.require(d is not None, "prod's Deployment is named prod-shop")
    k.expect_eq(d["spec"]["replicas"], 3, "prod replicas")
    k.expect_eq(container(d)["image"], "kubeapp:2.0", "prod image")
    k.expect_eq(labels(d).get("env"), "prod", "the env label")
    cm = container(d)["envFrom"][0]["configMapRef"]["name"]
    k.expect(cm.startswith("prod-shop-config-") and len(cm) > len("prod-shop-config-"),
             "the Deployment refers to the hashed ConfigMap name", cm)
    k.require(k.rollout("prod-shop", timeout=90), "prod-shop is rolled out")
    status, body = k.http("http://prod-shop/")
    k.expect(status == 200 and json.loads(body).get("message") == "hello from prod", "prod serves `hello from prod`", body[:200])
