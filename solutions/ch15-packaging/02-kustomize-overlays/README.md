# Exercise 15.2 — Overlays for dev and prod

`base/` is a complete app: Deployment, Service, and a generated ConfigMap `shop-config` with
`MESSAGE=hello from base` that the Deployment loads with `envFrom`.

Write two overlays:

* `overlays/dev/kustomization.yaml`: name prefix `dev-`, label `env: dev`, and replace the
  ConfigMap's `MESSAGE` with `hello from dev` (a `configMapGenerator` entry with
  `behavior: merge`).
* `overlays/prod/kustomization.yaml`: name prefix `prod-`, label `env: prod`, **3 replicas**,
  image **`kubeapp:2.0`** (with `images:`, no patch), and `MESSAGE=hello from prod`.

```console
$ kubectl kustomize overlays/dev
$ kubectl kustomize overlays/prod | grep -A3 'kind: ConfigMap'   # note the hash suffix
```

The checker applies **prod** (`kubectl apply -k overlays/prod`) and only renders dev.
