# Exercise 7.5 — A headless Service

`deployment.yaml` runs 3 `peer` pods that need to find *each other* (think of a gossip cluster),
so a virtual IP doesn't help them: they need the list of pod IPs.

Write `service.yaml`: a **headless** Service `peers` selecting `app: peer`, port 8080.

Then compare:

```console
$ kubectl -n ex-7-5 run -it --rm t --image=busybox:1.37 -- nslookup peers.ex-7-5.svc.cluster.local
```

The checker expects that lookup to return the IPs of all 3 pods.
