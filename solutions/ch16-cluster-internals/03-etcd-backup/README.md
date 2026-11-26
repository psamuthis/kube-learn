# Exercise 16.3 — Back up etcd

1. Take a snapshot of etcd with `etcdctl snapshot save` (inside the `etcd-kube-learn` pod, with the
   certificates from exercise 2.2). Write it to **`/var/lib/minikube/etcd/snapshot-ex163.db`**:
   that path is inside the pod's `etcd-data` hostPath volume, so the file lands on the node's disk.
2. Inspect it. The etcd image only has `etcdctl`, and the `snapshot status` command moved to
   `etcdutl`. Complete `status-pod.yaml`: a Pod `snapshot-status` that runs on the control-plane
   node (`nodeName`), mounts `/var/lib/minikube/etcd` from the host, and runs
   `etcdutl snapshot status /data/snapshot-ex163.db -w json` with the image
   `gcr.io/etcd-development/etcd:v3.6.4` (it ships `etcdutl`).
3. Read its logs (`kubectl -n ex-16-3 logs snapshot-status`) and fill in `answers.txt`.

The checker applies `status-pod.yaml`, so step 2 needs the snapshot from step 1.
`./course clean 16.3` deletes the snapshot file. Restoring is described in section 16.4. Don't
practise it on a cluster you care about.
