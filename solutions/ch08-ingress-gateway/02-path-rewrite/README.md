# Exercise 8.2 — Paths and rewrites

`apps.yaml` runs a frontend `web` and an `api`. Both are plain kubeapp, serving from `/`. Publish
them on one host, `shop.ex82.kube-learn.test`:

* `/` and everything else → `web`, unchanged;
* `/api/<rest>` → `api`, with the `/api` prefix **removed** (so `/api/hostname` reaches the api's
  `/hostname`), using ingress-nginx's regex rewrite (section 8.3).

Since the rewrite annotation applies to a whole Ingress object, write **two** Ingresses in
`ingress.yaml`: `web` and `api`.
