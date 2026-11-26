# Exercise 13.3 — Running, but no traffic

The pods of the Deployment `web` are `Running`, but `http://web/` (the Service) doesn't
answer. Follow the chain Service → EndpointSlice → Pods and fix the root cause, without
changing the Service.

This is a **scenario**: the setup created it in the namespace `ex-13-3` the first time you
ran `./course check 13.3`. There's nothing to apply; repair it **in the cluster** (`kubectl
edit`, `kubectl set …`, `kubectl patch`, or export it with `kubectl get … -o yaml`, fix and
apply). Then fill in `answers.txt` and check again. `--fresh` re-creates the broken state.
