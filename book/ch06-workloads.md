# Chapter 6 — The other workloads

> **Reading time:** ~40 min · **Exercises:** `exercises/ch06-workloads/` (5)

Deployments are for **stateless, long-running, interchangeable** replicas. Not everything is
like that. Kubernetes has four more workload controllers, each a different answer to "how many
pods, where, and for how long?".

| Controller | Pods | Identity | Lifetime | Typical use |
|---|---|---|---|---|
| Deployment | N, anywhere | interchangeable | forever | web apps, APIs, workers |
| **DaemonSet** | one per (matching) node | per node | forever | node agents: logs, metrics, CNI, storage drivers |
| **StatefulSet** | N, ordered | stable name, DNS, volume | forever | databases, queues, quorum systems |
| **Job** | until N succeed | interchangeable or indexed | to completion | batch, migrations, one-off tasks |
| **CronJob** | a Job per schedule tick | — | to completion | backups, reports, cleanup |

## 6.1 DaemonSet

A DaemonSet runs **one pod on every node** (or every node matching a `nodeSelector`/affinity).
Add a node and it gets a pod; remove a node and its pod goes with it. The DaemonSet controller
sets each pod's node affinity itself, so the scheduler only confirms the placement.

```yaml
apiVersion: apps/v1
kind: DaemonSet
metadata: {name: node-agent}
spec:
  selector: {matchLabels: {app: node-agent}}
  updateStrategy: {type: RollingUpdate, rollingUpdate: {maxUnavailable: 1}}
  template:
    metadata: {labels: {app: node-agent}}
    spec:
      tolerations:                                   # also run on control-plane nodes
        - {key: node-role.kubernetes.io/control-plane, operator: Exists, effect: NoSchedule}
      containers:
        - name: agent
          image: busybox:1.37
          command: ["sh", "-c", "while true; do df -h /host; sleep 60; done"]
          volumeMounts: [{name: host-root, mountPath: /host, readOnly: true}]
      volumes:
        - {name: host-root, hostPath: {path: /}}
```

Real DaemonSets you already have: `kube-proxy`, `calico-node` (in kube-system). Look at them:
`kubectl -n kube-system get ds`. Node agents often use `hostPath` volumes, `hostNetwork: true`
or privileged mode, which is why they're a security-sensitive category (chapter 12).

**Taints** keep ordinary pods off certain nodes (chapter 11). Production control-plane nodes
usually carry `node-role.kubernetes.io/control-plane:NoSchedule`, so agents that must run
everywhere need the matching **toleration**. minikube doesn't taint its control plane, but
write the toleration anyway: your manifests should work on real clusters too.

## 6.2 StatefulSet

Some systems need their replicas to be **distinguishable**: a database primary and replicas, a
Kafka broker with an ID, a ZooKeeper/etcd member with a fixed peer address. A StatefulSet gives
each pod:

* a **stable name** with an ordinal: `db-0`, `db-1`, `db-2` (recreated with the *same* name);
* a **stable DNS name** through a **headless Service** (`clusterIP: None`):
  `db-0.db.<ns>.svc.cluster.local`;
* its **own PersistentVolumeClaim** from `volumeClaimTemplates` (`data-db-0`, …), which follows
  the pod across restarts and reschedules, and is **not** deleted when you scale down (by
  default);
* **ordered** operations (by default): create `0, 1, 2` one at a time, each Ready before the
  next; delete and update in reverse order.

```yaml
apiVersion: v1
kind: Service
metadata: {name: db}
spec:
  clusterIP: None                 # headless: DNS returns the pod IPs, no virtual IP
  selector: {app: db}
  ports: [{port: 5432}]
---
apiVersion: apps/v1
kind: StatefulSet
metadata: {name: db}
spec:
  serviceName: db                 # the headless Service that owns the DNS names
  replicas: 3
  podManagementPolicy: OrderedReady   # or Parallel
  selector: {matchLabels: {app: db}}
  template:
    metadata: {labels: {app: db}}
    spec:
      containers:
        - name: postgres
          image: postgres:17-alpine
          volumeMounts: [{name: data, mountPath: /var/lib/postgresql/data}]
  volumeClaimTemplates:
    - metadata: {name: data}
      spec:
        accessModes: [ReadWriteOnce]
        resources: {requests: {storage: 1Gi}}
```

