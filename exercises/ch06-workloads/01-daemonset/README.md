# Exercise 6.1 — A node agent

Complete `daemonset.yaml`: a DaemonSet `node-agent` that runs one `busybox:1.37` pod on **every
node, including control-plane nodes** (production control planes are tainted
`node-role.kubernetes.io/control-plane:NoSchedule`, so add the toleration even though minikube
doesn't taint), and that:

* gets the name of its node in the env var `NODE_NAME` (downward API: `fieldRef` →
  `spec.nodeName`);
* mounts the node's `/var/log` read-only at `/host/var/log` (a `hostPath` volume);
* runs `sh -c 'echo "agent on $NODE_NAME"; ls /host/var/log | head; sleep infinity'`;
* requests only 5m CPU and 8Mi memory (agents must be cheap: there's one on every node).
