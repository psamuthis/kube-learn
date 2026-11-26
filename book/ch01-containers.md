# Chapter 1 — Containers, the building block

> **Reading time:** ~40 min · **Exercises:** `exercises/ch01-containers/` (4)

Kubernetes doesn't run programs; it runs **containers**, and it gets them from **images**. Before
we look at the orchestrator, let's make sure the thing being orchestrated holds no mystery.

## 1.1 A container is a process

There is no "container" object in the Linux kernel. A container is an ordinary process (and its
children) started with three kinds of restriction:

| Mechanism | What it does | See it |
|---|---|---|
| **Namespaces** | give the process its own *view* of a global resource | `ls -l /proc/$$/ns` |
| **cgroups (v2)** | *limit and account* CPU, memory, I/O, PIDs | `cat /proc/$$/cgroup` |
| **Root filesystem** | `pivot_root` into the image's files (an overlay mount) | `findmnt` inside a container |
| (plus) capabilities, seccomp, AppArmor/SELinux | restrict *what syscalls/privileges* it may use | chapter 12 |

The namespaces, one per kind of global resource:

* `pid`: the process sees itself as PID 1 and can't see other processes.
* `net`: its own interfaces, IPs, routing table, iptables, ports. **In Kubernetes all containers
  of a pod share one net namespace**, which is why they can talk over `localhost`.
* `mnt`: its own mount table (and so its own root filesystem).
* `uts`: its own hostname (in K8s: the pod name).
* `ipc`, `user`, `cgroup`, `time`.

You can build a "container" with nothing but util-linux:

```console
$ sudo unshare --pid --fork --mount-proc --uts --net bash
# hostname box; ps aux        ← you're PID 1, alone, with no network but `lo`
```

And **cgroups** are a filesystem: a directory per group under `/sys/fs/cgroup`, files to set
limits (`memory.max`, `cpu.max`, `pids.max`) and read usage (`memory.current`, `cpu.stat`). When a
cgroup goes over `memory.max`, the kernel's OOM killer kills a process in it. That's the
`OOMKilled` you'll meet in chapter 4. `cpu.max` contains `"<quota> <period>"`: `25000 100000` means
25 ms of CPU every 100 ms, i.e. a quarter of a core. Exceeding it doesn't kill you; you're
**throttled**.

Kubernetes `resources.limits.memory: 64Mi` becomes `memory.max = 67108864`, and
`limits.cpu: 250m` becomes `cpu.max = 25000 100000`. Exercise 1.3 has you verify both from inside a pod.

## 1.2 Images: layers + config

An **OCI image** (Open Container Initiative, the standard Docker donated in 2015) is:

```text
image manifest (JSON) ──▶ config  (JSON: Entrypoint, Cmd, Env, User, WorkingDir, ExposedPorts, history)
                     └──▶ layers  (tar.gz files, each a filesystem *diff*)
```

Each layer is content-addressed by its SHA-256 **digest**. At run time the runtime stacks the layers
with **overlayfs** (read-only lower layers + one writable upper layer per container), so 50
containers from the same image share the files on disk. Writes go into the container's upper
layer and **disappear when the container is deleted**. That's why durable data needs volumes
(chapter 10).

Image **references**:

```text
registry.example.com:5000/team/app:1.4.2@sha256:9f86d0…
└────── registry ──────┘└ repository ┘└ tag ┘└───── digest (immutable) ─────┘
```

* No registry means Docker Hub (`docker.io`); no `library/`-style namespace means `library/`
  (so `nginx` is `docker.io/library/nginx:latest`).
* **Tags are mutable pointers**, digests aren't. Production manifests often pin digests.
* **Never use `:latest` in Kubernetes**: you can't tell which version is running, and it changes
  the default pull policy to `Always` (see 1.5).

## 1.3 Writing a good Dockerfile

```dockerfile
# syntax=docker/dockerfile:1
FROM python:3.13-alpine            # small base; pin the version
WORKDIR /app
COPY requirements.txt .            # copy what changes rarely first…
RUN pip install --no-cache-dir -r requirements.txt
COPY . .                           # …and what changes often last: better layer caching
USER 10001:10001                   # never run as root; a *numeric* UID so K8s can verify it
EXPOSE 8000                        # documentation only
ENTRYPOINT ["python", "app.py"]    # exec form (JSON array): your process is PID 1 and gets SIGTERM
```

Rules of thumb:

* **Every instruction is a layer**, and layers are cached by their inputs. Order them from the
  least to the most frequently changing.
