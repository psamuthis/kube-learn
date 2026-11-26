# Exercise 13.7 — Finding the CPU hog

The setup started three Deployments, `alpha`, `bravo` and `charlie`. One of them burns CPU.
Find which with **metrics-server** (it needs a minute after the pods start before it has
numbers):

```console
$ kubectl top nodes
$ kubectl -n ex-13-7 top pods --sort-by=cpu
```

Answer in `answers.txt`, then scale the culprit down to 0 replicas.
