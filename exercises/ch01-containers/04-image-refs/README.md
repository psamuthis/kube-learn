# Exercise 1.4 — Broken image references

`pods.yaml` defines two pods. Neither starts. Apply it once (`./course check 1.4`) and look:

```console
$ kubectl -n ex-1-4 get pods
$ kubectl -n ex-1-4 describe pod web     # the Events say why
```

Fix the file so both pods run. Don't change the image *names* or *versions* you're asked for:

* `web` must run nginx **1.29** (alpine variant);
* `app` must run the course image `kubeapp:1.0`, which exists only on the nodes.

Note: changing a pod's image is allowed in place, but other fields aren't (pods are mostly
immutable). If `kubectl apply` complains, delete the pod first, or `./course check 1.4 --fresh`.
