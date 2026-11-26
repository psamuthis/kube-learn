# Chapter 2 — Architecture: how a cluster works

> **Reading time:** ~60 min · **Exercises:** `exercises/ch02-architecture/` (5)

This is the most important chapter of the course. Every later chapter is "one more resource
type, and the controller that acts on it". Here we learn the machine they all plug into.

## 2.1 The big picture

```text
                         ┌──────────────────────── control plane ─────────────────────────┐
  kubectl / CI / you ───▶│ kube-apiserver ◀───────▶ etcd                                    │
  (HTTPS + client cert)  │   ▲ ▲ ▲ ▲   authn → authz → admission → validation → storage   │
                         │   │ │ │ └── kube-scheduler           (watches unscheduled pods)  │
                         │   │ │ └──── kube-controller-manager  (~40 controllers)          │
                         │   │ └────── cloud-controller-manager (LBs, routes, node info)   │
                         └───┼─┼────────────────────────────────────────────────────────────┘
               watch pods    │ │ watch services/endpointslices
           ┌─────────────────┴─┴──── worker node ───────────────────────┐
           │ kubelet ──CRI──▶ containerd ──▶ runc ──▶ [pod] [pod] [pod]  │
           │    └─ CNI plugin (calico) gives each pod an IP              │
           │ kube-proxy: programs iptables/nftables for Service IPs      │
           └─────────────────────────────────────────────────────────────┘
```

Two invariants to remember:

1. **Only the API server talks to etcd.** Every other component is a client of the API server,
   like kubectl.
2. **Components never call each other.** The scheduler doesn't tell the kubelet to start a pod.
   It writes `spec.nodeName` on the Pod object, and the kubelet, which *watches* pods bound to its
   node, notices. All coordination goes through state in the API: a **blackboard architecture**.

This is what makes Kubernetes robust: any component can crash and restart. On restart it
**re-lists** the current state and carries on, with no messages lost because there were no
messages, only state.

## 2.2 The control plane

### kube-apiserver

A stateless REST server in front of etcd, and the only component with real logic about
*requests*. Each request goes through a pipeline:

```text
HTTP request
  → authentication   who are you?        client cert CN/O, bearer token (ServiceAccount, OIDC), …
  → authorization    may you do this?    RBAC (chapter 12), Node authorizer, webhooks
  → mutating admission                   defaults, inject things (e.g. ServiceAccount token volume)
  → schema validation                    OpenAPI types, field rules
  → validating admission                 policies (PodSecurity, ValidatingAdmissionPolicy/CEL, webhooks)
  → etcd write                           with optimistic concurrency (resourceVersion)
  → notify watchers
```

It scales horizontally (run 3 behind a load balancer) because all state is in etcd.

Key API concepts you'll use constantly:

* **resourceVersion**: every object has one (it's etcd's revision). An update must carry the
  version it read; if someone else wrote in between, you get `409 Conflict` and must retry. That's
  **optimistic concurrency**, the same as compare-and-swap.
* **watch**: `GET /api/v1/pods?watch=true&resourceVersion=N` streams `ADDED`/`MODIFIED`/`DELETED`
  events from revision N onward. Controllers are built on **list + watch** (the "informer"
  pattern: list once, then watch, and keep a local cache).
* **spec vs status**: users write `spec`, controllers write `status` (through a separate
  `/status` subresource, so the two don't clobber each other).

### etcd

A distributed, strongly consistent key-value store (Raft consensus). Kubernetes stores every
object as a protobuf value under a key like:

```text
/registry/pods/<namespace>/<name>
/registry/deployments/<namespace>/<name>
/registry/configmaps/kube-system/coredns
```

* Run **3 or 5 members** (Raft needs a majority: 3 survives 1 failure, 5 survives 2).
* It's the **only stateful part** of the control plane: back it up (chapter 16).
* It's sensitive to disk latency (fsync on every write) and its size is capped (default 2 GB,
  8 GB max), which is why you shouldn't put big blobs in ConfigMaps.

In exercise 2.2 you'll read raw keys straight out of etcd with `etcdctl`.

### kube-scheduler

Watches for pods with no `spec.nodeName`, picks a node, and writes a **Binding**. For each pod:

1. **Filter** (predicates): nodes with enough unreserved CPU/memory for the pod's *requests*,
   matching `nodeSelector`/affinity, tolerating the node's taints, free host ports, volume
   topology…
