# Exercise 12.2 — ClusterRoles

The ServiceAccount `ops` (in `ex-12-2`) needs:

1. to **read nodes** (get, list, watch). Nodes are cluster-scoped, so this needs a ClusterRole
   `node-viewer-ex122` and a ClusterRoleBinding `node-viewer-ex122`;
2. to **edit workloads in its own namespace only**: bind the *built-in* ClusterRole `edit`
   with a **RoleBinding** `ops-edit` in `ex-12-2`.

Write both in `rbac.yaml` (plus the ServiceAccount). Cluster-scoped objects ignore the namespace;
`./course clean 12.2` deletes them.
