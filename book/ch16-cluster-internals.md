# Chapter 16 — Cluster internals and operations

> **Reading time:** ~50 min · **Exercises:** `exercises/ch16-cluster-internals/` (5)

So far we've *used* a cluster. This chapter is about *running* one: how it's bootstrapped, the
certificates that hold it together, how users get credentials, backing up etcd, upgrading, and
repairing a broken node. Managed clusters hide most of this, but you'll still meet it when things
go wrong, and the CKA exam is full of it.

## 16.1 Bootstrapping with kubeadm

`kubeadm init` on the first control-plane node:

1. **preflight** checks (swap off, ports free, runtime reachable);
2. generates the **PKI** (CA, API server cert, etcd CA and certs, front-proxy CA, the ServiceAccount
   signing key pair);
3. writes **kubeconfig files** for the admin, kubelet, controller-manager and scheduler
   (`/etc/kubernetes/*.conf`);
4. writes **static pod manifests** for etcd, kube-apiserver, kube-controller-manager and
   kube-scheduler (`/etc/kubernetes/manifests/`), and waits for the kubelet to start them;
5. uploads its configuration into ConfigMaps (`kubeadm-config`, `kubelet-config` in kube-system),
   creates a **bootstrap token**, and installs CoreDNS and kube-proxy.

`kubeadm join <api>:6443 --token … --discovery-token-ca-cert-hash sha256:…` on a worker uses
**TLS bootstrapping**: the kubelet authenticates with the short-lived token, submits a
**CertificateSigningRequest** for its own client certificate, which is auto-approved, and from
then on authenticates as `system:node:<name>` (group `system:nodes`). The **Node authorizer**
limits each kubelet to the objects of its own pods.

minikube runs the same steps, with its files in slightly different places: certs in
`/var/lib/minikube/certs/` instead of `/etc/kubernetes/pki/`, and the API server on port 8443
instead of 6443.

*Kubernetes the Hard Way* does all of this by hand, with no kubeadm: `openssl`/`cfssl` for every
cert, systemd units for every component, routes for pod CIDRs. It takes a day, and it's the best
way to really see that there's no magic. Read it after this chapter.

## 16.2 The PKI

```text
cluster CA (ca.crt) ─┬─ apiserver.crt            server cert, SANs: kubernetes, kubernetes.default.svc, 10.96.0.1, node IP…
                     ├─ apiserver-kubelet-client  API server → kubelets (logs, exec)
                     ├─ admin / user client certs  CN = user, O = groups (system:masters = cluster-admin, bypasses RBAC!)
                     ├─ kubelet client certs       CN = system:node:<node>, O = system:nodes
                     └─ controller-manager, scheduler client certs
etcd CA ─────────────┬─ etcd server/peer certs
                     └─ apiserver-etcd-client     API server → etcd
front-proxy CA ──────── front-proxy-client        API server → aggregated APIs (metrics-server)
sa.key / sa.pub        signing key for ServiceAccount tokens (JWTs), not a cert
```

* `openssl x509 -in apiserver.crt -noout -text` shows the subject, issuer, validity and SANs.
* kubeadm certs are valid for **1 year** (the CA for 10). `kubeadm certs check-expiration` and
  `kubeadm certs renew all`. Upgrades renew them, so clusters that never upgrade break after a year.
* A client cert in group **`system:masters`** is effectively root: RBAC doesn't apply to it, and
  certs can't be revoked. Keep such credentials offline. Your minikube kubeconfig uses one
  (`O=system:masters, CN=minikube-user`).

## 16.3 Users through the CertificateSigningRequest API

You can issue a user certificate *through the API* instead of touching the CA key:

```console
$ openssl genrsa -out alice.key 2048
$ openssl req -new -key alice.key -out alice.csr -subj "/CN=alice/O=developers"
$ cat <<EOF | kubectl apply -f -
apiVersion: certificates.k8s.io/v1
kind: CertificateSigningRequest
metadata: {name: alice}
spec:
  request: $(base64 -w0 alice.csr)
  signerName: kubernetes.io/kube-apiserver-client
  expirationSeconds: 86400
  usages: [client auth]
EOF
$ kubectl certificate approve alice
$ kubectl get csr alice -o jsonpath='{.status.certificate}' | base64 -d > alice.crt
```

Then build a kubeconfig for it:

