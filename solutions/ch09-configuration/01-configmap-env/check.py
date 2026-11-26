import json

# HINT: `FEATURE_CHECKOUT: "true"`: quote it, ConfigMap values must be strings.
# HINT: `envFrom: [{configMapRef: {name: shop-config}, prefix: SHOP_}]`


def check(k):
    k.require(k.get("configmap", "shop-config") is not None, "a ConfigMap `shop-config` exists")
    k.kubectl("rollout", "restart", "deployment/shop")  # pick up ConfigMap edits made since the last start
    k.require(k.rollout("shop"), "the Deployment is rolled out")
    ip = k.ready_pods("app=shop")[0]["status"]["podIP"]
    _, body = k.http(f"http://{ip}:8080/")
    k.expect_eq(json.loads(body).get("message"), "configured by a ConfigMap", "kubeapp's message")
    _, body = k.http(f"http://{ip}:8080/env")
    env = json.loads(body)
    k.expect_eq(env.get("SHOP_LOG_LEVEL"), "debug", "SHOP_LOG_LEVEL")
    k.expect_eq(env.get("SHOP_FEATURE_CHECKOUT"), "true", "SHOP_FEATURE_CHECKOUT")
    k.expect_eq(env.get("SHOP_MESSAGE"), "configured by a ConfigMap", "SHOP_MESSAGE")