* **Multi-stage builds** for compiled languages: build in a fat image, then
  `COPY --from=build /out/app /app` into a minimal one (`gcr.io/distroless/static`, `scratch`). A
  Rust binary in `scratch` is a ~5 MB image.
* **Exec form** for `ENTRYPOINT`/`CMD`. Shell form (`ENTRYPOINT python app.py`) runs `/bin/sh -c`,
  which doesn't forward SIGTERM, so your app gets SIGKILLed 30 s later on every rollout.
* `ENTRYPOINT` + `CMD` are what Kubernetes calls **`command`** + **`args`**. A pod spec can
  override either.
* Don't bake config or secrets into images: inject them at run time (chapter 9).

## 1.4 Runtimes: who actually starts the process

```text
kubelet ──CRI (gRPC)──▶ containerd ──▶ containerd-shim ──▶ runc ──▶ your process
                          (pulls images,     (one per pod,      (sets up namespaces +
                           manages snapshots) keeps stdio)      cgroups, exec()s, exits)
```

* **runc** is the low-level OCI runtime: given a rootfs + `config.json`, it creates the container
  and exits.
* **containerd** (or **CRI-O**) is the high-level runtime: images, snapshots, lifecycle. It
  implements the **Container Runtime Interface** that the kubelet speaks.
* **Docker** is a developer tool built *on* containerd. Kubernetes stopped talking to Docker
  directly in 1.24, but images built by Docker are standard OCI images and run everywhere.
* `crictl` is the CRI command-line client, the `docker ps` of a Kubernetes node. Your lab nodes
  run containerd: try `minikube -p kube-learn ssh -- sudo crictl ps`.

Alternatives plug in at the bottom: **gVisor** (`runsc`, a user-space kernel) and **Kata
Containers** (each pod in a micro-VM) give stronger isolation behind the same API, selected with a
`RuntimeClass`.

## 1.5 How images get to a node

When a pod lands on a node, the kubelet asks the runtime for the image, following
`imagePullPolicy`:

| Policy | Behaviour | Default when… |
|---|---|---|
| `IfNotPresent` | pull only if the node doesn't have it | the tag isn't `:latest` |
| `Always` | check the registry every start (cheap if unchanged: just the manifest) | the tag is `:latest` or missing |
| `Never` | use the local image or fail with `ErrImageNeverPull` | never the default |

In this course, `kubeapp` isn't on any registry: `./course cluster images` builds it with Docker on
your machine and **loads** it into every node's containerd (`minikube image load`). So pods must
use `IfNotPresent` (the default for `kubeapp:1.0`) or `Never`. Set `Always` and the kubelet will
try `docker.io/library/kubeapp:1.0`, fail, and you get `ErrImagePull`, then `ImagePullBackOff`
(retries with exponential back-off up to 5 minutes). Exercise 1.4 is about exactly this.

Private registries need credentials: a `kubernetes.io/dockerconfigjson` Secret referenced by
`imagePullSecrets` in the pod (or attached to its ServiceAccount).

## 1.6 The course's demo app: kubeapp

`apps/kubeapp/app.py` is a ~300-line stdlib Python HTTP server we'll deploy over and over. It has
endpoints to *provoke* Kubernetes behaviour:

| Endpoint | Use |
|---|---|
| `/` | JSON with `version`, `hostname` (= pod name), `message`, `color` |
| `/healthz`, `/break` | liveness probe target; `/break` makes it fail (chapter 4) |
| `/ready`, `/toggle-ready` | readiness probe; `READY_DELAY` env simulates slow start |
| `/crash` | exits with status 1 (CrashLoopBackOff) |
| `/cpu?ms=`, `/mem?mb=` | burn CPU / hold memory (throttling, OOMKill, autoscaling) |
| `/env`, `/config` | show environment / files under `CONFIG_DIR` (chapter 9) |
| `/hits`, `/guestbook` | state in Redis (`REDIS_HOST`) or on disk (`DATA_DIR`) (chapters 10, 18) |

Two versions are loaded on every node: `kubeapp:1.0` (blue) and `kubeapp:2.0` (green), so we can do
rollouts. It runs as UID 10001 and handles SIGTERM gracefully (`SHUTDOWN_DELAY`).

## Exercises

| # | Name | What you practise |
|---|---|---|
| 1.1 | `dockerfile` | write a Dockerfile (small, non-root, exec form) and run it as a pod |
| 1.2 | `layers` | inspect an image's config and layers |
| 1.3 | `namespaces-cgroups` | see PID/UTS namespaces and cgroup limits from inside a pod, find the process on the node |
| 1.4 | `image-refs` | fix broken image references and pull policies |
