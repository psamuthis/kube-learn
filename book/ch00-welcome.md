# Chapter 0 — Welcome to Kubernetes

> **Reading time:** ~30 min · **Exercises:** `exercises/ch00-welcome/` (3)

## 0.1 What Kubernetes is

Kubernetes (Greek *κυβερνήτης*, "helmsman"; often written **K8s**, with 8 letters elided) is a
**distributed system for running other distributed systems**. You give it a description of what
you want running ("three copies of this container image, reachable on port 80 under this name,
each with 256 MiB of memory, never two on the same machine") and it keeps the world looking like
that description, forever, while machines crash, deploys happen and traffic shifts.

The shortest accurate definition:

> Kubernetes is a **database of desired state** (the API server and etcd) plus a set of
> **control loops** (controllers) that continuously drive *actual* state towards it.

Everything else (pods, deployments, services, volumes, RBAC, operators) is a *type* stored in that
database plus the loop that acts on it. Once this clicks, the 70-odd built-in resource kinds stop
looking like an arbitrary zoo, and writing your own (chapter 17) becomes natural.

A short history, because it explains a lot of design decisions:

| Year | Event |
|---|---|
| 2003– | Google runs everything on **Borg**, an internal cluster manager (later **Omega**). |
| 2013 | Docker makes Linux containers usable by mortals: images + a simple CLI. |
| 2014 | Google open-sources **Kubernetes**, a rewrite of Borg's ideas in Go, designed for everybody. |
| 2015 | Kubernetes **1.0**; Google donates it to the new **Cloud Native Computing Foundation** (CNCF). |
| 2017–18 | The "orchestrator wars" end: Docker Swarm and Mesos lose; every cloud ships managed K8s (GKE, EKS, AKS). |
| 2020–22 | dockershim removed (1.24): Kubernetes talks to runtimes via **CRI** (containerd, CRI-O). |
| 2023– | Gateway API GA, sidecar containers, in-place pod resize, CEL everywhere, DRA for GPUs… three minor releases a year. |

Borg's lessons that shaped Kubernetes: **declarative** configuration beats imperative scripts;
**labels** beat hierarchies for grouping things; every workload gets its own **IP address**; and
the system should be built from **small independent controllers** talking only through the API.

## 0.2 What Kubernetes is good at (and for)

* **Running many services on a shared pool of machines** — bin-packing them by declared
  CPU/memory, restarting what crashes, rescheduling what was on a dead node.
* **Zero-downtime deploys** — rolling updates, health-checked, with one-command rollback.
* **Service discovery and load balancing** — stable names and virtual IPs in front of a moving
  set of pods.
* **Self-service infrastructure** — teams describe what they need in YAML; the platform team
  writes the policies (RBAC, quotas, admission rules).
* **A common API for everything** — load balancers, certificates, DNS records, databases, GPUs:
  with operators, *anything* can be a Kubernetes object. That's why K8s became "the cloud's OS".

Where it's *less* appropriate:

* **One small app.** A single VM with systemd, or a PaaS (Fly, Render, Cloud Run) is far simpler.
  Kubernetes has a real fixed cost in complexity: it's a platform for building platforms.
* **Teams without operational capacity.** Use a managed offering (GKE/EKS/AKS) if you use it at all;
  upgrades happen three times a year.
* **Stateful systems you don't understand well.** K8s can run databases (chapter 10, StatefulSets,
  operators), but it doesn't make them easier to operate; it makes it easier to automate what you
  already know how to do.

## 0.3 The mental model in one picture

```text
   you ──kubectl apply──▶ ┌──────────── control plane ────────────┐
                          │  kube-apiserver ◀──▶ etcd (the state)  │
                          │     ▲     ▲     ▲                      │
                          │     │     │     └── controller-manager │  "make actual = desired"
                          │     │     └──────── scheduler          │  "pick a node for each pod"
                          └─────┼──────────────────────────────────┘
                                │ watch / report status
          ┌──────── node ───────┴──┐   ┌──────── node ──────────┐
          │ kubelet ─CRI─▶ containerd │   │ kubelet ─▶ containerd │   "run these pods here"
          │ kube-proxy  [pod][pod] │   │ kube-proxy [pod]       │
          └────────────────────────┘   └────────────────────────┘
```

Nobody calls anybody: every component **watches** the API server for the objects it cares about
and **writes** its results back. Chapter 2 takes this apart piece by piece.

Coming from your background:

* **From functional programming:** a controller computes `reconcile : (desired, observed) → actions`
  and is re-run until it reaches a **fixed point** (no more actions). Objects are records with a
  `spec` (the input you write) and a `status` (the output the system writes).
* **From Rust:** the API server is a typed store, the schemas are the types, and admission control
  is a type checker that runs at write time. `kubectl apply --dry-run=server` is your `cargo check`.
* **From C/systems:** a container is a normal Linux process with namespaces and cgroups (chapter 1).
  Kubernetes is "just" a very elaborate way of starting processes on remote machines with the
  right flags.

## 0.4 Your lab: minikube

This course uses a **3-node minikube cluster** called `kube-learn`, running in Docker. minikube
installs real, upstream Kubernetes with **kubeadm** (the same tool many production clusters are
built with), so what you see (static pods, certificates, etcd, kubelet config) is what you'd
find on a real machine. Each "node" is a Docker container with systemd, a container runtime and a
kubelet inside.

