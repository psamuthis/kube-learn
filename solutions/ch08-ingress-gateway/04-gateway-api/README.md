# Exercise 8.4 — The Gateway API

The setup installed the **Gateway API CRDs** (standard channel, v1.3.0). That's cluster-wide:
`kubectl get crd | grep gateway`. There's no Gateway *implementation* running, so nothing will
actually route traffic. The point here is to learn the objects, and the API server validates
them against their schemas.

`apps.yaml` gives you two Services, `shop` (v1) and `shop-v2`. Write:

1. `gateway.yaml`: a `Gateway` named `public` with `gatewayClassName: example` and one
   listener named `http` on port 80, protocol HTTP, for the hostname `shop.ex84.kube-learn.test`.
2. `httproute.yaml`: an `HTTPRoute` named `shop` attached to the Gateway `public`, for the
   hostname `shop.ex84.kube-learn.test`, with one rule matching the path prefix `/` that sends
   **90%** of the traffic to `shop` and **10%** to `shop-v2` (both port 80), and a second rule that
   sends requests carrying the header `x-beta: "1"` entirely to `shop-v2`.

`kubectl explain httproute.spec.rules` works for CRDs too.
