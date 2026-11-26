# Exercise 17.2 — An admission policy in CEL

Write `policy.yaml`:

* a `ValidatingAdmissionPolicy` **`team-and-size-ex172`** that, on CREATE and UPDATE of
  `apps/v1` Deployments, requires
  1. a label `team` (message: `every Deployment needs a team label`);
  2. at most 5 replicas (message built with `messageExpression`, containing the actual number);
* a `ValidatingAdmissionPolicyBinding` **`team-and-size-ex172`** that **denies** violations, but
  only in the namespace `ex-17-2` (select it with `namespaceSelector` on the automatic label
  `kubernetes.io/metadata.name`).

Test with `kubectl apply --dry-run=server`. Policies are cluster-scoped: `./course clean 17.2`
deletes them.
