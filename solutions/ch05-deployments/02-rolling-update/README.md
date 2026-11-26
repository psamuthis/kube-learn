# Exercise 5.2 — A zero-downtime rolling update

`deployment.yaml` runs 3 replicas of `kubeapp:1.0` with the *default* strategy (25% surge, 25%
unavailable). Change it so that:

* rollouts **never** go below 3 available pods, and add at most 1 extra pod at a time;
* a new pod must stay Ready for **3 seconds** before it counts as available;
* the image is `kubeapp:2.0`;
* the annotation `kubernetes.io/change-cause` on the Deployment says `upgrade to 2.0`
  (look at `kubectl rollout history` afterwards).

While you're at it, watch a rollout happen: `kubectl -n ex-5-2 get rs,pods -w` in a second
terminal before you save.

The checker then runs `kubectl rollout restart` and samples the Deployment's available pods
during the whole rollout: they must never drop below 3.
