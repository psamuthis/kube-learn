# Chapter 13 — Observability and debugging

> **Reading time:** ~40 min · **Exercises:** `exercises/ch13-observability-debugging/` (7)

Things will break. This chapter gives you a method and the tools to find out why: the signals
Kubernetes gives you (status, events, logs, metrics), how to get inside a container that has no
shell, and a catalogue of the failures you'll meet most often. The exercises are broken
scenarios: the setup breaks something, and you fix it in the live cluster.

## 13.1 A debugging method

Work **from the outside in** and **read before you act**:

```text
1. What's the symptom, precisely?            "HTTP 503 from the ingress for shop.example.com"
2. kubectl get <the thing> -o wide           status, READY, RESTARTS, AGE, node
3. kubectl describe <the thing>              conditions + EVENTS (bottom): the most useful output in K8s
4. Follow the chain of ownership/selection:  Ingress → Service → EndpointSlice → Pods → containers
                                              Deployment → ReplicaSet → Pods → events
5. kubectl logs [--previous]                  the app's own explanation
6. Get inside:  exec / debug / port-forward   test hypotheses from where the problem is
7. Change ONE thing, observe, repeat.
```

Events are objects too (`kubectl get events --sort-by=.lastTimestamp`, `-w` to follow,
`--field-selector type=Warning`), but they expire after **one hour** by default. Look early.

## 13.2 The usual suspects

| Symptom | Likely causes | Look at |
|---|---|---|
| `Pending` | no node fits: insufficient CPU/memory *requests*, taints, affinity, unbound PVC, quota | `describe pod` → `FailedScheduling` event |
| `ContainerCreating` for long | image pull in progress, volume can't mount (missing ConfigMap/Secret/PVC), CNI trouble | `describe pod` events |
| `ErrImagePull` / `ImagePullBackOff` | typo in name/tag, private registry without `imagePullSecrets`, `imagePullPolicy` vs. local images | event message |
| `CreateContainerConfigError` | env refers to a missing ConfigMap/Secret key | event message |
| `CrashLoopBackOff` | the process exits: bad command/args, missing config, failing liveness probe, can't reach a dependency at start | `logs --previous`, `describe` → Last State, Exit Code |
| `OOMKilled` (exit 137) | memory limit too low, or a leak | `describe` → Last State, `kubectl top` |
| exit code 1/2 | app error | logs |
| exit code 126/127 | command not executable / not found | `command`/`args` |
| `Running` but `0/1 READY` | readiness probe failing | `describe` → probe failure events |
| Service doesn't answer | selector/targetPort mismatch, no ready endpoints, NetworkPolicy, app bound to 127.0.0.1 | `get endpointslices`, chapter 7.6 |
| DNS failures | CoreDNS down, `dnsPolicy`/`dnsConfig`, egress NetworkPolicy blocking port 53 | `nslookup` from a debug pod |
| `Evicted` | node pressure (memory/disk), lowest QoS first | `describe node`, pod status message |
| Node `NotReady` | kubelet down, runtime down, network partition, disk full | `describe node` conditions, `journalctl -u kubelet` on the node |

## 13.3 Logs

```console
$ kubectl logs deploy/web                        # one pod of the deployment
$ kubectl logs -l app=web --prefix --tail=20     # several pods, prefixed with their name
$ kubectl logs web-abc -c sidecar                # a specific container
$ kubectl logs web-abc --previous                # the *previous* instance: essential for crash loops
$ kubectl logs -f --since=5m web-abc
```

Container logs are whatever the process writes to **stdout/stderr**. The runtime writes them to
files on the node (`/var/log/pods/…`), rotated by size. They're **lost when the pod is deleted**,
so production clusters ship them with a DaemonSet agent (Fluent Bit, Vector, the OpenTelemetry
Collector) to Loki, Elasticsearch or a cloud log service. Log to stdout, in a structured format
(JSON), with the pod name in each line (downward API).

## 13.4 Getting inside: exec, debug, port-forward

```console
$ kubectl exec -it web-abc -- sh                         # needs a shell in the image
$ kubectl port-forward deploy/web 8080:8080              # localhost:8080 → the pod
$ kubectl port-forward svc/web 8080:80
```

Minimal images (distroless, scratch) have no shell. **Ephemeral debug containers** add one to a
running pod without restarting it:

```console
$ kubectl debug -it web-abc --image=busybox:1.37 --target=app
#   --target=app shares the PID namespace of container "app": `ps` shows its processes,
#   and /proc/<pid>/root/ is its filesystem
$ kubectl debug web-abc -it --copy-to=web-debug --container=app -- sh   # a copy of the pod, with a changed command
$ kubectl debug node/kube-learn-m02 -it --image=busybox:1.37             # a pod on the node, host filesystem at /host
```

Ephemeral containers show up in `spec.ephemeralContainers` and can't be removed (the pod has to
be recreated). `nicolaka/netshoot` is a popular image packed with network tools.

## 13.5 Metrics

**metrics-server** (an addon you have) scrapes CPU/memory usage from every kubelet and serves the
`metrics.k8s.io` API. It's what `kubectl top` and the HPA (chapter 14) use:

```console
$ kubectl top nodes
$ kubectl top pods -A --sort-by=cpu
$ kubectl top pod web-abc --containers
```

It keeps only the latest values, with no history. Real monitoring is **Prometheus** (scraping
app `/metrics` endpoints plus kube-state-metrics, which exposes object state like "deployment
replicas available" as metrics, plus node-exporter) with **Grafana** dashboards and
**Alertmanager**. The kube-prometheus-stack Helm chart installs all of it. For traces, the
OpenTelemetry SDK + Collector, with Tempo or Jaeger.

The three golden signals per service are **latency, traffic, errors** (plus saturation). And
`kube_pod_container_status_restarts_total` going up is the best early warning there is.

## 13.6 Node-level debugging

When the problem is below the API (NotReady node, pods stuck in ContainerCreating for every
workload):

```console
$ kubectl describe node kube-learn-m02             # Conditions: Ready, MemoryPressure, DiskPressure, PIDPressure
$ minikube -p kube-learn ssh -n kube-learn-m02
$ systemctl status kubelet containerd
$ sudo journalctl -u kubelet --since "10 min ago" | tail -50
$ sudo crictl ps -a; sudo crictl logs <id>; sudo crictl pods
$ df -h; free -m
```

Chapter 16 has you break and repair a kubelet.

## Exercises

All scenario exercises (13.1–13.5) work the same way: the setup creates something broken in
`ex-13-N`, and you repair it **in the cluster** (`kubectl edit`, `set`, `patch`, `apply` of your own
files…). The checker only inspects the result. Use `--fresh` to start the scenario over.

| # | Name | Scenario |
|---|---|---|
| 13.1 | `crashloop` | a Deployment in CrashLoopBackOff |
| 13.2 | `pending` | pods that never get scheduled |
| 13.3 | `no-endpoints` | a Service with Running pods but no traffic |
| 13.4 | `config-error` | pods stuck in CreateContainerConfigError |
| 13.5 | `dns` | an app that can't resolve anything |
| 13.6 | `ephemeral-debug` | read a secret from a container with no shell, using `kubectl debug` |
| 13.7 | `top` | find the CPU hog with metrics-server |