2. **Score** (priorities): spread pods of the same service, prefer nodes that already have the
   image, balance utilisation, honour preferred affinities…
3. **Bind** to the highest score.

It's a constraint-satisfaction search, one pod at a time, with a pluggable framework of filter
and score plugins. If no node passes the filter, the pod stays `Pending` with an event like
`0/3 nodes are available: 3 Insufficient cpu`. Chapter 11 covers how to steer it.

### kube-controller-manager

One binary running ~40 **controllers**, each a reconcile loop for one kind of object:

| Controller | Watches | Does |
|---|---|---|
| Deployment | Deployments, ReplicaSets | creates/scales ReplicaSets for rollouts |
| ReplicaSet | ReplicaSets, Pods | creates/deletes Pods to match `replicas` |
| Node lifecycle | Nodes, Leases | marks nodes NotReady, evicts pods from dead nodes |
| EndpointSlice | Services, Pods | lists ready pod IPs behind each Service |
| Job / CronJob | Jobs, CronJobs | runs pods to completion / on a schedule |
| Namespace | Namespaces | deletes everything inside a terminating namespace |
| Garbage collector | ownerReferences | deletes dependents when their owner is deleted |
| ServiceAccount, token | … | creates default ServiceAccounts, … |

Only one copy is active at a time: replicas use **leader election** through a `Lease` object
(`kubectl -n kube-system get leases`).

### cloud-controller-manager

Cloud-specific loops (create a load balancer for `type: LoadBalancer` Services, label nodes
with zone/instance type, delete Node objects whose VM is gone). Not present in minikube; you'll see
how `LoadBalancer` behaves without it in chapter 7.

## 2.3 The node

### kubelet

The agent on every node, and the only component that actually starts containers. It:

* watches the API for pods with `spec.nodeName == <me>`;
* asks the runtime (via **CRI**) to create the pod sandbox (its network namespace, via **CNI**),
  pull images and start containers;
* runs **probes** and restarts containers per `restartPolicy`;
* mounts **volumes** (ConfigMaps, Secrets, PVCs via CSI drivers);
* reports pod `status` and node status, and renews the node's **Lease** every 10 s (the
  heartbeat). If no renewal comes for 40 s, the node lifecycle controller marks the node
  `NotReady`;
* runs **static pods**: manifests in a directory on the node (`/etc/kubernetes/manifests`) that
  it runs *without* the API server, and then reports to the API as read-only **mirror pods**.
  That's how kubeadm bootstraps the control plane: the API server itself is a static pod!

The kubelet is a systemd service, not a pod (it has to exist before pods do).

### Container runtime

containerd + runc (chapter 1.4). The kubelet only speaks CRI, so the runtime is swappable.

### kube-proxy

Watches Services and EndpointSlices and programs the node's packet filter (iptables, IPVS or
nftables) so that traffic to a Service's virtual IP gets DNAT'ed to one of the backing pod IPs.
It doesn't proxy traffic itself (its name is historical). Chapter 7.

### CNI plugin

Gives every pod an IP and makes pod IPs routable between nodes. Calico here; others are Cilium
(eBPF), Flannel, and the cloud providers' own (AWS VPC CNI…). It runs as a DaemonSet plus a binary
the runtime calls when creating a pod sandbox.

### Add-ons

Things that *run on* the cluster, as ordinary pods: **CoreDNS** (cluster DNS), the ingress
controller, metrics-server, the storage provisioner, dashboards…

## 2.4 What happens when you `kubectl apply` a Deployment

Let's trace `kubectl apply -f deploy.yaml` (3 replicas of kubeapp) end to end:

```text
 1. kubectl   → POST /apis/apps/v1/namespaces/demo/deployments          (authn, authz, admission)
 2. apiserver → etcd: /registry/deployments/demo/web                      → notify watchers
 3. Deployment controller (watching Deployments) sees ADDED
              → creates ReplicaSet web-7c9f8d…  (ownerReference: the Deployment)
 4. ReplicaSet controller sees the RS, counts 0 matching pods, wants 3
              → creates 3 Pods web-7c9f8d…-abcde  (ownerReference: the RS), no nodeName
 5. Scheduler sees 3 unscheduled pods → filters/scores → POST …/pods/<p>/binding  (nodeName set)
 6. kubelet on each chosen node sees a pod bound to it
              → CRI RunPodSandbox (CNI assigns IP) → PullImage → CreateContainer → StartContainer
              → runs readiness probe → PATCH pod status: Ready=True, podIP=10.244.1.7
 7. EndpointSlice controller sees ready pods matching the Service selector → updates the slice
 8. kube-proxy on every node sees the slice → rewrites iptables rules
 9. Deployment controller sees RS has 3 available → updates Deployment status
                                         → `kubectl rollout status` returns
```