```console
$ ./course cluster up          # minikube start -p kube-learn --nodes 3 --cni calico …
                               # + addons: ingress, metrics-server, local-path storage
                               # + builds the course's demo image (kubeapp) onto every node
$ kubectl get nodes -o wide
NAME             STATUS   ROLES           VERSION   INTERNAL-IP    CONTAINER-RUNTIME
kube-learn       Ready    control-plane   v1.34.0   192.168.49.2   docker://28.4.0
kube-learn-m02   Ready    <none>          v1.34.0   192.168.49.3   docker://28.4.0
kube-learn-m03   Ready    <none>          v1.34.0   192.168.49.4   docker://28.4.0
```

* It needs about **10 GB of RAM** free (3 × 3 GB). Short on memory? `./course cluster up --single`
  gives a 1-node cluster; everything except the scheduling chapter (11) works.
* `./course cluster down` stops it (state is kept), `./course cluster delete` throws it away.
* **Calico** is the network plugin, so NetworkPolicies (chapter 12) are actually enforced.
* kubectl warns if it's more than one minor version away from the server. The course only uses
  stable APIs, so a newer client works fine. If you want an exact match, use
  `minikube -p kube-learn kubectl -- …`.

## 0.5 kubectl, the first ten commands

`kubectl` is a thin HTTP client for the API server. Its config lives in `~/.kube/config`, which
holds **clusters** (URL + CA), **users** (credentials) and **contexts** (cluster + user + default
namespace). minikube added a context called `kube-learn` and made it current.

```console
$ kubectl config get-contexts                 # which cluster am I talking to?
$ kubectl cluster-info                        # API server URL, CoreDNS
$ kubectl api-resources                       # every kind the server knows
$ kubectl get pods -A                         # all pods, all namespaces
$ kubectl get pods -n kube-system -o wide     # with node and IP
$ kubectl describe pod <name> -n kube-system  # human summary + recent events
$ kubectl run hello --image=nginx:1.29        # imperative: create a pod
$ kubectl logs hello                          # its stdout
$ kubectl exec -it hello -- sh                # a shell inside it
$ kubectl delete pod hello
```

**Imperative vs declarative.** `kubectl run`/`create`/`scale` are fine for poking around, but real
work is **declarative**: you keep YAML files (under version control) and `kubectl apply -f` them.
`apply` computes the difference between your file and the live object and sends only that. Run
it twice and the second run changes nothing (it's idempotent). Every exercise in this course is
declarative.

A minimal object looks like this, and every Kubernetes object has the same four top-level fields:

```yaml
apiVersion: v1          # API group/version: "v1" is the core group
kind: Pod               # the type
metadata:               # identity: name, namespace, labels, annotations
  name: hello
  labels:
    app: hello
spec:                   # desired state: you write it
  containers:
    - name: web
      image: nginx:1.29
      ports:
        - containerPort: 80
# status:               # observed state: the system writes it (kubectl get -o yaml shows it)
```

Useful flags you'll type a thousand times: `-o wide`, `-o yaml`, `-o json`, `-o jsonpath=…`,
`-l app=web` (label selector), `-w` (watch), `-n NAMESPACE`, `-A` (all namespaces),
`--dry-run=client -o yaml` (print the object instead of creating it, a great way to start a manifest).

Set up shell completion and an alias now; you will thank yourself:

```console
$ echo 'source <(kubectl completion bash); alias k=kubectl; complete -o default -F __start_kubectl k' >> ~/.bashrc
```

## 0.6 How the exercises work

Each exercise is a directory under `exercises/` with:

* `README.md`: the task.
* Some `*.yaml` files to complete (look for `# TODO`) or to write from scratch.
* `answers.txt` for exploration exercises: `key: value` lines you fill in after investigating
  the cluster. Values starting with `$ ` are run as a shell command, so you can also answer with
  the command that finds the answer.
* `check.py`, the "tests": what the checker asserts about the live cluster. Read it when you're
  stuck. Don't edit it.

`./course check 0.2` creates a namespace `ex-0-2`, `kubectl apply`s every `*.yaml` in the
directory into it, and then inspects the cluster. Some exercises have a **setup** step that puts
something (usually broken) into the namespace the first time; `--fresh` starts over.

```console
$ ./course watch        # ⭐ checks the current exercise every time you save a file
$ ./course hint 0.2     # stuck?
$ ./course list         # progress
```

Work in the exercise namespace when you poke around by hand: `kubectl -n ex-0-2 get pods`. Or
switch your default for a while: `kubectl config set-context --current --namespace ex-0-2`.

## 0.7 Where to learn more

* The official docs at <https://kubernetes.io/docs/>, especially *Concepts* and the API
  reference (`kubectl explain` is the offline version).
* *Kubernetes the Hard Way* (Kelsey Hightower): builds a cluster by hand. We do a guided tour of
  it in chapter 16.
* The Kubernetes source (<https://github.com/kubernetes/kubernetes>) is surprisingly readable Go.
  `pkg/controller/` is where the built-in controllers live.
* The CKA/CKAD exam curricula make good checklists; this course covers both.

## Exercises

| # | Name | What you practise |
|---|---|---|
| 0.1 | `cluster-up` | starting the lab, `kubectl get nodes`, `version`, `config` |
| 0.2 | `first-pod` | your first manifest: a Pod with a label and a port |
| 0.3 | `kubectl-tour` | `get`/`describe`/`-o wide`/`cluster-info` to answer questions about the cluster |
