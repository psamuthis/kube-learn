# Exercise 11.1 — Pin pods to a node

The node `kube-learn-m02` has a fast disk (let's pretend). Pin the Deployment `fast` to it:

1. Label the node: `disktype=ssd` (one kubectl command; only that node).
2. Complete `deployment.yaml` with a `nodeSelector`.

Then: `kubectl -n ex-11-1 get pods -o wide`. All 3 replicas should be on m02.
`./course clean 11.1` removes the label afterwards.
