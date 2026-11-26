# Chapter 14 — Autoscaling and resource governance

> **Reading time:** ~35 min · **Exercises:** `exercises/ch14-autoscaling-resources/` (4)

Two related problems: making workloads **grow and shrink with load** (autoscaling), and stopping
one team or one bug from **eating the whole cluster** (LimitRanges, ResourceQuotas).

## 14.1 Three autoscalers

| Autoscaler | Scales | Based on | Where |
|---|---|---|---|
| **HorizontalPodAutoscaler** (HPA) | the number of replicas | metrics (CPU, memory, custom, external) | built in |
| **VerticalPodAutoscaler** (VPA) | requests/limits of pods | observed usage history | add-on |
| **Cluster Autoscaler** / **Karpenter** | the number of nodes | pending pods / under-used nodes | add-on, cloud-specific |

They compose: the HPA adds pods → some are Pending → the cluster autoscaler adds a node. Load
drops → the HPA removes pods → nodes are under-used → the autoscaler drains them (respecting
PDBs).

## 14.2 The HorizontalPodAutoscaler

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata: {name: web}
spec:
  scaleTargetRef: {apiVersion: apps/v1, kind: Deployment, name: web}
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target: {type: Utilization, averageUtilization: 60}   # % of the pods' CPU *requests*
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 0
      policies: [{type: Percent, value: 100, periodSeconds: 15}]   # at most double every 15 s
    scaleDown:
      stabilizationWindowSeconds: 300                               # wait 5 min of low load before shrinking
```

The control loop (every 15 s) is simple proportional control:

```text
desiredReplicas = ceil( currentReplicas × currentMetric / targetMetric )
   e.g. 3 pods at 90% CPU with a 60% target → ceil(3 × 90/60) = 5
```

Things to know:

* **Utilization is relative to requests.** No CPU request means no utilization means the HPA does
  nothing (`<unknown>` in `kubectl get hpa`). Requests must be realistic.
* CPU and memory come from **metrics-server**. Custom metrics (requests per second, queue
  length) need an adapter: prometheus-adapter, or **KEDA**, which also scales to zero on queue
  depth, cron, Kafka lag and more.
* **Don't set `replicas` in the Deployment manifest** when an HPA manages it: every `kubectl apply`
  would reset the count (chapter 5.7). Leave the field out; the HPA owns it.
* Memory is a poor scaling signal for most runtimes (memory usage rarely goes *down* when load
  drops).
* Scale-down is deliberately slow (stabilization window) to avoid flapping.

```console
$ kubectl autoscale deployment web --cpu-percent=60 --min=2 --max=10   # imperative version
$ kubectl get hpa -w                                                    # TARGETS: 85%/60%
$ kubectl describe hpa web                                              # events: "New size: 5; reason: cpu resource utilization above target"
```

## 14.3 VPA and in-place resize

The VPA watches actual usage and **recommends** (or applies) requests. In `Auto`/`Recreate` mode
it evicts pods to apply new requests; with in-place resize (1.33+), the `InPlaceOrRecreate` mode
can change them without a restart. Don't let VPA and HPA both act on CPU for the same workload.
Many teams run VPA in **recommendation-only** mode (`updateMode: "Off"`) just to size requests.

## 14.4 LimitRange: defaults and bounds per container

A LimitRange applies **per namespace**, at pod admission:

```yaml
apiVersion: v1
kind: LimitRange
metadata: {name: defaults}
spec:
  limits:
    - type: Container
      defaultRequest: {cpu: 50m, memory: 64Mi}     # filled in when a container sets no request
      default:        {cpu: 500m, memory: 256Mi}   # filled in when a container sets no limit
      min:            {cpu: 10m, memory: 16Mi}
      max:            {cpu: "2", memory: 1Gi}      # reject containers asking for more
      maxLimitRequestRatio: {memory: "2"}          # limit ≤ 2 × request
```

It mutates pods that don't set resources, and rejects pods outside the bounds. Existing pods
aren't touched.

## 14.5 ResourceQuota: a budget per namespace

```yaml
apiVersion: v1
kind: ResourceQuota
metadata: {name: team-budget}
spec:
  hard:
    pods: "10"
    requests.cpu: "2"
    requests.memory: 4Gi
    limits.memory: 8Gi
    persistentvolumeclaims: "5"
    requests.storage: 50Gi
    services.loadbalancers: "0"
    count/deployments.apps: "20"
```

* A create that would exceed the quota is **rejected** (`403 exceeded quota`). For Deployments,
  the *ReplicaSet* fails to create pods: the Deployment shows fewer ready replicas, and the
  ReplicaSet's events say why. Read them!
* With a quota on `requests.cpu`, **every pod must set CPU requests**, or it's rejected. Pair
  quotas with a LimitRange that provides defaults.
* `kubectl describe quota` shows `Used / Hard`.

LimitRange + ResourceQuota + RBAC + NetworkPolicy + Pod Security labels make a namespace a
reasonable **multi-tenant unit**: the typical "namespace per team per environment" setup.

## Exercises

| # | Name | What you practise |
|---|---|---|
| 14.1 | `hpa` | autoscale kubeapp on CPU under real load |
| 14.2 | `limitrange` | defaults and bounds applied at admission |
| 14.3 | `quota` | a namespace budget, and what a Deployment does when it hits it |
| 14.4 | `right-sizing` | measure usage with `kubectl top` and set requests from it |
