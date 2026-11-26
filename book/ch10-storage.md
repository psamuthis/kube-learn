# Chapter 10 — Storage

> **Reading time:** ~45 min · **Exercises:** `exercises/ch10-storage/` (5)

A container's filesystem is an overlay layer that's deleted with the container (chapter 1).
Anything that must outlive a restart, a reschedule or a rollout needs a **volume**. This chapter
goes from scratch space to persistent volumes, dynamic provisioning and a database on a
StatefulSet.

## 10.1 Volumes: lifetime is the whole story

A volume is declared in the pod spec and mounted into containers. Its **lifetime** depends on its
type:

| Volume type | Lives as long as | Use |
|---|---|---|
| `emptyDir` | the **pod** (survives container restarts, not pod deletion) | scratch space, caches, sharing between containers; `medium: Memory` for tmpfs |
| `configMap`, `secret`, `downwardAPI`, `projected` | the source object | config (chapter 9) |
| `hostPath` | the **node** (a directory on the host) | node agents only: dangerous, ties the pod to a node, a security risk |
| `persistentVolumeClaim` | the **claim** (independent of any pod) | real data |
| `ephemeral` | the pod, but provisioned like a PVC | big scratch volumes from a storage class |
| `image` (1.33+) | the pod | mount an OCI image's contents read-only (models, data) |

```console
$ kubectl exec pod -- sh -c 'echo hi > /data/x; kill 1'   # container restarts: emptyDir keeps /data/x
$ kubectl delete pod pod                                  # new pod: emptyDir is gone
```

## 10.2 PersistentVolumes and claims

Storage is split into two objects, so that **apps ask for storage abstractly** and **the cluster
supplies it**:

```text
 PersistentVolumeClaim (namespaced, written by the app team)
   "I need 10Gi, ReadWriteOnce, class fast-ssd"
          │ bound 1:1 by the PV controller
          ▼
 PersistentVolume (cluster-scoped, an actual piece of storage)
   "an EBS volume vol-0abc / an NFS export / a directory on node m02, 10Gi, RWO"
          │ attached and mounted by the kubelet (through a CSI driver)
          ▼
 pod volume  persistentVolumeClaim: {claimName: data}
```

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata: {name: data}
spec:
  accessModes: [ReadWriteOnce]
  storageClassName: local-path      # omit to use the default class; "" means "no class, static PVs only"
  resources:
    requests: {storage: 1Gi}
---
# in the pod spec
volumes:
  - name: data
    persistentVolumeClaim: {claimName: data}
```

**Access modes** describe how many *nodes* (not pods!) may mount the volume:

| Mode | Meaning | Typical backends |
|---|---|---|
| `ReadWriteOnce` (RWO) | read-write by **one node** | block disks: EBS, PD, Azure Disk, local |
| `ReadWriteOncePod` (RWOP) | read-write by **one pod** | same, stricter |
| `ReadOnlyMany` (ROX) | read-only by many nodes | |
| `ReadWriteMany` (RWX) | read-write by many nodes | NFS, CephFS, EFS, Azure Files |

So a Deployment with 3 replicas sharing one RWO claim only works if all 3 land on the same node.
Per-replica storage needs a StatefulSet (10.5); shared storage needs RWX.

**PV phases**: `Available` → `Bound` → `Released` (claim deleted) → reclaimed according to
`persistentVolumeReclaimPolicy`: `Delete` (the default for dynamic PVs: the disk is destroyed with
the claim) or `Retain` (kept, so an admin must clean up or re-bind it by hand). **Deleting a PVC
can delete your data.** For important data, use `Retain` classes and backups.

## 10.3 StorageClasses and dynamic provisioning

Nobody creates PVs by hand in a cloud. A **StorageClass** names a **provisioner** (a CSI driver)
and its parameters. When a claim names a class, the provisioner creates a matching PV on
demand:

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fast-ssd
  annotations: {storageclass.kubernetes.io/is-default-class: "true"}
provisioner: ebs.csi.aws.com
parameters: {type: gp3, iops: "6000"}
reclaimPolicy: Delete
allowVolumeExpansion: true                 # grow a claim by editing its request
volumeBindingMode: WaitForFirstConsumer    # provision only once a pod is scheduled
```

