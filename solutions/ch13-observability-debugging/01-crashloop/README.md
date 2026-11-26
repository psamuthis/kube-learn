# Exercise 13.1 — CrashLoopBackOff

The Deployment `api` never becomes available; its pods restart over and over. Find out why
from the container's **exit code** and its **previous logs**, and fix it so that kubeapp starts.

This is a **scenario**: the setup created it in the namespace `ex-13-1` the first time you
ran `./course check 13.1`. There's nothing to apply; repair it **in the cluster** (`kubectl
edit`, `kubectl set …`, `kubectl patch`, or export it with `kubectl get … -o yaml`, fix and
apply). Then fill in `answers.txt` and check again. `--fresh` re-creates the broken state.
