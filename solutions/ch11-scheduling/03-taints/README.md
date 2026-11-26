# Exercise 11.3 — A dedicated node

Reserve `kube-learn-m03` for GPU jobs (pretend it has a GPU):

1. **Label** it `dedicated=gpu` and **taint** it `dedicated=gpu:NoSchedule` (two kubectl commands).
2. Complete `gpu-job.yaml` so its 2 replicas run **only** on that node: they need a toleration
   *and* a nodeSelector. Why both? Read section 11.5 again.

`others.yaml` (6 replicas, no toleration) must end up entirely on the other nodes.
`./course clean 11.3` removes the taint and the label.
