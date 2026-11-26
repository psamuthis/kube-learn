# ☸️ kube-learn — a hands-on Kubernetes course

A self-paced Kubernetes course in **19 chapters** and **93 exercises** that run against a real
3-node cluster. It starts with "what is a container, really?", goes through the architecture,
every core resource and writing your own Deployments, and ends with operations, security, your
own operator, and a production-grade capstone.

It's written for someone who already programs (C, Scala, OCaml, Python, Rust…). Concepts are
explained the way a programmer wants them: controllers as fixed-point loops, the scheduler as a
filter/score search, RBAC as an allow-list, and so on. You'll learn by **doing things to a
live cluster** and having the result checked.

## Quick start

```console
$ ./course cluster up      # a 3-node minikube cluster (containerd, Calico, ingress, metrics, storage)
                           # + builds the course's demo image onto every node. ~5–10 min the first time.
$ ./course list            # see all chapters and exercises
$ ./course watch           # ⭐ start: re-checks the current exercise every time you save
```

Then, for each chapter:

1. **Read** `book/chXX-*.md`.
2. **Do** the exercises in `exercises/chXX-*/`. Each one is a directory with a `README.md`
   (the task), YAML files with `# TODO`s (or nothing, when you write from scratch), sometimes an
   `answers.txt` to fill in after investigating, and a `check.py` that inspects the cluster.
3. **Compare** with `solutions/` once you pass. There's often more than one good answer.

**Requirements:** Docker, `kubectl`, `minikube`, Python ≥ 3.11, `openssl`, and about 10 GB of free
RAM for the 3 nodes (`./course cluster up --single` runs everything except chapter 11 on one
node). Helm is optional: chapter 15 falls back to the `alpine/helm` Docker image.

## The runner: `./course`

| Command | What it does |
|---|---|
| `./course list` | progress overview (✓ done, → current) |
| `./course watch [ID]` | checks the current exercise on every save; Enter moves on when it passes (and cleans up its namespace) |
| `./course next` | checks the first unfinished exercise once |
| `./course check 5.1` | checks one exercise (IDs are `chapter.exercise`; part of a name works too) |
| `./course check 5.1 --fresh` | deletes the exercise's namespace first (and re-runs its setup) |
| `./course hint 5.1` | progressive hints |
| `./course reset 5.1` | restores an exercise's files to their initial state (asks first) |
| `./course solution 5.1` | where the reference solution is |
| `./course clean [ID]` | deletes exercise namespaces (and cluster-wide leftovers) to free the cluster |
| `./course verify [CH]` | re-checks everything you did (or one chapter) and refreshes your progress |
| `./course cluster up \| down \| delete \| status \| images` | manages the minikube profile `kube-learn` |
| `-v` | prints every kubectl command a check runs |

