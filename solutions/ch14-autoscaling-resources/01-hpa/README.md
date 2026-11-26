# Exercise 14.1 — Autoscaling on CPU

`deployment.yaml` runs kubeapp behind the Service `web`. Its `/cpu?ms=N` endpoint burns N ms of
CPU per request.

1. Make the Deployment HPA-friendly: give the container a **CPU request of 50m**, and **remove
   the `replicas` field** (the HPA will own it).
2. Write `hpa.yaml`: an `autoscaling/v2` HPA `web` targeting the Deployment, min **1**, max **5**
   replicas, target **50%** average CPU utilization. Let it scale up fast:
   `behavior.scaleUp.stabilizationWindowSeconds: 0`.

The checker starts a load generator that hammers `http://web/cpu?ms=100`, and expects the HPA to
scale beyond 1 replica within about 2 minutes. Watch it: `kubectl -n ex-14-1 get hpa -w`.
