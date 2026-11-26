# Chapter 11 — Scheduling: where pods run

> **Reading time:** ~45 min · **Exercises:** `exercises/ch11-scheduling/` (5) · needs the 3-node cluster

The scheduler's default is "anywhere that fits, spread out a bit". This chapter is about
telling it more: put pods on nodes with SSDs, never two replicas on the same node, keep this node
for GPU jobs, spread across zones, and survive a node being drained for maintenance.

## 11.1 How the scheduler decides (recap)

For each pending pod: **filter** the nodes that *can* run it (resources, selectors, affinity,
taints, ports, volume topology), then **score** the survivors (spreading, affinity preferences,
resource balance, image locality) and **bind** to the best. "Required" rules are filters;
"preferred" rules add to scores. If nothing passes the filters, the pod stays **Pending**, and
its events say exactly which filter rejected how many nodes:

```text
0/3 nodes are available: 1 node(s) had untolerated taint {dedicated: gpu}, 2 node(s) didn't match Pod's node affinity/selector.
```

All the steering tools are about **labels on nodes** and **labels on other pods**:

```console
$ kubectl get nodes --show-labels
$ kubectl label node kube-learn-m02 disktype=ssd          # add
$ kubectl label node kube-learn-m02 disktype-             # remove
```

Well-known node labels: `kubernetes.io/hostname`, `kubernetes.io/os`, `kubernetes.io/arch`,
`topology.kubernetes.io/zone`, `topology.kubernetes.io/region`,
`node.kubernetes.io/instance-type` (the last three are set by cloud providers).

## 11.2 nodeSelector and node affinity

**nodeSelector**: the simple version, an exact-match map:

```yaml
spec:
  nodeSelector:
    disktype: ssd
```

**Node affinity**: the expressive version, with required and preferred terms:

```yaml
spec:
  affinity:
    nodeAffinity:
      requiredDuringSchedulingIgnoredDuringExecution:       # a filter
        nodeSelectorTerms:                                  # terms are ORed…
          - matchExpressions:                               # …expressions within a term are ANDed
              - {key: kubernetes.io/arch, operator: In, values: [amd64, arm64]}
              - {key: disktype, operator: NotIn, values: [hdd]}
      preferredDuringSchedulingIgnoredDuringExecution:      # a score bonus
        - weight: 50
          preference:
            matchExpressions:
              - {key: topology.kubernetes.io/zone, operator: In, values: [eu-west-1a]}
```

Operators: `In`, `NotIn`, `Exists`, `DoesNotExist`, `Gt`, `Lt`. "IgnoredDuringExecution"
means that relabelling a node later doesn't evict pods that are already running.

## 11.3 Pod affinity and anti-affinity

Rules relative to **other pods**: "schedule me (not) in the same *topology domain* as pods
matching this selector". The domain is defined by a node label (`topologyKey`): per node
(`kubernetes.io/hostname`), per zone (`topology.kubernetes.io/zone`)…

```yaml
affinity:
  podAntiAffinity:                       # never two of us on the same node
    requiredDuringSchedulingIgnoredDuringExecution:
      - labelSelector: {matchLabels: {app: web}}
        topologyKey: kubernetes.io/hostname
  podAffinity:                           # prefer to be near the cache
    preferredDuringSchedulingIgnoredDuringExecution:
      - weight: 100
        podAffinityTerm:
          labelSelector: {matchLabels: {app: cache}}
          topologyKey: kubernetes.io/hostname
```

Required anti-affinity per hostname means `replicas` can't exceed the number of nodes: the 4th
replica of a 3-node cluster stays Pending. That's sometimes what you want (a quorum must never
share a node) and often not (use *preferred*, or topology spread).

## 11.4 Topology spread constraints

The modern, quantitative way to spread replicas:

