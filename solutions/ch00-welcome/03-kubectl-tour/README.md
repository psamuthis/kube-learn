# Exercise 0.3 — A kubectl tour

Answer the questions in `answers.txt` by exploring the cluster with `kubectl get`, `-o wide`,
`describe`, `-n`, `-A` and `cluster-info`. Nothing to apply.

Some questions are about the `kube-system` namespace, where the cluster's own components run.
Look at it with `kubectl get pods -n kube-system -o wide`.
