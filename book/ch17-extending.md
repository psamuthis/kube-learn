# Chapter 17 — Extending Kubernetes: CRDs, admission policies, operators

> **Reading time:** ~60 min · **Exercises:** `exercises/ch17-extending/` (5)

Chapter 2 said Kubernetes is a database of desired state plus control loops. This chapter adds
your own **types** to that database (CustomResourceDefinitions), your own **rules** at its door
(admission policies), and your own **loop** (a controller). Together, a CRD and its controller
are an **operator**: operational knowledge ("how to run a Redis cluster") encoded as software.

## 17.1 CustomResourceDefinitions

A CRD teaches the API server a new kind. From then on it's a first-class resource: REST
endpoints, kubectl support, RBAC, watch, `kubectl explain`, and storage in etcd.

```yaml
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: keyvaluestores.kube-learn.dev        # <plural>.<group>
spec:
  group: kube-learn.dev
  scope: Namespaced                          # or Cluster
  names:
    kind: KeyValueStore
    plural: keyvaluestores
    singular: keyvaluestore
    shortNames: [kvs]
  versions:
    - name: v1
      served: true
      storage: true                          # exactly one version is the storage version
      subresources:
        status: {}                           # /status: spec and status updated separately
        scale:                               # /scale: makes `kubectl scale` and HPAs work
          specReplicasPath: .spec.replicas
          statusReplicasPath: .status.readyReplicas
      additionalPrinterColumns:
        - {name: Replicas, type: integer, jsonPath: .spec.replicas}
        - {name: Phase, type: string, jsonPath: .status.phase}
        - {name: Age, type: date, jsonPath: .metadata.creationTimestamp}
      schema:
        openAPIV3Schema:                     # structural schema: every field typed
          type: object
          required: [spec]
          properties:
            spec:
              type: object
              required: [version]
              properties:
                replicas: {type: integer, minimum: 1, maximum: 5, default: 1}
                version:  {type: string, enum: ["7.4", "8.0"]}
              x-kubernetes-validations:      # CEL rules, evaluated by the API server
                - rule: "self.replicas == 1 || self.version != '7.4'"
                  message: "7.4 only supports a single replica"   # (just an example rule)
            status:
              type: object
              properties:
                phase: {type: string}
                readyReplicas: {type: integer}
                observedGeneration: {type: integer}
```

* The schema is enforced: unknown fields are **pruned** (or rejected with
  `kubectl --validate=strict`), types and bounds are checked, and `default`s are filled in.
* **CEL** (Common Expression Language) rules in `x-kubernetes-validations` cover cross-field
  checks, and with `oldSelf`, transition rules ("this field is immutable":
  `self == oldSelf`).
* New versions (`v2`) can be served next to `v1`. Converting between them needs a **conversion
  webhook** if the shapes differ.
* A CRD without a controller is just structured storage, and that alone is sometimes useful.

## 17.2 Admission control

Between authorization and storage, every write passes through **admission**: mutating first, then
validating (chapter 2.2). Built-in plugins (LimitRanger, ResourceQuota, PodSecurity,
ServiceAccount…) run there, and so can your own rules:

| Mechanism | How | Pros / cons |
|---|---|---|
| **ValidatingAdmissionPolicy** (GA 1.30) | CEL expressions in an API object | in-process, fast, no extra service to run; limited to what CEL can see |
| **MutatingAdmissionPolicy** (beta) | CEL that produces patches | same, for defaults/injection |
| **Admission webhooks** | the API server calls your HTTPS service | anything goes; but if the webhook is down, writes fail (`failurePolicy`) |
| Kyverno, OPA Gatekeeper | policy engines built on webhooks | rich policy libraries, reporting |

```yaml
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingAdmissionPolicy
metadata: {name: deployments-need-a-team}
spec:
  failurePolicy: Fail
  matchConstraints:
    resourceRules:
      - apiGroups: [apps]
        apiVersions: [v1]
        operations: [CREATE, UPDATE]
        resources: [deployments]
  validations:
    - expression: "has(object.metadata.labels) && 'team' in object.metadata.labels"
      message: "every Deployment needs a `team` label"
    - expression: "object.spec.replicas <= 5"
      messageExpression: "'too many replicas: ' + string(object.spec.replicas)"
---
apiVersion: admissionregistration.k8s.io/v1
kind: ValidatingAdmissionPolicyBinding
metadata: {name: deployments-need-a-team}
spec:
  policyName: deployments-need-a-team
  validationActions: [Deny]                 # or [Warn], [Audit]: roll out policies gently
  matchResources:
    namespaceSelector:
      matchLabels: {environment: prod}
```

CEL sees `object`, `oldObject`, `request` (user, operation), `params` (an optional parameter
object), `namespaceObject`. Test policies with `kubectl apply --dry-run=server`.

