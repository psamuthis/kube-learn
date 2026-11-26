# Exercise 12.6 — NetworkPolicy: egress

The pod `client` (labelled `app: client`, started by the checker) is a suspicious third-party
component. Lock down what it can *call*:

* **only** the `backend` pods on TCP 8080;
* and DNS, otherwise it can't even resolve `backend`: UDP and TCP 53 to the CoreDNS pods
  (`k8s-app: kube-dns` in the namespace `kube-system`).

Write `netpol.yaml`: one policy `client-egress` selecting `app: client` with
`policyTypes: [Egress]`. Other pods in the namespace must stay unrestricted.

The checker expects `client` to resolve and reach `backend`, but *not* reach the ingress
controller or the API server, while another pod (`other`) still reaches everything.