```console
$ kubectl config set-cluster kube-learn --server=$(kubectl config view --minify -o jsonpath='{.clusters[0].cluster.server}') \
    --certificate-authority=$HOME/.minikube/ca.crt --embed-certs --kubeconfig=alice.kubeconfig
$ kubectl config set-credentials alice --client-certificate=alice.crt --client-key=alice.key --embed-certs --kubeconfig=alice.kubeconfig
$ kubectl config set-context alice --cluster=kube-learn --user=alice --namespace=dev --kubeconfig=alice.kubeconfig
$ kubectl config use-context alice --kubeconfig=alice.kubeconfig
$ kubectl --kubeconfig=alice.kubeconfig auth whoami
```

alice can authenticate, but she can do nothing until RBAC grants her (or her group `developers`)
something.

## 16.4 etcd backup and restore

etcd is the cluster's only state, so **back it up**:

```console
# inside the etcd pod (or anywhere with the certs and network access)
$ ETCDCTL_API=3 etcdctl --endpoints=https://127.0.0.1:2379 \
    --cacert=…/etcd/ca.crt --cert=…/etcd/server.crt --key=…/etcd/server.key \
    snapshot save /var/lib/etcd-backup/snap.db
$ etcdutl snapshot status /var/lib/etcd-backup/snap.db -w table   # hash, revision, keys, size
```

**Restore** (a disaster-recovery operation, never casual): stop the API server and etcd (move
their static pod manifests out of the manifests directory), `etcdutl snapshot restore snap.db
--data-dir /var/lib/etcd-restored`, point etcd's `--data-dir` (its hostPath volume) at the new
directory, and move the manifests back. Everything created after the snapshot is lost, and
controllers will reconcile the world back to the snapshot's state, so pods may be killed or
created. GitOps-managed clusters often prefer "rebuild and re-sync" to restoring etcd.

Backups of *objects* (not etcd) with Velero are more portable: across clusters, versions and
namespaces.

## 16.5 Upgrades

Version skew rules: the API server leads. Controller-manager and scheduler may be one minor
version behind; kubelets up to three; kubectl ±1. So an upgrade goes, **one minor version at a
time**:

1. Read the changelog's "urgent upgrade notes" and deprecated API removals. Tools like `pluto` or
   `kubent` find manifests using removed APIs.
2. Upgrade the control plane: `kubeadm upgrade plan`, then `kubeadm upgrade apply v1.x.y` on the
   first node and `kubeadm upgrade node` on the others.
3. For each worker: `kubectl drain`, upgrade the kubelet and kubeadm packages, `kubeadm upgrade node`,
   restart the kubelet, `kubectl uncordon`. PDBs keep applications available throughout
   (chapter 11).

Managed clusters do steps 2–3 for you (node pools get replaced, also drained with PDBs).

## 16.6 High availability

* **Stacked**: 3 control-plane nodes, each running apiserver + etcd member + controller-manager
  + scheduler, behind a load balancer for the API (port 6443).
* **External etcd**: a separate etcd cluster of 3–5 nodes. More machines, better isolation.
* controller-manager and scheduler are active/passive through **leader election** (Leases, see
  chapter 2); API servers are all active.
* Workers don't need HA themselves: the scheduler spreads replicas across them, ideally across
  zones (topology spread, chapter 11).

## 16.7 When a node breaks

The node lifecycle controller marks a node `NotReady` (then `Unknown`) after its Lease isn't
renewed for 40 s, taints it `node.kubernetes.io/unreachable:NoExecute`, and its pods are evicted
after their toleration (300 s by default), then recreated elsewhere by their controllers.
StatefulSet pods are **not** replaced while the old one might still be running: that's safety
over availability. Debugging is in 13.6: `describe node`, then on the node `systemctl status
kubelet`, `journalctl -u kubelet`, `crictl`.

## Exercises

| # | Name | What you practise |
|---|---|---|
| 16.1 | `pki` | inspect the cluster's certificates and your own credentials |
| 16.2 | `new-user` | issue a user certificate through the CSR API, build a kubeconfig, grant RBAC |
| 16.3 | `etcd-backup` | snapshot etcd and verify the snapshot |
| 16.4 | `broken-kubelet` | a node goes NotReady: find out why on the node, and fix it |
| 16.5 | `leases` | heartbeats and leader election, seen through Lease objects |
