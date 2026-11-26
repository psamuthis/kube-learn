# Exercise 1.3 — Namespaces and cgroups from the inside

`pod.yaml` runs kubeapp with resource limits. Once it's running (`./course check 1.3` applies it),
investigate with `kubectl -n ex-1-3 exec -it inspect -- sh` and fill in `answers.txt`:

* inside the container: `ps`, `hostname`, `cat /sys/fs/cgroup/memory.max`, `cat /sys/fs/cgroup/cpu.max`;
* on the node: find the *same* process as the node's kernel sees it.
  `kubectl -n ex-1-3 get pod inspect -o wide` tells you the node;
  `minikube -p kube-learn ssh -n <node>` gets you a shell there;
  `sudo crictl ps` and `sudo crictl inspect <container-id>` (look for `"pid"`) find it.
