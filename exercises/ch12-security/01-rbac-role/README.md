# Exercise 12.1 — A least-privilege Role

Write `rbac.yaml` with:

* a ServiceAccount `reader`;
* a Role `pod-reader` that may `get`, `list` and `watch` **pods**, and `get` **pods/log**, and
  nothing else;
* a RoleBinding `reader-pod-reader` giving that Role to the ServiceAccount.

Test before checking:

```console
$ kubectl -n ex-12-1 auth can-i list pods --as=system:serviceaccount:ex-12-1:reader
$ kubectl -n ex-12-1 auth can-i --list --as=system:serviceaccount:ex-12-1:reader
```
