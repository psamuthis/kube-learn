# Exercise 10.2 — A PersistentVolumeClaim

Same counter app, but now the count must survive the pod being deleted.

1. Write `pvc.yaml`: a PersistentVolumeClaim `data`, `ReadWriteOnce`, **100Mi**, storage class
   `local-path`.
2. Complete `deployment.yaml`: mount the claim at `/data` (with `DATA_DIR=/data`). Use the
   `Recreate` strategy: with a single-node (RWO) volume you don't want two pods fighting over it
   during a rollout.

Then look at what got created: `kubectl -n ex-10-2 get pvc`, `kubectl get pv`,
`kubectl get pv <name> -o yaml` (find its `nodeAffinity`).

The checker counts some hits, deletes the pod, and expects the new pod to continue the count.
