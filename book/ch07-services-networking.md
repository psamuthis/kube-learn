# Chapter 7 — Services and cluster networking

> **Reading time:** ~60 min · **Exercises:** `exercises/ch07-services-networking/` (7)

Pods come and go, and their IPs change every time. This chapter is about how anything finds
anything: the Kubernetes network model, Services, kube-proxy, EndpointSlices and DNS.

## 7.1 The network model: three rules

Kubernetes doesn't implement networking; it imposes **requirements** and lets a CNI plugin meet
them:

1. **Every pod gets its own IP address**, unique in the cluster.
2. **Every pod can reach every other pod's IP directly**, on any node, without NAT.
3. Agents on a node (kubelet, system daemons) can reach all pods on that node.

So a pod is like a VM on a flat network: no port mapping, no "which host port did I get?".
Containers in a pod share the IP (chapter 4). How the CNI plugin achieves this varies:

* **Overlay** (VXLAN/IP-in-IP encapsulation): Flannel, Calico in IPIP/VXLAN mode. Works on any
  underlying network.
* **Routed**: Calico with BGP, cloud routes. Each node owns a pod CIDR (`kubectl get node -o
  jsonpath='{.spec.podCIDR}'`) and routes are announced between nodes.
* **Native VPC IPs**: AWS VPC CNI, Azure CNI. Pods get real VPC addresses.
* **eBPF**: Cilium replaces iptables entirely and can also replace kube-proxy.

```console
$ kubectl get pods -A -o wide                 # pod IPs from 10.244.x.y
$ minikube -p kube-learn ssh -- ip route      # routes to other nodes' pod CIDRs (via tunl0 / cali*)
```

## 7.2 Services: a stable name and IP for a moving set of pods

A **Service** selects pods by label and gives them a stable **virtual IP** (ClusterIP) and a
DNS name. Connections to `ClusterIP:port` are load-balanced over the **Ready** pods behind it.

```yaml
apiVersion: v1
kind: Service
metadata: {name: web}
spec:
  type: ClusterIP              # default
  selector: {app: web}         # equality map: which pods
  ports:
    - name: http
      port: 80                 # the Service's port (what clients use)
      targetPort: http         # the pod's port: a number or a *named* container port
      protocol: TCP
```

`kubectl expose deployment web --port 80 --target-port 8080` generates one.

Behind the scenes:

```text
Service web (selector app=web) ──watched by──▶ EndpointSlice controller
                                                  │ lists IP:port of Ready pods matching the selector
                                                  ▼
                                    EndpointSlice web-abc12  [10.244.1.7:8080, 10.244.2.3:8080, …]
                                                  │ watched by kube-proxy on every node
                                                  ▼
                       iptables: dst 10.96.14.2:80 → DNAT to a random endpoint
```

* The ClusterIP **isn't on any interface**. You can't ping it. It exists only as packet rewrite
  rules on every node, so traffic is load-balanced at the *client's* node.
* Load balancing is **per connection**, not per request. HTTP/1.1 keep-alive or gRPC (HTTP/2)
  clients stick to one pod. For per-request balancing you need an L7 proxy (ingress, mesh).
