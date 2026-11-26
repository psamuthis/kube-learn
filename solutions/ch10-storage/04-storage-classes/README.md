# Exercise 10.4 — Storage classes and binding

`pvc.yaml` (applied by the checker) creates a claim `probe` that nothing uses yet.

1. Inspect `kubectl get storageclass` and `kubectl -n ex-10-4 describe pvc probe`, and answer
   the first questions in `answers.txt`.
2. Then apply the pod yourself: `kubectl -n ex-10-4 apply -f manual/pod.yaml`. Watch the claim become
   Bound, find the PV that was created, and answer the rest.
