# Exercise 5.5 — Blue/green

`blue.yaml` runs the current version (`kubeapp:1.0`) as the Deployment `web-blue`, with pod labels
`app: web` and `version: blue`.

1. Write `green.yaml`: a Deployment `web-green`, 2 replicas, `kubeapp:2.0`, pod labels `app: web`
   and `version: green` (copy blue and change what's needed).
2. Write `service.yaml`: a Service `web` (port 80 → targetPort 8080) that sends traffic
   **only to green**. (A Service routes to every Ready pod matching its `selector`; chapter 7 covers
   the details.)

Blue stays running: rolling back would just mean switching the selector back. The checker
fetches `http://web/` ten times from inside the namespace and expects version 2.0 every time.
