# Exercise 15.3 — Patches

Write `overlays/hardened/` on top of `base/`:

1. `resources-patch.yaml`: a **strategic-merge patch** (partial Deployment `shop`) that gives the
   container `app` a memory limit of `64Mi`, and a container `securityContext` with
   `allowPrivilegeEscalation: false` and `readOnlyRootFilesystem: true`.
2. In `kustomization.yaml`, besides that patch, an **inline JSON 6902 patch** on the Deployment
   `shop` that **adds** an env var `HARDENED=true` (the base container has no `env` list yet, so
   add the whole list: `path: /spec/template/spec/containers/0/env`).

Applied with `kubectl apply -k overlays/hardened`.