A StatefulSet doesn't make your software clustered. It gives you stable identity and storage;
*replication, failover and backups* are still the database's job (or an operator's, chapter 17).
Updates use `RollingUpdate` in reverse ordinal order, with `partition: N` to update only ordinals
≥ N, which is a built-in canary.

## 6.3 Job

A Job runs pods **until a number of them succeed**.

```yaml
apiVersion: batch/v1
kind: Job
metadata: {name: crunch}
spec:
  completions: 6            # need 6 successful pods (default 1)
  parallelism: 2            # run at most 2 at a time (default 1)
  backoffLimit: 3           # give up after 3 failed pods (exponential back-off between retries)
  activeDeadlineSeconds: 300  # give up after 5 minutes, whatever happens
  ttlSecondsAfterFinished: 3600   # garbage-collect the Job an hour after it finishes
  template:
    spec:
      restartPolicy: Never  # Never or OnFailure; Always isn't allowed
      containers:
        - name: work
          image: busybox:1.37
          command: ["sh", "-c", "echo crunching; sleep 3"]
```

* `restartPolicy: OnFailure` restarts the *container* in place; `Never` creates a *new pod* per
  retry, which keeps the failed pod's logs around for debugging.
* **Indexed Jobs** (`completionMode: Indexed`) give each pod an index `0…completions-1` in the env var
  `JOB_COMPLETION_INDEX` (and in its hostname). That's static work partitioning: "pod 3 processes
  shard 3". With a headless Service, indexed pods can even talk to each other (MPI-style).
* `podFailurePolicy` can say "exit code 42 means a bug, don't retry" or "eviction doesn't count
  as a failure".
* A Job's pods get the label `job-name=<job>`: `kubectl logs -l job-name=crunch`.
* `kubectl wait --for=condition=Complete job/crunch` in scripts and CI.

## 6.4 CronJob

A CronJob creates a Job on a **cron schedule** (in the controller-manager's time zone unless
you set `timeZone`).

```yaml
apiVersion: batch/v1
kind: CronJob
metadata: {name: nightly-report}
spec:
  schedule: "30 2 * * *"            # minute hour day-of-month month day-of-week
  timeZone: Europe/Paris
  concurrencyPolicy: Forbid         # Allow (default) | Forbid (skip if still running) | Replace
  startingDeadlineSeconds: 300      # if we missed the slot by more than 5 min, skip it
  successfulJobsHistoryLimit: 3
  failedJobsHistoryLimit: 1
  suspend: false
  jobTemplate:
    spec:
      backoffLimit: 2
      template:
        spec:
          restartPolicy: OnFailure
          containers:
            - name: report
              image: busybox:1.37
              command: ["sh", "-c", "date; echo generating report"]
```

Test a CronJob without waiting for the schedule:
`kubectl create job --from=cronjob/nightly-report manual-run-1`.

CronJobs are **at-least-once-ish**: a slot can be missed (controller down) or, in rare cases,
run twice. Make the work **idempotent**.

## 6.5 Choosing a workload

* Stateless, scale horizontally, any pod can serve any request → **Deployment**.
* Needs to run on every node, or on every node with a label → **DaemonSet**.
* Each replica owns data or has a role/identity → **StatefulSet** (or better, an operator for that
  database).
* Finishes → **Job**; finishes on a schedule → **CronJob**.
* Exactly one copy of a long-running singleton → a Deployment with `replicas: 1` and
  `strategy: Recreate` (the rolling update would briefly run two), or leader election inside the app.

## Exercises

| # | Name | What you practise |
|---|---|---|
| 6.1 | `daemonset` | a node agent on every node, including the control plane |
| 6.2 | `job` | completions, parallelism, backoff |
| 6.3 | `indexed-job` | static work partitioning with `JOB_COMPLETION_INDEX` |
| 6.4 | `cronjob` | schedule, concurrency policy, history, triggering by hand |
| 6.5 | `statefulset` | stable names, headless DNS, ordered start-up |
