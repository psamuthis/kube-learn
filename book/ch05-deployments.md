# Chapter 5 — Deployments: writing your own

> **Reading time:** ~50 min · **Exercises:** `exercises/ch05-deployments/` (6)

You'll write more Deployments than any other object. This chapter goes from the ReplicaSet
underneath to zero-downtime rollouts, rollbacks and release strategies, and ends with a
checklist for a production-grade Deployment.

## 5.1 ReplicaSet: "keep N of these running"

A **ReplicaSet** has three things: a **selector**, a **replica count**, and a **pod template**.
Its controller counts the pods that match the selector and are owned by it, then creates from
the template or deletes until the count is right. That's all it does.

```yaml
apiVersion: apps/v1
kind: ReplicaSet
metadata: {name: web}
spec:
  replicas: 3
  selector: {matchLabels: {app: web}}
  template:                               # a Pod, minus apiVersion/kind
    metadata: {labels: {app: web}}        # MUST match the selector
    spec:
      containers: [{name: app, image: kubeapp:1.0}]
```

What a ReplicaSet *doesn't* do: change existing pods when you change the template. Edit the
image and nothing happens to the running pods, because their count is still right. Updating is
the Deployment's job. You almost never create ReplicaSets by hand.

## 5.2 Deployment = ReplicaSets over time

A **Deployment** manages ReplicaSets: one per version of the pod template. When you change the
template, it creates a new ReplicaSet and shifts replicas from the old one to the new one,
gradually, while watching readiness:

```text
 kubectl apply (image 1.0 → 2.0)
 Deployment web
   ├── ReplicaSet web-5d4f8 (template hash of 1.0)   3 → 2 → 1 → 0   (kept for rollback)
   └── ReplicaSet web-7c9b1 (template hash of 2.0)   0 → 1 → 2 → 3
```

* The ReplicaSet name suffix is the **pod-template-hash**, also added as a label on its pods so
  the two ReplicaSets' selectors don't overlap.
* Only changes to `spec.template` trigger a rollout. Changing `replicas` just scales the
  current ReplicaSet.
* Old ReplicaSets are kept (scaled to 0) up to `revisionHistoryLimit` (default 10). They *are*
  the rollback history.

## 5.3 Anatomy of a good Deployment

Here's a Deployment you could ship. Every field is there for a reason:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web
  labels: {app.kubernetes.io/name: web}
spec:
  replicas: 3
  revisionHistoryLimit: 5
  selector:
    matchLabels: {app.kubernetes.io/name: web}        # immutable after creation!
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxSurge: 1                 # at most replicas+1 pods during a rollout
      maxUnavailable: 0           # never fewer than `replicas` ready pods
  minReadySeconds: 5              # a new pod must stay Ready 5 s to count as available
  progressDeadlineSeconds: 120    # mark the rollout failed if it hasn't progressed in 2 min
  template:
    metadata:
      labels: {app.kubernetes.io/name: web}
    spec:
      terminationGracePeriodSeconds: 30
      containers:
        - name: app
          image: kubeapp:1.0                           # a pinned tag (or digest), never :latest
          ports: [{name: http, containerPort: 8080}]
          env:
            - {name: SHUTDOWN_DELAY, value: "5"}       # keep serving briefly after SIGTERM
          resources:
            requests: {cpu: 50m, memory: 64Mi}
            limits: {memory: 128Mi}
          readinessProbe:
            httpGet: {path: /ready, port: http}
            periodSeconds: 2
          livenessProbe:
            httpGet: {path: /healthz, port: http}
            periodSeconds: 10
          securityContext:                             # chapter 12
            runAsNonRoot: true
            allowPrivilegeEscalation: false
