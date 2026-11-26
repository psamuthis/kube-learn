# Exercise 17.3 — The heart of a controller

Complete `reconcile.py`, the **pure** part of the KeyValueStore operator (section 17.5). It has
no I/O: objects in, objects out. That makes it easy to test, and the checker runs unit tests
against it (no cluster involved).

A KeyValueStore looks like:

```python
{"apiVersion": "kube-learn.dev/v1", "kind": "KeyValueStore",
 "metadata": {"name": "cache", "namespace": "shop", "uid": "1234", "generation": 2},
 "spec": {"replicas": 2, "version": "7.4"},
 "status": {...}}
```

Implement, following the docstrings:

* `desired_service(kv)`: a Service `<name>` on port 6379 (named `redis`) selecting the pods;
* `desired_statefulset(kv)`: a StatefulSet `<name>` with `spec.replicas` replicas of
  `redis:<version>-alpine`, the labels from `labels(kv)`, and an **ownerReference** to the
  KeyValueStore (so deleting the KeyValueStore deletes everything);
* `reconcile(kv, observed)`: the list of objects to (re)apply, **only** those that are missing or
  differ in the fields we own (replicas, image). An empty list means "converged";
* `compute_status(kv, sts)`: `{"phase", "readyReplicas", "observedGeneration"}`.

`python3 -c 'import reconcile'` checks it at least imports. The tests are in `check.py`.
