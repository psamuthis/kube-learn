# Exercise 4.5 — QoS classes

Complete `pods.yaml` so that the three pods get the QoS class their name says:

* `guaranteed`: requests **equal** limits for both CPU and memory (use 100m CPU, 64Mi memory);
* `burstable`: a memory request of 32Mi and a memory limit of 128Mi;
* `besteffort`: no resources at all.

Then check `kubectl -n ex-4-5 get pods -o custom-columns=NAME:.metadata.name,QOS:.status.qosClass`.

Resources of a running pod can't be changed with apply: use `--fresh` after editing.