```yaml
topologySpreadConstraints:
  - maxSkew: 1                               # max difference in pod count between any two domains
    topologyKey: kubernetes.io/hostname
    whenUnsatisfiable: DoNotSchedule         # or ScheduleAnyway (a preference)
    labelSelector: {matchLabels: {app: web}}
  - maxSkew: 1
    topologyKey: topology.kubernetes.io/zone
    whenUnsatisfiable: ScheduleAnyway
    labelSelector: {matchLabels: {app: web}}
```

6 replicas on 3 nodes with `maxSkew: 1` per hostname gives 2/2/2; 7 gives 3/2/2. Spreading is
only enforced **at scheduling time**. After a node comes back, nothing rebalances (that's what
the *descheduler* project does).

## 11.5 Taints and tolerations

Affinity *attracts* pods; **taints repel** them. A node with a taint accepts only pods that
**tolerate** it:

```console
$ kubectl taint node kube-learn-m03 dedicated=gpu:NoSchedule      # add
$ kubectl taint node kube-learn-m03 dedicated=gpu:NoSchedule-     # remove
```

```yaml
tolerations:
  - key: dedicated
    operator: Equal          # or Exists (any value)
    value: gpu
    effect: NoSchedule
```

| Effect | Meaning |
|---|---|
| `NoSchedule` | new pods without the toleration aren't scheduled here |
| `PreferNoSchedule` | avoid if possible |
| `NoExecute` | also **evicts** running pods that don't tolerate it (optionally after `tolerationSeconds`) |

A toleration only *allows* a pod on a tainted node; it doesn't send it there. **Dedicated nodes**
need both: a taint (to keep others off) plus a nodeSelector or affinity (to bring the right pods in).

Kubernetes taints nodes itself: `node.kubernetes.io/not-ready` and `/unreachable` (NoExecute,
which is how pods get evicted from dead nodes: by default they tolerate it for 300 s),
`/disk-pressure`, `/memory-pressure`, `/unschedulable` (cordoned).

## 11.6 Priority and preemption

A **PriorityClass** gives pods a priority number. When a high-priority pod can't fit, the
scheduler **preempts** (evicts) lower-priority pods to make room.

```yaml
apiVersion: scheduling.k8s.io/v1
kind: PriorityClass
metadata: {name: critical-batch}
value: 100000
preemptionPolicy: PreemptLowerPriority     # or Never
description: "jobs that must run tonight"
---
spec:
  priorityClassName: critical-batch        # in the pod spec
```

`system-cluster-critical` and `system-node-critical` protect DNS, CNI and so on. Keep your own
values well below them.

## 11.7 Maintenance: cordon, drain and PodDisruptionBudgets

```console
$ kubectl cordon kube-learn-m02          # mark unschedulable (taint node.kubernetes.io/unschedulable)
$ kubectl drain kube-learn-m02 --ignore-daemonsets --delete-emptydir-data
                                         # cordon + *evict* every pod (respecting PDBs)
$ kubectl uncordon kube-learn-m02        # back in service
```

`drain` uses the **Eviction API**, not a plain delete, so it respects **PodDisruptionBudgets**:

```yaml
apiVersion: policy/v1
kind: PodDisruptionBudget
metadata: {name: web}
spec:
  minAvailable: 2               # or maxUnavailable: 1
  selector: {matchLabels: {app: web}}
```

If evicting a pod would take the matching pods below `minAvailable`, the eviction is refused
(HTTP 429) and `drain` retries until the Deployment has rescheduled replacements elsewhere.
PDBs protect against *voluntary* disruptions (drains, cluster upgrades, autoscaler scale-down).
They don't help when a node crashes. Every production workload with more than one replica
should have one.

## Exercises

| # | Name | What you practise |
|---|---|---|
| 11.1 | `node-selector` | label a node, pin a Deployment to it |
| 11.2 | `anti-affinity` | one replica per node; prefer co-location with a cache |
| 11.3 | `taints` | a dedicated node: taint + toleration + selector |
| 11.4 | `topology-spread` | an exact 2/2/2 spread |
| 11.5 | `drain-pdb` | drain a node without dropping below a PodDisruptionBudget |
