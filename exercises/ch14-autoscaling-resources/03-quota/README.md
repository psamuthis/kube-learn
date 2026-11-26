# Exercise 14.3 — A ResourceQuota

1. Write `quota.yaml`: a ResourceQuota `budget` allowing at most **4 pods**, **400m** of CPU
   requests and **512Mi** of memory requests in this namespace.
2. `fleet.yaml` (given) asks for 6 replicas. Apply both (`./course check 14.3`) and investigate:

```console
$ kubectl -n ex-14-3 describe quota budget
$ kubectl -n ex-14-3 get deploy,rs,pods
$ kubectl -n ex-14-3 describe rs -l app=fleet        # Events
```

3. Fill in `answers.txt`.
