# Exercise 16.5 — Heartbeats and leaders

Leases are tiny objects (`coordination.k8s.io/v1`) used for two things: **node heartbeats** and
**leader election**. Explore and fill in `answers.txt`:

```console
$ kubectl get leases -A
$ kubectl -n kube-node-lease get lease kube-learn-m02 -o yaml -w     # watch renewTime move
$ kubectl -n kube-system get lease kube-controller-manager -o yaml
```
