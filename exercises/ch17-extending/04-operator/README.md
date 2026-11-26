# Exercise 17.4 — The operator loop

`kv_operator.py` is a complete little controller *except* for its reconcile step. It contains a
stdlib API client (`Api`: get, server-side apply, status patch, watch) and the
list-then-watch-then-resync loop from section 17.3. It imports **your** `reconcile.py` from
exercise 17.3, so do that one first.

Complete `reconcile_one(api, kv)`:

1. skip KeyValueStores that are being deleted (`metadata.deletionTimestamp`): the garbage
   collector removes the children through their ownerReferences;
2. read the observed Service and StatefulSet (`api.get(...)`, `None` when they don't exist);
3. apply every object `reconcile()` returns (`api.apply(obj)`, server-side apply with the field
   manager `kv-operator`);
4. re-read the StatefulSet and patch the KeyValueStore's **status** subresource with
   `compute_status()`.

Run it yourself against the cluster:

```console
$ kubectl apply -f crd.yaml
$ kubectl proxy --port 8001 &
$ python3 kv_operator.py --namespace ex-17-4 --api http://127.0.0.1:8001
$ kubectl -n ex-17-4 apply -f kv.yaml          # in another terminal
$ kubectl -n ex-17-4 get kvs,sts,svc,pods -w
$ kubectl -n ex-17-4 scale kvs cache --replicas=3   # the CRD has a scale subresource
```

The checker starts its own proxy and operator, creates `cache` (2 replicas), waits for the
StatefulSet and the status to be Ready, scales the KeyValueStore to 3, pings Redis through the
Service, and deletes the KeyValueStore, expecting the StatefulSet to be garbage-collected.
