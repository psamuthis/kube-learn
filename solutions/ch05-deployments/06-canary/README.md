# Exercise 5.6 — A canary release

`stable.yaml` runs 3 replicas of `kubeapp:1.0` (`web-stable`, labels `app: shop`, `track: stable`),
and `service.yaml` exposes them as `shop`.

Write `canary.yaml`: a Deployment `web-canary` with **1** replica of `kubeapp:2.0` whose pods also
receive traffic from the `shop` Service, so about 25% of the requests hit the new version. Don't
touch the Service or the stable Deployment.

The checker sends 40 requests to `http://shop/` and expects both versions in the answers.
