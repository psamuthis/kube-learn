# Exercise 11.2 — Spread for availability, stay close to the cache

`cache.yaml` runs one `cache` pod. Complete `web.yaml` so that the 3 `web` replicas

* **never** share a node (required pod anti-affinity on `kubernetes.io/hostname`);
* **prefer** (weight 100) to be on the same node as a `cache` pod (preferred pod affinity).

With 3 nodes that gives one web per node, whatever the preference says. Required beats preferred.
The checker also scales `web` to 4 and expects the 4th replica to stay `Pending`. Read its event
in `kubectl -n ex-11-2 describe pod`.
