# Exercise 6.5 — A StatefulSet

Write `statefulset.yaml` with:

* a **headless** Service `web` (`clusterIP: None`) selecting `app: web`, port 8080;
* a StatefulSet `web` using that Service (`serviceName`), **3 replicas** of `kubeapp:1.0`, with a
  readiness probe on `/ready`, and the default *ordered* pod management.

The checker verifies the pods are named `web-0`, `web-1`, `web-2` and started in that order; that
`web-1.web.ex-6-5.svc.cluster.local` (or just `web-1.web` from inside the namespace) resolves in DNS to the pod `web-1`; and that after you delete `web-1` the replacement
has the **same name**.
