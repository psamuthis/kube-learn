# Exercise 13.5 — Nothing resolves

Inside the pod of the Deployment `resolver`, no name resolves, not even
`kubernetes.default.svc.cluster.local`. CoreDNS is fine; other pods resolve normally. Compare
`/etc/resolv.conf` in this pod with the one in any other pod, and fix the Deployment so it uses the
cluster DNS again.

This is a **scenario**: the setup created it in the namespace `ex-13-5` the first time you
ran `./course check 13.5`. There's nothing to apply; repair it **in the cluster** (`kubectl
edit`, `kubectl set …`, `kubectl patch`, or export it with `kubectl get … -o yaml`, fix and
apply). Then fill in `answers.txt` and check again. `--fresh` re-creates the broken state.
