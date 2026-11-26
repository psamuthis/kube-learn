# Chapter 4 — Pods

> **Reading time:** ~50 min · **Exercises:** `exercises/ch04-pods/` (7)

A **Pod** is the smallest thing Kubernetes schedules: one or more containers that are always
placed together on one node and share a network namespace (one IP, one `localhost`), optionally
volumes, and a lifecycle. You'll rarely create bare pods in production (controllers do that,
chapter 5), but every workload is a pod template, so everything here applies everywhere.

## 4.1 Why pods and not containers?

Because some processes belong together: an app and a log shipper reading its files, an app and
a proxy (service mesh sidecar), an app and a process that refreshes its credentials. They need
to share a network namespace and files and to be scheduled as a unit. A pod is that unit,
somewhere between a logical host and a process group.

The shared parts:

* **Network**: one IP and one port space; containers talk over `localhost`. A hidden
  **pause container** ("sandbox") holds the network namespace, so app containers can restart
  without losing the IP.
* **Volumes**: declared at pod level and mounted into any of its containers.
* Optional: the PID namespace (`shareProcessNamespace: true`).

Rule of thumb: **one main process per pod**. Things that scale independently go in different
pods. Web server and database in one pod is an anti-pattern.

## 4.2 The pod spec, a guided tour

```yaml
apiVersion: v1
kind: Pod
metadata:
  name: web
  labels: {app: web}
spec:
  containers:
    - name: app
      image: kubeapp:1.0
      imagePullPolicy: IfNotPresent
      command: ["python"]                 # overrides ENTRYPOINT
      args: ["/app/app.py"]               # overrides CMD
      workingDir: /app
      ports:
        - name: http                      # name ports: probes and Services can refer to "http"
          containerPort: 8080
          protocol: TCP
      env:
        - name: MESSAGE
          value: "hi"
        - name: POD_NAME
          valueFrom: {fieldRef: {fieldPath: metadata.name}}   # downward API, chapter 9
      resources:
        requests: {cpu: 100m, memory: 64Mi}
        limits:   {memory: 128Mi}
      readinessProbe: {httpGet: {path: /ready, port: http}}
      livenessProbe:  {httpGet: {path: /healthz, port: http}}
      volumeMounts:
        - {name: scratch, mountPath: /tmp}
  volumes:
    - name: scratch
      emptyDir: {}
  restartPolicy: Always                   # Always | OnFailure | Never
  terminationGracePeriodSeconds: 30
  nodeSelector: {}                        # chapter 11
  serviceAccountName: default             # chapter 12
```

`containerPort` is **informational**: the process listens on whatever it listens on. But naming
ports lets probes and Services say `port: http` instead of repeating numbers.

## 4.3 Lifecycle: phases, states, restarts

The **pod phase** is a coarse summary:

| Phase | Meaning |
|---|---|
| `Pending` | accepted, but not all containers are running: not scheduled yet, pulling images, init containers running |
| `Running` | bound to a node, at least one container running (or restarting) |
| `Succeeded` | all containers exited 0 and won't restart (Jobs) |
| `Failed` | all containers terminated, at least one with failure, and won't restart |
| `Unknown` | the node stopped reporting |

Each **container** has a state (`Waiting` with a reason, `Running`, `Terminated` with exit code
and reason) and a `lastState`. The STATUS column of `kubectl get pods` shows the most interesting
reason: `ContainerCreating`, `ErrImagePull`, `ImagePullBackOff`, `CrashLoopBackOff`,
`OOMKilled`, `Completed`, `Error`, `Terminating`…

**`restartPolicy`** applies to every container in the pod. With `Always` (the default; required
for Deployments) and `OnFailure`, the kubelet restarts exited containers **in place** (same pod,
same node, same IP) with exponential back-off: 10 s, 20 s, 40 s… capped at 5 min. That back-off
is **CrashLoopBackOff**. It's not an error type itself: it means "this container keeps exiting;
look at `kubectl logs --previous`".

The pod's **conditions**: `PodScheduled`, `Initialized`, `ContainersReady`, `Ready`. **Ready** is
what Services care about: only Ready pods receive traffic.

Pods are **mortal and mostly immutable**. A pod is never moved: if its node dies, it's replaced
by a *new* pod (new name, new IP) created by its controller. Apart from `image`, a few
scheduling-gate and toleration fields and the `resize` subresource, you can't change a pod's
spec: delete and recreate.

## 4.4 Init containers and sidecars

