# Exercise 17.5 — Ship the operator

Run kv-operator **inside** the cluster, with the least privilege it needs.

1. `Dockerfile`: an image `kv-operator:dev` with `kv_operator.py` (from 17.4) and `reconcile.py`
   (from 17.3) in `/app`, running as a non-root numeric user, with the entrypoint
   `python /app/kv_operator.py`. The checker builds it from a temporary context containing your
   Dockerfile plus those two files.
2. `rbac.yaml`: a ServiceAccount `kv-operator`, a **Role** (the operator only watches its own
   namespace) granting exactly:
   * `get`, `list`, `watch` on `keyvaluestores` (group `kube-learn.dev`), and `patch` on
     `keyvaluestores/status`;
   * `get`, `create`, `patch` on `statefulsets` (`apps`) and `services` (core);

   and a RoleBinding.
3. `deployment.yaml`: a Deployment `kv-operator`, 1 replica, image `kv-operator:dev`
   (`imagePullPolicy: Never`), the ServiceAccount, and the `restricted` securityContext from
   chapter 12. The operator finds its namespace in the token mount (`--namespace` defaults to it).

The checker installs the CRD, builds and loads the image, waits for the operator, creates a
KeyValueStore, and checks the RBAC: the operator's ServiceAccount must **not** be able to
delete pods or read Secrets.
