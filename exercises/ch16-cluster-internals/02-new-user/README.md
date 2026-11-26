# Exercise 16.2 — A new user, the proper way

Create a user **alice** in the group **developers** who can *read* everything in `ex-16-2`, and
nothing else:

1. Complete `make-alice.sh` (section 16.3). It must:
   * generate a key and a CSR with `CN=alice, O=developers` (openssl);
   * submit it as a `CertificateSigningRequest` named **`alice-ex162`**, signer
     `kubernetes.io/kube-apiserver-client`, usage `client auth`, valid for one day;
   * approve it, and fetch the signed certificate;
   * write a self-contained kubeconfig **`alice.kubeconfig`** in this directory (embedded certs,
     default namespace `ex-16-2`). The cluster CA is `~/.minikube/ca.crt`.
2. Write `rbac.yaml`: a RoleBinding `alice-view` giving the built-in ClusterRole `view` to the
   **User** `alice` in this namespace.

Run `bash make-alice.sh`, then `kubectl --kubeconfig alice.kubeconfig get pods` and
`kubectl --kubeconfig alice.kubeconfig delete pod x` (it should be forbidden).
`alice.key` and `alice.kubeconfig` are credentials: don't commit them. `./course clean 16.2`
deletes the CSR.
