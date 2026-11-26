# Chapter 3 — The API and kubectl, seriously

> **Reading time:** ~45 min · **Exercises:** `exercises/ch03-api-and-kubectl/` (5)

Kubernetes *is* its API. This chapter is about the shape every object shares, and about using
kubectl as a precise query tool rather than as a magic incantation.

## 3.1 Groups, versions, kinds, resources

```text
apiVersion: apps/v1        ← GROUP/VERSION   ("v1" alone = the core group, which has no name)
kind: Deployment           ← KIND            (the type, CamelCase, singular)
```

* **Group**: a family of related types. Core (`""`: Pod, Service, ConfigMap, Secret, Node,
  Namespace…), `apps` (Deployment, StatefulSet, DaemonSet, ReplicaSet), `batch` (Job,
  CronJob), `networking.k8s.io` (Ingress, NetworkPolicy), `rbac.authorization.k8s.io`,
  `autoscaling`, `storage.k8s.io`, and every CRD's own group (`cert-manager.io`…).
* **Version**: `v1alpha1` → `v1beta1` → `v1`. A group can serve several versions of the same kind
  at once; the API server converts between them, and stores one.
* **Kind** names the type; **resource** names the URL collection (lower-case plural):
  kind `Deployment` ↔ resource `deployments` ↔ `/apis/apps/v1/namespaces/x/deployments`.
  Together: **GVK** (group-version-kind) and **GVR** (group-version-resource).

```console
$ kubectl api-resources                    # NAME, SHORTNAMES, APIVERSION, NAMESPACED, KIND
$ kubectl api-resources --namespaced=false # cluster-scoped: nodes, namespaces, PVs, ClusterRoles, CRDs…
$ kubectl api-versions                     # every group/version served
$ kubectl explain deployment.spec.strategy # the schema, with docs: your offline API reference
$ kubectl explain pod.spec.containers --recursive | less
```

Short names save typing: `po`, `svc`, `deploy`, `rs`, `ds`, `sts`, `cm`, `ns`, `no`, `pvc`,
`pv`, `sa`, `ing`, `netpol`, `hpa`, `pdb`, `crd`.

## 3.2 Anatomy of an object

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: web                       # unique per (kind, namespace)
  namespace: shop                 # absent for cluster-scoped kinds
  uid: 3f1c…                      # unique forever; a re-created "web" gets a new uid
  resourceVersion: "48211"        # optimistic concurrency token (chapter 2)
  generation: 4                   # bumped on every spec change
  creationTimestamp: "…"
  deletionTimestamp: "…"          # set when deletion was requested but finalizers remain
  labels: {app: web, tier: front} # identifying, selectable
  annotations: {…}                # non-identifying metadata, arbitrary size-ish
  ownerReferences: [{kind: …, name: …, uid: …, controller: true}]
  finalizers: [example.com/cleanup]
  managedFields: […]              # who set which field (server-side apply)
spec: {…}                         # desired state (yours)
status:                           # observed state (the controllers')
  observedGeneration: 4           # "I have acted on spec generation 4"
  conditions:
    - type: Available
      status: "True"
      reason: MinimumReplicasAvailable
      lastTransitionTime: "…"
```

**Conditions** are the standard way to report status: a list of `{type, status: True|False|Unknown,
reason, message}`. `kubectl wait --for=condition=Available deploy/web` waits on them.
`observedGeneration == generation` means the controller has seen your latest change.

## 3.3 Namespaces

A namespace is a **name scope** and a **policy boundary** (RBAC, quotas, network policies,
pod security levels attach to namespaces). It is *not* a network or security boundary on its own:
pods in different namespaces can talk freely unless a NetworkPolicy says otherwise.

* Built-in: `default`, `kube-system` (cluster components), `kube-public`, `kube-node-lease`
  (one Lease per node: the heartbeats).
* DNS names include the namespace: `web.shop.svc.cluster.local`.
* Deleting a namespace deletes **everything in it** (the namespace controller loops over every
  namespaced resource type). It can hang in `Terminating` if some object has a finalizer that
  nothing removes.

## 3.4 Labels, selectors and annotations

**Labels** are the *only* way Kubernetes groups objects. A Deployment finds its pods, a Service
finds its endpoints, a NetworkPolicy finds its targets, all through **label selectors**. There
are no folders, no hard links.

```console
$ kubectl get pods -l app=web                     # equality
$ kubectl get pods -l 'app=web,tier!=cache'       # AND; != also matches pods without the key
$ kubectl get pods -l 'env in (prod,staging)'     # set-based
$ kubectl get pods -l 'env notin (dev)'
$ kubectl get pods -l 'release'                   # key exists
$ kubectl get pods -l '!release'                  # key doesn't exist
$ kubectl get pods -L app,tier                    # show labels as columns
$ kubectl label pod x tier=front --overwrite      # set / change
$ kubectl label pod x tier-                       # remove
```

In YAML, selectors come in two forms:

```yaml
selector:                       # Service: equality only (map)
  app: web
selector:                       # Deployment, Job, NetworkPolicy, …: LabelSelector
  matchLabels: {app: web}
  matchExpressions:
    - {key: env, operator: In, values: [prod, staging]}   # In, NotIn, Exists, DoesNotExist
