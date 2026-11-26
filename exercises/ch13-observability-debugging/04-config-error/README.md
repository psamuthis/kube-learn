# Exercise 13.4 — CreateContainerConfigError

The Deployment `shop` reads its log level from the ConfigMap `shop-settings`, and its pods
never start. Fix it so the pods run with `LOG_LEVEL=info` (the value that's in the ConfigMap).

This is a **scenario**: the setup created it in the namespace `ex-13-4` the first time you
ran `./course check 13.4`. There's nothing to apply; repair it **in the cluster** (`kubectl
edit`, `kubectl set …`, `kubectl patch`, or export it with `kubectl get … -o yaml`, fix and
apply). Then fill in `answers.txt` and check again. `--fresh` re-creates the broken state.