**Init containers** run **before** the app containers, **one at a time, in order**, each to
completion. If one fails, the kubelet retries per `restartPolicy`. Use them for "wait until the
database DNS resolves", "render a config file", "run migrations", "fix volume permissions".
They can use a different image (with tools the app image doesn't have).

**Sidecar containers** (stable since 1.33) are init containers with `restartPolicy: Always`:
they start before the app containers, *keep running* alongside them, and are stopped *after*
them. That gives log shippers and proxies a correct start and stop order:

```yaml
spec:
  initContainers:
    - name: wait-for-db
      image: busybox:1.37
      command: ["sh", "-c", "until nslookup db.shop.svc.cluster.local; do sleep 1; done"]
    - name: log-shipper            # a native sidecar
      image: busybox:1.37
      restartPolicy: Always
      command: ["sh", "-c", "tail -F /logs/app.log"]
      volumeMounts: [{name: logs, mountPath: /logs}]
  containers:
    - name: app
      image: kubeapp:1.0
      volumeMounts: [{name: logs, mountPath: /logs}]
  volumes:
    - {name: logs, emptyDir: {}}
```

Before 1.28, sidecars were just extra regular containers, with no ordering guarantees (and Jobs
never finished because the sidecar never exited). You'll still see that style a lot.

## 4.5 Probes

The kubelet probes containers three ways: `httpGet` (2xx–3xx is success), `tcpSocket`
(connect succeeds), `exec` (exit 0), and `grpc`. There are three kinds of probe, with very
different consequences:

| Probe | On failure | Use for |
|---|---|---|
| **readiness** | pod marked *not Ready* → removed from Service endpoints. **Not restarted.** | "can I take traffic now?" (warming caches, overloaded, dependency down) |
| **liveness** | container **killed and restarted** | "am I irrecoverably stuck?" (deadlock) |
| **startup** | blocks the other two until it succeeds once; if it never does, restart | slow-starting apps, so liveness can stay strict |

```yaml
readinessProbe:
  httpGet: {path: /ready, port: http}
  initialDelaySeconds: 0     # wait before the first probe
  periodSeconds: 5           # how often
  timeoutSeconds: 1          # per attempt
  failureThreshold: 3        # consecutive failures before "failed"
  successThreshold: 1        # consecutive successes before "ok" (readiness only)
livenessProbe:
  httpGet: {path: /healthz, port: http}
  periodSeconds: 10
  failureThreshold: 3        # → restart after ~30 s of failure
startupProbe:
  httpGet: {path: /healthz, port: http}
  periodSeconds: 2
  failureThreshold: 30       # allow up to 60 s to start
```

Probe wisdom, learned the hard way:

* **Liveness must not depend on anything external.** If the DB is down and your liveness probe
  checks the DB, Kubernetes restarts *every* pod in a loop and turns a DB blip into an outage.
  Liveness = "is this process wedged?"; readiness = "should I get traffic?".
* No liveness probe is better than a bad one. A crashed process already restarts without one.
* Readiness failing on *all* pods at once is an outage too (no endpoints).
* Give probes their own cheap endpoints (`/healthz`, `/ready`).

## 4.6 Resources: requests, limits and QoS

```yaml
resources:
  requests: {cpu: 250m, memory: 128Mi}   # what the scheduler reserves for you
  limits:   {cpu: "1", memory: 256Mi}    # what the kernel enforces (cgroups)
```

Units: CPU in cores (`1`, `0.5`, `250m` = 250 millicores); memory in bytes with suffixes
(`Mi`/`Gi` = powers of 2, `M`/`G` = powers of 10, so beware: `128M` ≠ `128Mi`).

* **Requests** are used for **scheduling** (a node fits a pod if the sum of requests fits its
  *allocatable* capacity) and for CPU **weighting** under contention. Actual usage can be higher.
* **Limits**: going over the **memory** limit means the container gets **OOMKilled** (exit code
  137 = 128 + SIGKILL). Going over the **CPU** limit means you get **throttled** (slowed, never killed).
* No limit means the container may use whatever's free on the node.

The combination determines the pod's **QoS class** (`status.qosClass`), which decides who gets
evicted first when the *node* runs out of memory:

| QoS class | Rule | Evicted |
|---|---|---|
| **Guaranteed** | every container has requests = limits for both CPU and memory | last |
| **Burstable** | at least one request or limit set, not Guaranteed | in between |
| **BestEffort** | no requests or limits at all | first |

Common production advice: always set requests (otherwise the scheduler is flying blind); set a
memory limit (often = request); think twice about CPU limits (throttling hurts latency, and
requests already give fair sharing). Since 1.33 you can **resize** CPU/memory of a running pod
in place (`kubectl patch pod … --subresource resize`).

## 4.7 Termination

When a pod is deleted (by you, a rollout, a drain…):

1. The API sets `deletionTimestamp`; the pod shows `Terminating`. *At the same time* it's removed
   from Service endpoints (asynchronously, so for a moment traffic may still arrive).
2. The kubelet runs each container's `preStop` hook (if any), then sends **SIGTERM** to PID 1.
3. It waits up to `terminationGracePeriodSeconds` (default 30) in total, then sends **SIGKILL**.

So your app must **handle SIGTERM**: stop accepting, finish in-flight requests, exit. And because
endpoint removal races with SIGTERM, a short `preStop: sleep 5` (or the app delaying its
shutdown, like kubeapp's `SHUTDOWN_DELAY`) avoids dropped requests during rollouts. Chapter 5 puts
this to use.

## 4.8 Debugging pods, the first toolkit

```console
$ kubectl get pod web -o wide                 # phase, restarts, node, IP
$ kubectl describe pod web                    # conditions, container states, EVENTS ← read these first
$ kubectl logs web [-c container] [-f] [--previous] [--since=10m]
$ kubectl exec -it web -c app -- sh
$ kubectl get pod web -o jsonpath='{.status.containerStatuses[*].lastState}'
$ kubectl port-forward pod/web 8080:8080      # then curl localhost:8080 from your machine
$ kubectl debug -it web --image=busybox --target=app   # an ephemeral debug container (chapter 13)
```

## Exercises

| # | Name | What you practise |
|---|---|---|
| 4.1 | `pod-spec` | ports, env, command/args, labels |
| 4.2 | `multi-container` | two containers sharing a volume and `localhost` |
| 4.3 | `init-containers` | ordering with init containers, waiting for a dependency |
| 4.4 | `probes` | fix readiness/liveness probes; a slow starter needs a startup probe |
| 4.5 | `qos` | requests/limits and the three QoS classes |
| 4.6 | `oomkill` | diagnose an OOMKilled container from its status, then fix it |
| 4.7 | `native-sidecar` | a sidecar as an init container with `restartPolicy: Always` |
