# Exercise 10.3 — A hand-made PersistentVolume

The setup put a file in the directory `/data/archive-ex103` on the node **kube-learn-m03**
(it plays the role of an existing NFS share or disk). Make it available to a pod:

1. `pv.yaml`: a PersistentVolume `archive-ex103` (PVs are cluster-scoped, hence the unique name)
   * 200Mi, `ReadWriteOnce`, `persistentVolumeReclaimPolicy: Retain`, `storageClassName: ""`;
   * `hostPath: {path: /data/archive-ex103}`;
   * a `nodeAffinity` that requires the node `kube-learn-m03` (the data is only there).
2. `pvc.yaml`: a claim `archive` that binds **explicitly** to that PV (`volumeName`), with
   `storageClassName: ""` so no dynamic provisioner gets involved.
3. `pod.yaml` is written for you: it mounts the claim at `/archive` and kubeapp shows that
   directory on `/config` (`CONFIG_DIR=/archive`).

`./course clean 10.3` deletes the PV afterwards. With `Retain` it would otherwise stay
`Released` forever. (Single-node cluster? Use the node `kube-learn`.)