Nine independent loops, no orchestration script. If the kubelet on a node dies at step 6,
nothing breaks: the node goes NotReady, the pod is eventually evicted, the ReplicaSet controller
sees only 2 pods and creates a replacement, and the scheduler puts it elsewhere.

`kubectl get events -w` in a second terminal while you apply something shows this as it happens.
Try it in exercise 2.4.

## 2.5 Desired state, reconciliation and level-triggering

A controller is a loop of the form:

```python
while True:
    desired  = read_spec()        # from the API (cached via watch)
    observed = read_world()       # from the API, or the outside world (cloud APIs, containers…)
    for action in diff(desired, observed):
        do(action)                # usually: create/update/delete other API objects
    write_status(observed)
    wait_for_change_or_timeout()  # re-run periodically even without events ("resync")
```

Two properties make this robust:

* **Level-triggered, not edge-triggered.** A controller doesn't react to "a pod was deleted"
  (an edge). It reacts to "there are 2 pods and there should be 3" (a level). Missed or
  duplicated events don't matter: the next pass sees the current level and converges. Like a
  thermostat.
* **Idempotent actions.** Running a reconcile pass twice is harmless. If a step fails halfway,
  the next pass picks up from the current state.

In type-theory terms: `reconcile` is a function iterated to a **fixed point**, and the system is
correct if every reachable state converges. You'll write one in chapter 17.

Corollaries you'll run into:

* **Everything is eventually consistent.** `kubectl apply` returns as soon as the object is
  stored, *not* when it's running. Use `kubectl rollout status` or `kubectl wait`.
* **You can't fight a controller.** Edit a pod owned by a ReplicaSet (or delete it) and the
  ReplicaSet "fixes" it. Change the owner instead.
* **Ownership forms a tree**: Deployment → ReplicaSet → Pod, linked by `metadata.ownerReferences`.
  Delete the root and the **garbage collector** cascades down.

## 2.6 A cluster built by kubeadm (what's on your control-plane node)

minikube used kubeadm, so your control-plane node looks like a typical self-managed cluster:

```console
$ minikube -p kube-learn ssh
$ ls /etc/kubernetes/manifests/      # static pods: etcd, kube-apiserver, controller-manager, scheduler
$ sudo cat /etc/kubernetes/manifests/kube-apiserver.yaml   # every flag of the API server
$ systemctl status kubelet           # kubelet is a systemd unit
$ sudo cat /var/lib/kubelet/config.yaml   # its config, including staticPodPath
$ ls /var/lib/minikube/certs/         # the cluster PKI (kubeadm default: /etc/kubernetes/pki)
$ sudo crictl ps                     # running containers, the CRI view
```

Managed clusters (GKE/EKS/AKS) hide the control plane from you entirely: you see only worker
nodes, and the API server is an endpoint the provider runs.

## 2.7 Talking to the API without kubectl

kubectl is just an HTTP client. `kubectl proxy` opens an authenticated tunnel on localhost:

```console
$ kubectl proxy --port 8001 &
$ curl -s localhost:8001/api/v1/namespaces/default/pods | head
$ curl -s localhost:8001/apis | python3 -m json.tool | grep '"name"' | head     # API groups
$ curl -s "localhost:8001/api/v1/namespaces/default/pods?watch=true"           # a raw watch stream
$ kubectl get pods -v=8           # shows the HTTP requests kubectl makes
```

URL shape: `/api/v1/...` for the core group, `/apis/<group>/<version>/...` for the rest,
`/namespaces/<ns>/<resource>/<name>` for namespaced objects, and subresources like `/status`,
`/scale`, `/log`, `/exec`, `/binding`.

## Exercises

| # | Name | What you practise |
|---|---|---|
| 2.1 | `control-plane` | find the control-plane components, static pods, runtime and leases |
| 2.2 | `etcd` | read Kubernetes objects straight out of etcd with `etcdctl` |
| 2.3 | `raw-api` | create an object with `curl` through `kubectl proxy` |
| 2.4 | `reconcile` | kill pods and watch controllers put them back; follow owner references |
| 2.5 | `static-pod` | run a pod on a node with no API call at all |