**How a check works:** exercise `N.M` gets its own namespace `ex-N-M`. The checker creates it
(running the exercise's *setup* the first time: some exercises start with something broken),
`kubectl apply`s the exercise's `*.yaml` files (or `-k` a kustomization), then runs `check.py`,
which inspects the live cluster and prints ✓/✗ lines. Values in `answers.txt` that start with
`$ ` are run as shell commands, so you can answer with the command that finds the answer.

Progress is stored in `.course-progress`. You can always work without the runner:
`kubectl -n ex-5-1 apply -f exercises/ch05-deployments/01-first-deployment/`.

## Course map

| Ch | Topic | You'll build / practise | Ex. |
|---|---|---|---|
| 0 | [Welcome](book/ch00-welcome.md) | what K8s is (and isn't for), the lab, kubectl basics, your first pod | 3 |
| 1 | [Containers](book/ch01-containers.md) | namespaces, cgroups, images & layers, a Dockerfile, pull policies | 4 |
| 2 | [Architecture](book/ch02-architecture.md) 🏛 | control plane & nodes, etcd by hand, the raw API, reconciliation, static pods | 5 |
| 3 | [The API & kubectl](book/ch03-api-and-kubectl.md) | GVK, jsonpath, selectors, finalizers, server-side apply & field managers | 5 |
| 4 | [Pods](book/ch04-pods.md) | multi-container, init & native sidecars, probes, QoS, OOMKilled | 7 |
| 5 | [Deployments](book/ch05-deployments.md) ✍️ | writing Deployments, zero-downtime rollouts, rollback, graceful shutdown, blue/green, canary | 6 |
| 6 | [Other workloads](book/ch06-workloads.md) | DaemonSet, Job, indexed Job, CronJob, StatefulSet | 5 |
| 7 | [Services & networking](book/ch07-services-networking.md) | ClusterIP, NodePort, headless, DNS, kube-proxy's iptables, manual EndpointSlices | 7 |
| 8 | [Ingress & Gateway API](book/ch08-ingress-gateway.md) | host/path routing, rewrites, TLS, HTTPRoutes | 4 |
| 9 | [Configuration](book/ch09-configuration.md) | ConfigMaps, Secrets, live reload vs subPath, downward API | 5 |
| 10 | [Storage](book/ch10-storage.md) | emptyDir, PVCs, static PVs, storage classes, Postgres on a StatefulSet | 5 |
| 11 | [Scheduling](book/ch11-scheduling.md) | node selectors, (anti-)affinity, taints, topology spread, drain & PDBs | 5 |
| 12 | [Security](book/ch12-security.md) 🔒 | RBAC, in-cluster API access, Pod Security `restricted`, NetworkPolicies | 6 |
| 13 | [Observability & debugging](book/ch13-observability-debugging.md) 🔧 | 5 broken scenarios, ephemeral debug containers, `kubectl top` | 7 |
| 14 | [Autoscaling & resources](book/ch14-autoscaling-resources.md) | HPA under real load, LimitRange, ResourceQuota, right-sizing | 4 |
| 15 | [Packaging](book/ch15-packaging.md) | Kustomize bases/overlays/patches, writing a Helm chart | 4 |
| 16 | [Cluster internals](book/ch16-cluster-internals.md) 🏛 | PKI, users via the CSR API, etcd backup, repairing a broken kubelet, leases | 5 |
| 17 | [Extending Kubernetes](book/ch17-extending.md) 🧩 | CRDs, CEL admission policies, **your own operator** (pure reconcile → loop → in-cluster) | 5 |
| 18 | [Capstone: guestbook](book/ch18-capstone.md) | a production-grade app: Kustomize, TLS, HPA, PDB, restricted pods, network isolation, persistence | 1 |

🏛 = the architecture track (chapters 2 and 16 together take the cluster apart, from etcd keys
and static pods to certificates and the kubelet). ✍️ = the "write your own deployments" core
(chapters 4–6 and 9). 🧩 = extending the platform.

Rough pacing: chapters 0–7 are the foundation (a couple of weeks of evenings); 8–15 are what
you need to run real apps; 16–17 go deep; 18 is a weekend project.

## Repository layout

```text
kube-learn/
├── book/                 ← reading, one Markdown file per chapter
├── exercises/            ← YOUR working copy (one directory per exercise)
│   └── ch05-deployments/
│       └── 01-first-deployment/   ← README.md, *.yaml, check.py
├── solutions/            ← reference solutions (the source of truth for exercises/)
├── apps/kubeapp/         ← the demo app used everywhere (stdlib Python): probes, crash, CPU/mem load, config, Redis…
├── runner/               ← the `./course` tool (stdlib Python: read it!) and the check helpers (kube.py)
└── course                ← entry point
```

In `solutions/`, regions between `#>>` and `#<<` are what you had to write; lines starting with
`#|` show the initial stub, and `# HINT:` lines feed `./course hint`. `./course generate --force`
rebuilds `exercises/` from `solutions/` and **erases your work**; use `./course reset ID` for a
single exercise. `./course verify --solutions` checks every reference solution against the
cluster: it's how the course itself is tested.

## Tips

* Read `kubectl describe` to the end: the **Events** at the bottom usually say exactly what's
  wrong. `kubectl get events -n <ns> --sort-by=.lastTimestamp` for everything at once.
* `kubectl explain <kind>.<field>` is the API reference, offline and always matching your cluster.
* Start manifests with `kubectl create … --dry-run=client -o yaml`, and check them with
  `kubectl apply --dry-run=server -f`.
* Stuck for more than ~15 minutes? `./course hint ID`, then `check.py` (it says precisely what's
  expected). Still stuck? Read the solution, close it, and redo it the next day.
* The cluster is yours to break. `./course cluster delete && ./course cluster up` gives you a
  fresh one in minutes.
* Don't edit `check.py` files.
