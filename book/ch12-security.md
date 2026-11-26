# Chapter 12 — Security: identity, RBAC, pod security, network policy

> **Reading time:** ~60 min · **Exercises:** `exercises/ch12-security/` (6)

Kubernetes security has four layers, and this chapter covers all of them:

1. **Who are you?** Authentication: users, ServiceAccounts, tokens.
2. **What may you do through the API?** Authorization: RBAC.
3. **What may your containers do on the node?** securityContext, Pod Security Standards.
4. **Who may talk to whom on the network?** NetworkPolicy.

## 12.1 Authentication: users and ServiceAccounts

Kubernetes has **no User objects**. A human "user" is whatever identity the API server can
verify:

* **client certificates** signed by the cluster CA: the user is the cert's CN, the groups are its
  O fields (your minikube kubeconfig has one, chapter 16);
* **OIDC tokens** from an identity provider (Google, Azure AD, Keycloak, Dex): the usual choice for
  people in real clusters;
* cloud IAM via webhook token authentication (EKS, GKE).

**ServiceAccounts** *are* objects: namespaced identities for **workloads**. Every namespace has a
`default` ServiceAccount, and every pod runs as one (`spec.serviceAccountName`). The kubelet mounts
a **short-lived, audience-bound, auto-rotated token** into the pod at
`/var/run/secrets/kubernetes.io/serviceaccount/token`, along with the CA and the namespace. The
pod's username is `system:serviceaccount:<ns>:<name>`.

```yaml
apiVersion: v1
kind: ServiceAccount
metadata: {name: lister}
automountServiceAccountToken: false     # good default: opt in per pod
---
spec:                                   # pod
  serviceAccountName: lister
  automountServiceAccountToken: true    # this pod needs the API
```

Most apps never talk to the Kubernetes API, so **don't mount a token** they don't need. A leaked
token is a foothold in the cluster.

```console
$ kubectl create token lister --duration=10m      # mint a token by hand (for testing)
$ kubectl auth whoami
```

## 12.2 Authorization: RBAC

RBAC is **allow-only** and **additive** (no deny rules). Four objects:

| | Namespaced | Cluster-wide |
|---|---|---|
| a set of permissions | **Role** | **ClusterRole** |
| who gets them | **RoleBinding** | **ClusterRoleBinding** |

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata: {name: pod-reader, namespace: shop}
rules:
  - apiGroups: [""]                       # "" = core group
    resources: [pods, pods/log]           # subresources are separate resources
    verbs: [get, list, watch]
  - apiGroups: [apps]
    resources: [deployments]
    resourceNames: [web]                  # optionally: only these objects
    verbs: [get, patch]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata: {name: lister-reads-pods, namespace: shop}
subjects:
  - {kind: ServiceAccount, name: lister, namespace: shop}
  - {kind: User, name: alice@example.com, apiGroup: rbac.authorization.k8s.io}
  - {kind: Group, name: team-shop, apiGroup: rbac.authorization.k8s.io}
roleRef: {kind: Role, name: pod-reader, apiGroup: rbac.authorization.k8s.io}   # immutable
```

* **Verbs**: `get`, `list`, `watch`, `create`, `update`, `patch`, `delete`, `deletecollection`,
  plus special ones (`impersonate`, `bind`, `escalate`, `use`). `kubectl exec` needs `create` on
  `pods/exec`.
* A **RoleBinding can reference a ClusterRole**: it grants that ClusterRole's rules *inside
  the binding's namespace only*. That's how you reuse the built-in roles `view`, `edit` and
  `admin` per namespace. `cluster-admin` is everything.
* **ClusterRoles** are needed for cluster-scoped resources (nodes, PVs, namespaces, CRDs) and for
  "in all namespaces".
* **Aggregated ClusterRoles** combine others by label (this is how CRDs add their permissions to
  `view`/`edit`).
* RBAC prevents **privilege escalation**: you can't grant permissions you don't have yourself
  (unless you have `escalate`/`bind`).

Test permissions without guessing:

```console
$ kubectl auth can-i list pods -n shop --as=system:serviceaccount:shop:lister
$ kubectl auth can-i --list -n shop --as=system:serviceaccount:shop:lister
$ kubectl auth can-i '*' '*' --all-namespaces            # am I cluster-admin?
```

**Dangerous permissions** (treat as admin-equivalent): `create pods` (can mount any Secret or
ServiceAccount of the namespace, and run privileged containers unless pod security forbids it),
`get secrets`, `create pods/exec`, `update` on roles/bindings, `impersonate`, `nodes/proxy`, and
anything with `*`.

## 12.3 securityContext: what a container may do on its node

Containers share the node's kernel, so the defaults matter:

```yaml
spec:
  securityContext:                        # pod level
    runAsNonRoot: true                    # the kubelet refuses to start a container running as UID 0
    runAsUser: 10001
    runAsGroup: 10001
    fsGroup: 10001                        # group ownership of mounted volumes
    seccompProfile: {type: RuntimeDefault}   # block ~50 dangerous syscalls
  containers:
    - name: app
      securityContext:                    # container level (overrides the pod level)
        allowPrivilegeEscalation: false   # no setuid gains (no_new_privs)
        readOnlyRootFilesystem: true      # write only to volumes (mount an emptyDir at /tmp)
        capabilities:
          drop: [ALL]                     # add back only what's needed, e.g. NET_BIND_SERVICE
        privileged: false                 # privileged = root on the node, basically
