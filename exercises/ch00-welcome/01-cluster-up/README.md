# Exercise 0.1 — Cluster up

Start the lab cluster and get your bearings.

1. `./course cluster up` (takes a few minutes the first time: it downloads Kubernetes and builds
   the course's `kubeapp` image onto every node).
2. Use `kubectl get nodes`, `kubectl version` and `kubectl config current-context` to fill in
   `answers.txt`.

There's nothing to apply in this exercise; the checker just compares your answers with the
cluster. (Tip: an answer can also be a command: `nodes: $ kubectl get nodes --no-headers | wc -l`.)
