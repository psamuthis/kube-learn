# Chapter 8 — Ingress and the Gateway API

> **Reading time:** ~35 min · **Exercises:** `exercises/ch08-ingress-gateway/` (4)

A `LoadBalancer` Service per app gives you one external IP (and one cloud bill line) per app, at
layer 4. What you usually want is **one** entry point that routes HTTP by host name and path,
terminates TLS, and maybe rewrites, rate-limits or authenticates. That's an **ingress
controller** (a reverse proxy running in the cluster) configured by **Ingress** or **Gateway
API** objects.

## 8.1 The moving parts

```text
 client ──▶ LB / NodePort / hostPort ──▶ ingress controller pods (nginx, Traefik, HAProxy, Envoy…)
                                              │ watches Ingress objects, renders its proxy config
                                              ├── Host: shop.example.com  /      ──▶ Service shop ──▶ pods
                                              └── Host: shop.example.com  /api   ──▶ Service api  ──▶ pods
```

* The **Ingress** object is just configuration; **nothing happens without a controller**.
  Kubernetes doesn't ship one. minikube's `ingress` addon installs **ingress-nginx** in the
  namespace `ingress-nginx`, listening on ports 80/443 of the control-plane node (`hostPort`).
* Controllers usually proxy **straight to pod IPs** (they read the EndpointSlices), skipping
  kube-proxy: per-request balancing, keep-alive pools, retries.
* An **IngressClass** says which controller handles which Ingress (`spec.ingressClassName`).
  Several controllers can coexist.

## 8.2 An Ingress

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: shop
spec:
  ingressClassName: nginx
  rules:
    - host: shop.kube-learn.test
      http:
        paths:
          - path: /
            pathType: Prefix          # Prefix | Exact | ImplementationSpecific
            backend:
              service:
                name: shop
                port: {name: http}    # or {number: 80}
```

* `pathType: Prefix` matches by path *segment*: `/api` matches `/api` and `/api/x`, not `/apix`.
  The longest match wins.
* No `host` means it matches any host.
* `defaultBackend` catches what no rule matches (otherwise nginx returns its own 404).
* The backend Service must be in the **same namespace** as the Ingress.

Test without DNS by setting the Host header yourself:

```console
$ curl -H 'Host: shop.kube-learn.test' http://$(minikube -p kube-learn ip)/
$ curl --resolve shop.kube-learn.test:80:$(minikube -p kube-learn ip) http://shop.kube-learn.test/
```

## 8.3 Controller-specific behaviour: annotations

The Ingress API is deliberately small: hosts, paths, TLS. Everything else is done with
**annotations** that only one controller understands. For ingress-nginx:

```yaml
metadata:
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /$2        # with a regex path, see below
    nginx.ingress.kubernetes.io/use-regex: "true"
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/proxy-body-size: 10m
    nginx.ingress.kubernetes.io/limit-rps: "20"
    nginx.ingress.kubernetes.io/canary: "true"             # + canary-weight: "10"
    nginx.ingress.kubernetes.io/canary-weight: "10"
```

**Path rewriting** is the classic need: the app serves `/`, but you publish it under `/api/`:

```yaml
metadata:
  annotations:
    nginx.ingress.kubernetes.io/use-regex: "true"
    nginx.ingress.kubernetes.io/rewrite-target: /$2
spec:
  rules:
    - http:
        paths:
          - path: /api(/|$)(.*)                # $2 = everything after /api/
            pathType: ImplementationSpecific
            backend: {service: {name: api, port: {number: 80}}}
```

Note that the rewrite annotation applies to *every* path of that Ingress object, so put
rewritten and non-rewritten routes in **separate Ingress objects** (the controller merges all
Ingresses for the same host).

Annotations are the Ingress API's big weakness: they're stringly-typed, unvalidated, and not
portable between controllers. That's why the Gateway API exists.

## 8.4 TLS

```yaml
spec:
  tls:
    - hosts: [shop.kube-learn.test]
      secretName: shop-tls             # a Secret of type kubernetes.io/tls: tls.crt + tls.key
  rules: [...]
```

```console
$ openssl req -x509 -newkey rsa:2048 -nodes -days 30 -keyout tls.key -out tls.crt \
    -subj "/CN=shop.kube-learn.test" -addext "subjectAltName=DNS:shop.kube-learn.test"
$ kubectl create secret tls shop-tls --cert=tls.crt --key=tls.key
$ curl -k --resolve shop.kube-learn.test:443:$(minikube -p kube-learn ip) https://shop.kube-learn.test/
```

The controller picks the certificate by **SNI** (the host name in the TLS handshake). Hosts with
no matching certificate get the controller's self-signed "Kubernetes Ingress Controller Fake
Certificate". In real clusters, **cert-manager** watches Ingresses (or Certificate objects) and
gets and renews certificates from Let's Encrypt or your CA automatically.

## 8.5 The Gateway API

The Gateway API (`gateway.networking.k8s.io`, v1 since 2023) is Ingress's successor. It splits
responsibilities across **roles**, and typed fields replace annotations:

```text
GatewayClass     (infra provider)   "Envoy Gateway / Cilium / NGINX Gateway Fabric / GKE L7…"
   └── Gateway   (cluster operator) "listen on :443 for *.example.com with this cert"
         └── HTTPRoute (app team)   "for shop.example.com, /api → Service api (90%) + api-v2 (10%)"
```

```yaml
apiVersion: gateway.networking.k8s.io/v1
kind: HTTPRoute
metadata: {name: shop}
spec:
  parentRefs: [{name: public-gateway, namespace: infra}]
  hostnames: [shop.example.com]
  rules:
    - matches: [{path: {type: PathPrefix, value: /api}}]
      filters:
        - type: URLRewrite
          urlRewrite: {path: {type: ReplacePrefixMatch, replacePrefixMatch: /}}
      backendRefs:
        - {name: api, port: 80, weight: 90}
        - {name: api-v2, port: 80, weight: 10}       # a canary, as a typed field
    - matches: [{headers: [{name: x-beta, value: "1"}]}]
      backendRefs: [{name: shop-beta, port: 80}]
```

Header matching, weights, rewrites, redirects, request mirroring, cross-namespace attachment
(controlled by `allowedRoutes` on the Gateway and `ReferenceGrant`s) are all part of the
standard API. There are also `GRPCRoute`, `TLSRoute` and `TCPRoute`. The CRDs aren't installed
by default, and like Ingress you need an implementation. For new projects, the Gateway API is
the recommended choice. ingress-nginx itself is being retired in favour of Gateway API
implementations.

## Exercises

| # | Name | What you practise |
|---|---|---|
| 8.1 | `host-routing` | an Ingress that routes two host names to two Services |
| 8.2 | `path-rewrite` | path-based routing with a regex rewrite |
| 8.3 | `tls` | a self-signed certificate, a TLS Secret and HTTPS through the Ingress |
| 8.4 | `gateway-api` | install the Gateway API CRDs and write a weighted HTTPRoute |
