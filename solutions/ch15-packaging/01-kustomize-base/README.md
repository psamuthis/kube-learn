# Exercise 15.1 — A Kustomize base

`base/` contains a Deployment and a Service. Write `base/kustomization.yaml` so that it:

* includes both files;
* adds the label `app.kubernetes.io/name: shop` to **every object, including selectors and pod
  templates** (`labels` with `includeSelectors: true`);
* adds the label `app.kubernetes.io/part-of: kube-learn` to every object's metadata **only**
  (a second `labels` entry, without selectors, so it could change later without breaking the
  immutable Deployment selector).

Render it before applying: `kubectl kustomize base`. The checker runs `kubectl apply -k base`.
