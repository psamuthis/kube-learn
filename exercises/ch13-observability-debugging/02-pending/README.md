# Exercise 13.2 — Pending forever

The Deployment `worker` has 2 replicas, and they stay `Pending`. There are **two** problems in its
pod template. The `FailedScheduling` event names them both. The workload really needs 100m CPU
and 64Mi memory, and it doesn't care which node it runs on.

This is a **scenario**: the setup created it in the namespace `ex-13-2` the first time you
ran `./course check 13.2`. There's nothing to apply; repair it **in the cluster** (`kubectl
edit`, `kubectl set …`, `kubectl patch`, or export it with `kubectl get … -o yaml`, fix and
apply). Then fill in `answers.txt` and check again. `--fresh` re-creates the broken state.
