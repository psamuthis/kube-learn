# Exercise 5.1 — Your first Deployment, from scratch

Write `deployment.yaml` (there's no starter file) for a Deployment that's ready for production:

* name `web`, **3 replicas**, `revisionHistoryLimit: 5`;
* selector and pod labels: `app.kubernetes.io/name: web`;
* rolling updates with `maxSurge: 1` and `maxUnavailable: 0`;
* one container `app`, image `kubeapp:1.0`, port **named** `http` (8080);
* requests: 50m CPU, 64Mi memory; limit: 128Mi memory (no CPU limit);
* readiness probe on `/ready`, liveness probe on `/healthz`, both on the `http` port.

Tip: `kubectl create deployment web --image=kubeapp:1.0 --replicas=3 --port=8080 --dry-run=client -o yaml > deployment.yaml`
gives you a skeleton. Then edit it, and `kubectl explain deployment.spec.strategy` when in doubt.
