import json

APPLY = None



def setup(k):
    k.apply("""
apiVersion: apps/v1
kind: Deployment
metadata: {name: web}
spec:
  replicas: 2
  selector: {matchLabels: {app: web}}
  template:
    metadata: {labels: {app: web}}
    spec:
      containers:
        - name: app
          image: kubeapp:1.0
          ports: [{name: http, containerPort: 8080}]
          readinessProbe: {httpGet: {path: /healthy, port: http}, periodSeconds: 2}
          resources: {requests: {cpu: 10m, memory: 32Mi}}
---
apiVersion: v1
kind: Service
metadata: {name: web}
spec:
  selector: {app: web}
  ports: [{port: 80, targetPort: http}]
""")


def check(k):
    if k.solution:
        k.kubectl("patch", "deployment", "web", "--type=json", "-p", json.dumps([
            {"op": "replace", "path": "/spec/template/spec/containers/0/readinessProbe/httpGet/path", "value": "/ready"}]))
    k.require(k.rollout("web", timeout=90), "the Deployment `web` is available")
    svc = k.get("service", "web")
    k.expect(svc["spec"]["selector"] == {"app": "web"}, "the Service is unchanged")
    status, body = k.http("http://web/")
    k.expect(status == 200, "http://web/ answers", body[:200])
    a = k.answers()
    k.expect_eq(a.get("ready_before"), "0/1", "ready_before")
    k.expect_eq(a.get("probe_status"), "404", "probe_status")
