from kube import container, cpu_millis, mem_bytes



def check(k):
    d = k.get("deployment", "web")
    k.require(d is not None, "a Deployment `web` exists")
    s = d["spec"]
    k.expect_eq(s.get("replicas"), 3, "replicas")
    k.expect_eq(s.get("revisionHistoryLimit"), 5, "revisionHistoryLimit")
    k.expect_eq(s["selector"].get("matchLabels"), {"app.kubernetes.io/name": "web"}, "the selector")
    ru = s.get("strategy", {}).get("rollingUpdate", {})
    k.expect(str(ru.get("maxSurge")) == "1" and str(ru.get("maxUnavailable")) == "0", "maxSurge 1, maxUnavailable 0",
             f"got {ru}")
    c = container(d, "app")
    k.require(c is not None, "a container named `app`")
    k.expect_eq(c.get("image"), "kubeapp:1.0", "the image")
    k.expect(any(p.get("name") == "http" and p.get("containerPort") == 8080 for p in c.get("ports", [])), "port http = 8080")
    r = c.get("resources", {})
    k.expect(cpu_millis(r.get("requests", {}).get("cpu", "0")) == 50, "requests 50m CPU")
    k.expect(mem_bytes(r.get("requests", {}).get("memory", "0")) == 64 * 2**20, "requests 64Mi memory")
    k.expect(mem_bytes(r.get("limits", {}).get("memory", "0")) == 128 * 2**20, "limit 128Mi memory")
    k.expect("cpu" not in r.get("limits", {}), "no CPU limit")
    k.expect(c.get("readinessProbe", {}).get("httpGet", {}).get("path") == "/ready", "readiness probe on /ready")
    k.expect(c.get("livenessProbe", {}).get("httpGet", {}).get("path") == "/healthz", "liveness probe on /healthz")
    k.require(k.rollout("web"), "the rollout completes")
    pods = k.ready_pods("app.kubernetes.io/name=web")
    k.expect(len(pods) == 3, "3 pods are Ready", f"{len(pods)} ready")
    for p in pods:
        status, _ = k.http(f"http://{p['status']['podIP']}:8080/")
        k.expect(status == 200, f"{p['metadata']['name']} answers")