```

Recommended label keys (`app.kubernetes.io/name`, `/instance`, `/version`, `/component`,
`/part-of`, `/managed-by`) let tools understand your objects. Prefixed keys (`example.com/x`) are
yours; `kubernetes.io/` and `k8s.io/` prefixes are reserved.

**Annotations** have the same `key: value` shape, but you can't select on them. They hold
metadata for tools and humans: build info, `kubectl.kubernetes.io/last-applied-configuration`,
ingress controller options, `deployment.kubernetes.io/revision`, change causes…

**Field selectors** filter on a few built-in fields: `kubectl get pods
--field-selector status.phase=Running,spec.nodeName=kube-learn-m02`.

## 3.5 Output formats: kubectl as a query language

```console
$ kubectl get pods -o wide
$ kubectl get pod web-1 -o yaml                    # everything, including status
$ kubectl get pods -o name                         # pod/web-1 …: good for scripting
$ kubectl get pods -o jsonpath='{.items[*].metadata.name}'
$ kubectl get pods -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.nodeName}{"\n"}{end}'
$ kubectl get pods -o jsonpath='{.items[?(@.status.phase=="Running")].metadata.name}'   # filter
$ kubectl get pods -o custom-columns=NAME:.metadata.name,IMAGE:.spec.containers[0].image
$ kubectl get pods --sort-by=.metadata.creationTimestamp
$ kubectl get pods -o json | jq '.items[] | select(.spec.nodeName=="kube-learn") | .metadata.name'
```

JSONPath cheat-sheet: `.a.b` child, `[0]` index, `[*]` all, `[?(@.x=="y")]` filter,
`{range …}{…}{end}` loop, `{"\n"}` literal. Keys containing dots must be escaped:
`{.metadata.labels.app\.kubernetes\.io/name}`.

## 3.6 Three ways to change things

| | Imperative command | Imperative config | **Declarative** |
|---|---|---|---|
| Example | `kubectl create deploy web --image=…` | `kubectl replace -f web.yaml` | `kubectl apply -f dir/` |
| Source of truth | your shell history | the file (whole object) | the files (fields you set) |
| Idempotent | no | yes | yes |
| Use for | experiments | rarely | **everything real** |

Also handy: `kubectl edit` (opens the live object in `$EDITOR`), `kubectl patch` (merge,
JSON-patch or strategic-merge patch from the command line), `kubectl set image`,
`kubectl scale`, `kubectl diff -f` (what would apply change?).

### Client-side vs server-side apply

Classic `kubectl apply` is **client-side**: kubectl stores your last applied file in the
`last-applied-configuration` annotation and computes a three-way diff (last applied, live, new
file) to decide what to change, and in particular which fields to *remove*.

**Server-side apply** (`kubectl apply --server-side`) moves that logic into the API server and
records **field ownership** in `managedFields`: each field has a **manager** (`kubectl`, `helm`,
`kube-controller-manager`, your operator…). If you apply a field someone else owns with a
different value, you get a **conflict** instead of silently overwriting it. Use `--force-conflicts`
to take ownership deliberately. Applying a file only claims the fields *in that file*, which
lets several actors (a team, an HPA, an operator) co-own one object. Exercise 3.5.

## 3.7 Lifecycle helpers: ownerReferences and finalizers

**ownerReferences** link a dependent to its owner. When the owner is deleted, the **garbage
collector** deletes the dependents:

* `--cascade=background` (default): delete the owner now, dependents shortly after;
* `--cascade=foreground`: the owner gets a `foregroundDeletion` finalizer and waits until all
  dependents are gone;
* `--cascade=orphan`: leave the dependents (they lose their ownerReference).

**Finalizers** are strings in `metadata.finalizers`. Deleting an object that has any only *sets
`deletionTimestamp`*; the object stays (read-only, apart from finalizers) until something
removes every finalizer. That "something" is a controller doing cleanup (a cloud load balancer
being released, a PV being wiped). If that controller is gone, the object is stuck forever, and
you remove the finalizer by hand:

```console
$ kubectl patch configmap stuck --type=merge -p '{"metadata":{"finalizers":null}}'
```

Do this only when you understand what cleanup you're skipping.

## 3.8 Debugging kubectl itself

* `-v=6` shows the URLs, `-v=8` the bodies, `-v=9` everything (curl commands!).
* `kubectl get --raw /api/v1/namespaces/default/pods | head` does a raw GET without a proxy.
* `kubectl auth whoami` shows who the API server thinks you are.
* `kubectl get --raw /readyz?verbose` reports the API server's own health checks.

## Exercises

| # | Name | What you practise |
|---|---|---|
| 3.1 | `explain` | `api-resources`, `explain`, groups/versions/short names |
| 3.2 | `jsonpath` | precise queries with jsonpath, custom-columns, sorting |
| 3.3 | `selectors` | equality and set-based label selectors |
| 3.4 | `finalizers` | delete an object that's held by a finalizer, and understand why it was stuck |
| 3.5 | `server-side-apply` | field managers, conflicts, co-owning one object |
