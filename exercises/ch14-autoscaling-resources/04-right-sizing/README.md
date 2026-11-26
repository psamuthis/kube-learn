# Exercise 14.4 — Right-sizing requests

`deployment.yaml` runs 2 kubeapp replicas that each **request 1Gi of memory and 500m CPU**.
The scheduler reserves all of it: look at `kubectl describe node <node>` → "Allocated resources".
That's capacity nobody else can use, for an app that idles at a few dozen MiB.

1. Measure: `kubectl -n ex-14-4 top pods` (give metrics-server a minute).
2. Change the requests so that
   * memory request is **at least** what a pod uses, and **at most** twice that plus 16Mi;
   * CPU request is at most **50m**;
   * there's a memory **limit** of at least the request (and at most 256Mi).
