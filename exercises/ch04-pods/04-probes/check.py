import time

from kube import container



def check(k):
    d = k.get("deployment", "app")
    c = container(d)
    rp, lp = c.get("readinessProbe", {}), c.get("livenessProbe", {})
    k.expect(rp.get("httpGet", {}).get("path") == "/ready" and rp["httpGet"].get("port") in ("http", 8080),
             "readiness probes /ready on the http port")
    k.expect(lp.get("httpGet", {}).get("path") == "/healthz" and lp["httpGet"].get("port") in ("http", 8080),
             "liveness probes /healthz on the http port")
    k.expect(lp.get("periodSeconds") == 3 and lp.get("failureThreshold", 3) == 3, "liveness: every 3 s, 3 failures")
    k.require(k.rollout("app", timeout=90), "the pod becomes Ready (rollout completes)")
    pod = k.ready_pods("app=probes")[0]
    name = pod["metadata"]["name"]
    restarts = pod["status"]["containerStatuses"][0]["restartCount"]
    k.expect(restarts == 0, "it never restarted during warm-up", f"restartCount = {restarts}")
    ip = pod["status"]["podIP"]
    k.http(f"http://{ip}:8080/break")
    restarted = k.wait_for(lambda: k.jp("pod", name, "{.status.containerStatuses[0].restartCount}") not in ("", "0"),
                           timeout=45)
    k.expect(restarted, "after /break, liveness restarts the container within 45 s")
    k.rollout("app", timeout=60)