```

Things to note:

* **`selector` is immutable**: choose labels you won't need to change. The template's labels must
  be a superset of the selector.
* **Readiness probes are what make rollouts safe.** Without one, a pod counts as ready the moment
  its process starts, and the Deployment happily replaces all your working pods with broken ones.
* `kubectl create deployment web --image=kubeapp:1.0 --replicas=3 --port=8080 --dry-run=client -o yaml`
  generates a skeleton to start from.

## 5.4 Rolling updates

The rolling update is a loop: scale the new ReplicaSet up as far as `maxSurge` allows, wait for
new pods to become **available** (Ready for `minReadySeconds`), scale the old one down as far as
`maxUnavailable` allows, and repeat.

| Setting | Effect |
|---|---|
| `maxSurge: 25%, maxUnavailable: 25%` (default) | fast, some capacity loss |
| `maxSurge: 1, maxUnavailable: 0` | the classic zero-downtime choice: one extra pod at a time |
| `maxSurge: 100%, maxUnavailable: 0` | double the pods, then switch: fastest safe rollout, needs room |
| `type: Recreate` | kill all old pods, then start new ones: downtime, but never two versions at once (needed when versions can't coexist, like an exclusive DB schema lock or a single RWO volume) |

Driving rollouts:

```console
$ kubectl set image deploy/web app=kubeapp:2.0        # or edit the YAML and apply (better)
$ kubectl rollout status deploy/web                   # blocks until done or failed
$ kubectl rollout history deploy/web                  # revisions
$ kubectl rollout history deploy/web --revision=3     # the template of one revision
$ kubectl rollout undo deploy/web                     # back to the previous revision
$ kubectl rollout undo deploy/web --to-revision=2
$ kubectl rollout pause / resume deploy/web           # batch several changes into one rollout
$ kubectl rollout restart deploy/web                  # new pods, same spec (adds an annotation)
$ kubectl annotate deploy/web kubernetes.io/change-cause="bump to 2.0"   # shows in history
```

**Failed rollouts don't roll back by themselves.** If new pods never become ready (bad image,
crash, failing probe), the Deployment stops progressing. With `maxUnavailable: 0`, the old pods
keep serving. After `progressDeadlineSeconds`, the `Progressing` condition turns `False` with
reason `ProgressDeadlineExceeded`, which is your CI's signal to run `rollout undo`.

Remember that after `rollout undo` the live object no longer matches your YAML in git. In a
GitOps workflow you revert the commit instead.

## 5.5 Zero downtime, for real

A readiness probe plus `maxUnavailable: 0` covers *start-up*. *Shutdown* has a race, as
section 4.7 explained: when a pod is deleted, endpoint removal and SIGTERM happen in parallel,
so for a second or two kube-proxy on some nodes still sends new connections to a pod that's
shutting down. The fixes:

1. The app keeps serving for a few seconds after SIGTERM, but fails readiness
   (kubeapp: `SHUTDOWN_DELAY`), **or**
2. a `preStop` hook delays SIGTERM: `lifecycle: {preStop: {sleep: {seconds: 5}}}` (the built-in
   `sleep` action needs no shell in the image; older clusters use `exec: {command: [sleep, "5"]}`);
3. and `terminationGracePeriodSeconds` larger than preStop + drain time.

## 5.6 Release strategies built from Deployments and labels

Kubernetes has no "blue/green" or "canary" object; you build them from Deployments and the label
selectors of Services (chapter 7 covers Services; for now, a Service sends traffic to every
Ready pod matching its selector).

**Blue/green:** two complete Deployments, and one Service whose selector picks one of them.

```yaml
# deployment web-blue:  labels {app: web, version: blue}   image 1.0
# deployment web-green: labels {app: web, version: green}  image 2.0
kind: Service
spec:
  selector: {app: web, version: blue}     # flip to green: an instant, atomic switch; flip back to roll back
```

**Canary:** the Service selects only `app: web`, and two Deployments both carry that label:
`web-stable` with 9 replicas and `web-canary` with 1. About 10% of the traffic goes to the canary
(per connection, by pod count). Watch your metrics, then roll the new version into stable.

Precise percentages, header-based routing and automatic analysis need an ingress controller,
Gateway API, a service mesh, or a tool like Argo Rollouts or Flagger.

## 5.7 Deployments and the reconcile loop

Things you'll now recognise as consequences of chapter 2:

* `kubectl scale deploy/web --replicas=5` works until the next `kubectl apply` of a file that
  says `replicas: 3`. Whoever writes last wins. Leave `replicas` out of the file when an HPA
  owns it (chapter 14).
* Deleting a pod of a Deployment just gets it replaced. Deleting the ReplicaSet gets *it*
  replaced. To get rid of the whole thing, delete the Deployment.
* `kubectl get deploy` columns: `READY` (ready/desired), `UP-TO-DATE` (pods on the latest
  template), `AVAILABLE` (ready for minReadySeconds).

## Exercises

| # | Name | What you practise |
|---|---|---|
| 5.1 | `first-deployment` | a production-grade Deployment from scratch |
| 5.2 | `rolling-update` | surge/unavailable, minReadySeconds, rolling to 2.0 with zero downtime |
| 5.3 | `rollback` | recover from a broken rollout with `rollout undo` |
| 5.4 | `graceful-shutdown` | preStop, grace period, SIGTERM handling |
| 5.5 | `blue-green` | two Deployments and a selector switch |
| 5.6 | `canary` | weighted traffic by replica count |