## 17.3 The controller pattern, in detail

```text
            ┌─────────────── informer ────────────────┐
 API ──list+watch──▶ local cache (indexed)  ──events──▶ workqueue (deduplicated keys "ns/name")
                                                            │
                                         worker(s): reconcile(key)
                                            1. read desired state (the CR) from the cache
                                            2. read observed state (children, external world)
                                            3. compute and apply the difference (idempotently)
                                            4. write status (conditions, observedGeneration)
                                            5. on error: requeue with back-off
```

Rules of good controllers:

* **Level-triggered**: reconcile from the current state of the world, never from the event
  ("an update happened"). Re-run periodically anyway ("resync").
* **Idempotent**: running reconcile twice changes nothing the second time. **Server-side apply**
  makes this easy: "make it look like this", with a field manager name.
* **Owner references** on everything you create (`controller: true`): the garbage collector
  deletes children with the parent, and you can watch children and map them back to their owner.
* **Finalizers** only for cleanup *outside* the cluster (a cloud resource, a DNS record). Remove
  them when cleanup is done, or deletions hang forever (chapter 3.7).
* **Status reports what was observed**: `observedGeneration`, conditions (`Ready`, `Progressing`,
  `Degraded`), never a copy of spec.
* **Leader election** if more than one replica runs.
* **Least-privilege RBAC**: exactly the verbs on exactly the resources you manage.

## 17.4 Frameworks

You'll write one in plain Python (stdlib, raw HTTP) to see every moving part. In practice:

* **Go: controller-runtime** with **kubebuilder** or **Operator SDK** scaffolding. Used by most of
  the ecosystem (cert-manager, Argo, Crossplane, every big operator). CRD YAML is generated from Go
  structs with markers.
* **Rust: kube-rs** (`kube::runtime::Controller`). You know this language now:

  ```rust
  #[derive(CustomResource, Deserialize, Serialize, Clone, Debug, JsonSchema)]
  #[kube(group = "kube-learn.dev", version = "v1", kind = "KeyValueStore", namespaced, status = "KvStatus")]
  struct KvSpec { replicas: i32, version: String }

  async fn reconcile(kv: Arc<KeyValueStore>, ctx: Arc<Ctx>) -> Result<Action, Error> {
      let sts = desired_statefulset(&kv);                       // pure, testable
      let api: Api<StatefulSet> = Api::namespaced(ctx.client.clone(), &kv.namespace().unwrap());
      api.patch(&sts.name_any(), &PatchParams::apply("kv-operator").force(), &Patch::Apply(&sts)).await?;
      Ok(Action::requeue(Duration::from_secs(300)))
  }
  // Controller::new(kvs, watcher::Config::default()).owns(statefulsets, …).run(reconcile, error_policy, ctx)
  ```
* **Python: kopf**; **Java: Java Operator SDK**; also Metacontroller (write only the reconcile
  function, as a webhook).

Before writing an operator, check whether one already exists (OperatorHub, Artifact Hub), and
whether a Helm chart would do. Operators shine when the software needs *ongoing* decisions:
failover, backups, upgrades with ordering, rebalancing.

## 17.5 The exercise operator: KeyValueStore

Over exercises 17.3–17.5 you'll build `kv-operator`, which turns

```yaml
apiVersion: kube-learn.dev/v1
kind: KeyValueStore
metadata: {name: cache}
spec: {replicas: 2, version: "7.4"}
```

into a StatefulSet of `redis:7.4-alpine` plus a Service named `cache`, reports `status.phase`
and `status.readyReplicas`, follows changes, and lets the garbage collector clean up when the
KeyValueStore is deleted:

1. **17.3**: the *pure* part, `desired_statefulset`, `desired_service`, `reconcile`, `status`,
   tested like a library (no cluster).
2. **17.4**: the *loop*. A small stdlib API client (given) watches KeyValueStores, calls your
   `reconcile`, applies the result with server-side apply and patches status. It runs on your
   machine through `kubectl proxy`.
3. **17.5**: *packaging*. A Dockerfile, a ServiceAccount, a least-privilege ClusterRole, and a
   Deployment, so that it runs in the cluster with its in-cluster token.

## Exercises

| # | Name | What you practise |
|---|---|---|
| 17.1 | `crd` | a CRD with schema validation, defaults, printer columns and a short name |
| 17.2 | `admission-policy` | a ValidatingAdmissionPolicy in CEL, scoped by namespace |
| 17.3 | `reconcile` | the pure heart of a controller, test-driven |
| 17.4 | `operator` | a watch-based operator using server-side apply and the status subresource |
| 17.5 | `operator-in-cluster` | run the operator in the cluster with least-privilege RBAC |