```

Also dangerous at pod level: `hostNetwork`, `hostPID`, `hostIPC`, `hostPath` volumes, `hostPort`.
Those are for node agents only.

## 12.4 Pod Security Standards and admission

Kubernetes defines three **Pod Security Standards**:

| Level | Allows | For |
|---|---|---|
| `privileged` | anything | system components (CNI, storage drivers) |
| `baseline` | no privileged, no host namespaces, no hostPath, limited capabilities | most apps, easy to meet |
| `restricted` | baseline + must run as non-root, drop ALL capabilities, no privilege escalation, seccomp RuntimeDefault | hardened apps: **the target** |

The built-in **Pod Security Admission** controller enforces them **per namespace**, through
labels:

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: shop
  labels:
    pod-security.kubernetes.io/enforce: restricted     # reject violating pods
    pod-security.kubernetes.io/warn: restricted        # warn kubectl users
    pod-security.kubernetes.io/audit: restricted       # annotate audit logs
```

Rejections happen at **pod creation**. For a Deployment, the Deployment is accepted, but its
ReplicaSet can't create pods: look at `kubectl describe rs` events ("violates PodSecurity
restricted:latest…"). For custom rules beyond the three levels, use ValidatingAdmissionPolicy
(chapter 17), Kyverno or OPA Gatekeeper.

## 12.5 NetworkPolicy

By default **every pod can reach every pod**, in every namespace. A NetworkPolicy selects pods
and lists what traffic is **allowed** to (ingress) or from (egress) them. Once any policy selects
a pod for a direction, everything not allowed in that direction is **denied**. Like RBAC, policies
are additive allow-lists.

```yaml
# 1. Default deny all ingress in the namespace
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata: {name: default-deny-ingress}
spec:
  podSelector: {}               # every pod in the namespace
  policyTypes: [Ingress]        # no ingress rules → nothing allowed in
---
# 2. Allow the frontend to call the backend on 8080
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata: {name: backend-from-frontend}
spec:
  podSelector: {matchLabels: {app: backend}}
  policyTypes: [Ingress]
  ingress:
    - from:
        - podSelector: {matchLabels: {app: frontend}}           # same namespace
        - namespaceSelector: {matchLabels: {team: monitoring}}  # OR any pod in those namespaces
      ports:
        - {port: 8080, protocol: TCP}
```

Selector semantics, a classic trap:

```yaml
from:
  - namespaceSelector: {matchLabels: {team: a}}     # two list items = OR
  - podSelector: {matchLabels: {app: x}}
from:
  - namespaceSelector: {matchLabels: {team: a}}     # one item with both = AND
    podSelector: {matchLabels: {app: x}}            #   (pods app=x in namespaces team=a)
```

**Egress** policies are the same with `to:`. If you default-deny egress, **allow DNS** (UDP and TCP
53 to kube-dns) or nothing will resolve. Namespaces have an automatic label
`kubernetes.io/metadata.name: <name>` you can select on. `ipBlock` handles external CIDRs.

NetworkPolicy is implemented by the **CNI plugin**. With a plugin that doesn't support it, the
objects are accepted and **silently do nothing**. That's why your lab runs Calico. Policies are
L3/L4 only (IPs and ports); for L7 rules (HTTP paths) and mTLS you need Cilium or a service mesh.

## 12.6 A security checklist for workloads

* Images: minimal base, scanned, pinned by digest, from a trusted registry; non-root `USER`.
* Pods: `restricted` Pod Security level; `readOnlyRootFilesystem`; resources set.
* Identity: one ServiceAccount per app; no token unless needed; least-privilege Roles; no
  `cluster-admin` bindings for workloads.
* Network: default-deny ingress (and ideally egress) per namespace, explicit allows.
* Secrets: external secret store, encryption at rest, files over env vars, RBAC on `secrets`.
* Cluster: audit logging, an up-to-date version, private API endpoint, restricted
  `nodes/proxy`, admission policies.

## Exercises

| # | Name | What you practise |
|---|---|---|
| 12.1 | `rbac-role` | a least-privilege Role and RoleBinding, tested with `auth can-i` |
| 12.2 | `clusterrole` | cluster-scoped permissions, and a ClusterRole bound per namespace |
| 12.3 | `in-cluster-api` | a pod calling the API with its ServiceAccount token |
| 12.4 | `restricted` | make a Deployment pass the `restricted` Pod Security level |
| 12.5 | `netpol-ingress` | default deny, then allow frontend → backend |
| 12.6 | `netpol-egress` | lock down egress, without breaking DNS |
