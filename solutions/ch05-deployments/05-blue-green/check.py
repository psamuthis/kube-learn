import json

# HINT: The green Deployment's *selector* must match its own pods (version: green), not blue's.
# HINT: Service: `spec: {selector: {app: web, version: green}, ports: [{port: 80, targetPort: 8080}]}`


def check(k):
    k.require(k.get("deployment", "web-green") is not None, "a Deployment `web-green` exists")
    k.require(k.rollout("web-green") and k.rollout("web-blue"), "blue and green are both rolled out")
    svc = k.get("service", "web")
    k.require(svc is not None, "a Service `web` exists")
    versions = []
    for _ in range(10):
        status, body = k.http("http://web/")
        versions.append(json.loads(body).get("version") if status == 200 else f"HTTP {status}")
    k.expect(all(v == "2.0" for v in versions), "http://web/ always answers version 2.0", f"got {versions}")
    k.expect(len(k.ready_pods("version=blue")) == 2, "blue is still running (for a quick rollback)")