**`volumeBindingMode: WaitForFirstConsumer`** matters for any storage with **topology**: a zonal
cloud disk, or a node-local disk. With `Immediate`, the volume is created right away (maybe in the
wrong zone or on the wrong node) and the pod can then never be scheduled. With
`WaitForFirstConsumer`, the scheduler picks the node first, and the volume is created where the
pod is.

**Your lab has two classes:**

* `local-path` (the default, Rancher's local-path provisioner): creates a directory on the
  **node where the pod is scheduled**, and gives the PV a **node affinity** for that node. It's
  honest about topology: the PV is local, so the pod will always come back to that node. If the
  node dies, the data is gone. It's a single-node disk, like `hostPath` with proper bookkeeping.
* `standard` (minikube's hostpath provisioner): `Immediate` binding, directory on the control-plane
  node. It doesn't handle multi-node clusters well, so the course uses `local-path`.

Real clusters use network block storage (EBS/PD/Azure Disk CSI), file storage (EFS, NFS), or
distributed storage run *on* the cluster (Rook/Ceph, Longhorn, OpenEBS).

**CSI** (Container Storage Interface) is the plugin API: a controller part (create, delete,
attach, snapshot) and a node part (a DaemonSet that mounts volumes on each node). Snapshots
(`VolumeSnapshot`) and clones are CSI features too.

## 10.4 Static provisioning

You can also create a PV by hand (pre-existing NFS shares, migrated disks) and bind a claim to
it, either by matching (class `""`, size, access modes, a label selector) or explicitly with
`spec.volumeName` on the claim (and `claimRef` on the PV, to reserve it):

```yaml
apiVersion: v1
kind: PersistentVolume
metadata: {name: archive, labels: {kind: archive}}
spec:
  capacity: {storage: 500Mi}
  accessModes: [ReadWriteOnce]
  persistentVolumeReclaimPolicy: Retain
  storageClassName: ""
  hostPath: {path: /data/archive}        # for labs only; really an nfs:, csi:, …
  nodeAffinity:
    required:
      nodeSelectorTerms:
        - matchExpressions: [{key: kubernetes.io/hostname, operator: In, values: [kube-learn-m03]}]
```

## 10.5 StatefulSets and storage

`volumeClaimTemplates` give each StatefulSet replica its own claim, named
`<template>-<sts>-<ordinal>`:

```yaml
volumeClaimTemplates:
  - metadata: {name: data}
    spec:
      accessModes: [ReadWriteOnce]
      storageClassName: local-path
      resources: {requests: {storage: 1Gi}}
```

* `db-0` always gets `data-db-0`, wherever and whenever it's (re)created. With node-local storage,
  that also pins `db-0` to its node.
* Scaling down **doesn't delete** the claims (`persistentVolumeClaimRetentionPolicy` can change
  that), so scaling back up finds the data again.
* Databases want their data directory to be a dedicated, empty mount. For Postgres, point
  `PGDATA` at a subdirectory of the mount (the mount root can contain `lost+found`).

## 10.6 Operational notes

* **Expanding**: edit the PVC's `resources.requests.storage` upward (the class must allow it).
  Shrinking isn't supported.
* **Backups**: snapshots (`VolumeSnapshot`) are crash-consistent at best. Databases need
  logical or WAL backups (pg_dump, pgBackRest, or an operator that does them). Velero backs up
  objects + volumes.
* **Permissions**: volumes are often root-owned; non-root containers need `fsGroup`
  (chapters 9 and 12) or an init container that chowns.
* **Don't run your production database on Kubernetes casually.** It works well with a good
  operator (CloudNativePG, Percona, Zalando) and good storage; a managed database is often simpler.

## Exercises

| # | Name | What you practise |
|---|---|---|
| 10.1 | `emptydir` | what survives a container restart vs. a pod deletion |
| 10.2 | `pvc` | a dynamically provisioned claim: data survives pod deletion |
| 10.3 | `static-pv` | bind a claim to a hand-made PV, `Retain` |
| 10.4 | `storage-classes` | inspect classes, binding modes, node affinity of local volumes |
| 10.5 | `postgres` | Postgres on a StatefulSet with volumeClaimTemplates and a Secret |