* **Not-ready pods are removed** from the endpoints. That's what readiness probes are *for*.
* `sessionAffinity: ClientIP` pins a client IP to a pod.
* **Selector mismatch** is the #1 Service bug: `kubectl get endpointslices -l
  kubernetes.io/service-name=web` shows an empty list. Always check endpoints when a Service
  "doesn't work".

## 7.3 Service types

| Type | Reachable from | How |
|---|---|---|
| `ClusterIP` | inside the cluster | virtual IP + DNS name |
| `NodePort` | outside, via `<any node IP>:<30000–32767>` | ClusterIP + a port opened on *every* node |
| `LoadBalancer` | outside, via an external IP | NodePort + a cloud load balancer pointing at it (provisioned by the cloud-controller-manager) |
| `ExternalName` | inside | just a DNS CNAME to an external name, no proxying |
| headless (`clusterIP: None`) | inside | no virtual IP: DNS returns the **pod IPs** directly |

* **NodePort**: `externalTrafficPolicy: Local` keeps traffic on the node it arrived at (preserves
  the client source IP, but nodes without a local pod drop it); `Cluster` (default) may forward to
  another node with SNAT.
* **LoadBalancer** without a cloud (bare metal, minikube) stays `<pending>` forever, unless you run
  MetalLB, or `minikube tunnel`, which assigns external IPs from your machine.
* **Headless** Services are for clients that want to pick pods themselves (databases, StatefulSet
  peers, gRPC client-side balancing). Chapter 6 used one for stable pod DNS names.
* A Service **without a selector** gets no automatic endpoints. You create the EndpointSlice
  yourself, which is a way to give an in-cluster name to something outside (a legacy VM database).

## 7.4 kube-proxy and the data path

kube-proxy runs on every node (a DaemonSet) in one of these modes:

* **iptables** (the default here): for each Service, a `KUBE-SVC-…` chain that jumps to one
  `KUBE-SEP-…` (service endpoint) chain at random (using `statistic --probability`); each SEP
  chain DNATs to a pod IP:port. Lookup is O(number of rules), which gets slow with tens of
  thousands of Services.
* **ipvs**: kernel L4 load balancer, hash tables, many algorithms.
* **nftables** (GA in 1.33): the modern replacement for iptables mode.
* Or no kube-proxy at all, with Cilium's eBPF.

```console
$ kubectl -n kube-system get cm kube-proxy -o yaml | grep mode
$ minikube -p kube-learn ssh -- sudo iptables-save -t nat | grep -A3 'KUBE-SVC' | head -30
```

Exercise 7.6 has you find your own Service in those rules.

## 7.5 DNS

**CoreDNS** (a Deployment in kube-system, behind the Service `kube-dns`) serves the cluster
zone:

| Name | Resolves to |
|---|---|
| `web.shop.svc.cluster.local` | the ClusterIP of Service `web` in namespace `shop` |
| `web` (from a pod in `shop`) | same, thanks to the search path |
| `web.shop` (from anywhere) | same |
| `db-0.db.shop.svc.cluster.local` | pod `db-0` behind headless Service `db` |
| `_http._tcp.web.shop.svc.cluster.local` | SRV record: port number for the named port `http` |
| `10-244-1-7.shop.pod.cluster.local` | a pod by IP (rarely useful) |

Every pod's `/etc/resolv.conf` (written by the kubelet) looks like:

```text
search shop.svc.cluster.local svc.cluster.local cluster.local
nameserver 10.96.0.10        ← the kube-dns Service's ClusterIP
options ndots:5
```

**Service environment variables.** For historical reasons the kubelet also injects, into every
pod, env vars for each Service that existed in the namespace when the pod started:
`WEB_SERVICE_HOST=10.96.14.2`, `WEB_SERVICE_PORT=80`, and Docker-links style
`WEB_PORT=tcp://10.96.14.2:80`. A Service named `redis` therefore sets `REDIS_PORT=tcp://…` in
every pod, which breaks apps that read `REDIS_PORT` as a number. Use DNS instead, and set
`enableServiceLinks: false` in the pod spec if those variables get in the way.

`ndots:5` means any name with fewer than 5 dots is first tried with each search suffix. That's
why `web` works, and also why `api.example.com` costs up to 4 useless lookups before the real
one. Use a trailing dot (`api.example.com.`) for external names in hot paths. `dnsPolicy` and
`dnsConfig` in the pod spec override all this.

## 7.6 Debugging connectivity, step by step

When "service X can't reach service Y", work up the stack:

```console
$ kubectl get svc y -o wide                        # selector, ports
$ kubectl get endpointslices -l kubernetes.io/service-name=y   # empty? selector/readiness problem
$ kubectl get pods -l <selector> -o wide           # are they Ready? right labels?
$ kubectl run -it --rm t --image=busybox:1.37 -- sh
  / # nslookup y.ns.svc.cluster.local              # DNS ok?
  / # wget -qO- -T 2 http://<pod IP>:<targetPort>/ # pod directly ok?
  / # wget -qO- -T 2 http://y.ns/                  # through the Service ok?
$ kubectl port-forward svc/y 8080:80               # from your machine (bypasses kube-proxy)
```

Typical culprits, in order: the selector doesn't match the pod labels; `targetPort` doesn't match
what the process listens on; pods aren't Ready; the app listens on `127.0.0.1` instead of
`0.0.0.0`; a NetworkPolicy blocks it (chapter 12).

## Exercises

| # | Name | What you practise |
|---|---|---|
| 7.1 | `clusterip` | a Service with a named targetPort |
| 7.2 | `broken-service` | fix a Service with no endpoints |
| 7.3 | `nodeport` | reach a Service from your machine |
| 7.4 | `dns` | resolv.conf, search paths, FQDNs, SRV records |
| 7.5 | `headless` | DNS that returns every pod |
| 7.6 | `kube-proxy` | find your Service in the node's iptables rules |
| 7.7 | `manual-endpoints` | a Service with no selector and a hand-written EndpointSlice |
