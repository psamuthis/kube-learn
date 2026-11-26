# Exercise 4.4 — Probes that don't lie

`deployment.yaml` runs one kubeapp pod that takes **20 seconds** to warm up (`READY_DELAY=20`:
`/ready` returns 503 during warm-up). Its probes are wrong. Apply it (`./course check 4.4`) and
watch `kubectl -n ex-4-4 get pods -w`: restarts, never Ready.

(The pod is wrapped in a Deployment so you can re-apply changed probes; chapter 5 explains
Deployments. Changing the template replaces the pod.)

Fix the probes so that:

* **readiness** checks `/ready` on the port named `http`, every 2 seconds;
* **liveness** checks `/healthz` (the process is alive even while warming up), every 3 seconds,
  restarting after 3 consecutive failures;
* the pod becomes Ready in under 60 s and **never restarts** during warm-up.

The checker then calls `/break` (which makes `/healthz` fail) and expects the liveness probe to
restart the container within 45 seconds.
