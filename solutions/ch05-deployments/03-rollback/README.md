# Exercise 5.3 — Rolling back

The setup deployed `web` with `kubeapp:1.0`, then "upgraded" it to `kubeapp:1.1`, which doesn't
exist. The rollout is stuck. Thanks to `maxUnavailable: 0`, users still get the old version.

1. Look: `kubectl -n ex-5-3 get deploy,rs,pods`, `kubectl -n ex-5-3 rollout status deploy/web`,
   `kubectl -n ex-5-3 describe deploy web` (Conditions!), `kubectl -n ex-5-3 rollout history deploy/web`.
2. Fill in `answers.txt`.
3. Roll back **with `kubectl rollout undo`**. Don't delete anything and don't edit the YAML:
   the checker verifies that the broken ReplicaSet still exists (scaled to 0) and that the
   rollback created a new revision.

There's nothing to apply: this one is all kubectl.
