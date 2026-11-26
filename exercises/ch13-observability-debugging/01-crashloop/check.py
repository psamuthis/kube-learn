import json

from kube import container

APPLY = None



def setup(k):
    k.apply("""
apiVersion: apps/v1
kind: Deployment
metadata: {name: api}
spec:
  replicas: 2
  selector: {matchLabels: {app: api}}
  template:
    metadata: {labels: {app: api}}
    spec:
      containers:
        - name: app
          image: kubeapp:1.0
          command: ["python", "/app/ap.py"]
          readinessProbe: {httpGet: {path: /ready, port: 8080}, periodSeconds: 2}
          resources: {requests: {cpu: 10m, memory: 32Mi}}
""")


def check(k):
    if k.solution and container(k.get("deployment", "api")).get("command"):
        k.kubectl("patch", "deployment", "api", "--type=json",
                  "-p", json.dumps([{"op": "remove", "path": "/spec/template/spec/containers/0/command"}]))
    k.require(k.rollout("api", timeout=90), "the Deployment `api` is available")
    for p in k.ready_pods("app=api"):
        status, _ = k.http(f"http://{p['status']['podIP']}:8080/healthz")
        k.expect(status == 200, f"{p['metadata']['name']} serves /healthz")
    a = k.answers()
    k.expect_eq(a.get("exit_code"), "2", "exit_code")
    k.expect(a.get("logs_flag") in ("--previous", "-p"), "logs_flag", f"you wrote {a.get('logs_flag')!r}")
