# Exercise 3.4 — Stuck in deletion

The setup created a ConfigMap `stuck` and then *deleted* it. Yet it's still there:

```console
$ kubectl -n ex-3-4 get configmap stuck -o yaml
```

1. Find out why, and fill in `answers.txt`.
2. Then get rid of it for good. You can't edit the ConfigMap's data any more (try it!), but you
   can still change one field.

In real life the finalizer would belong to a controller that's supposed to clean something up
first; removing it by hand skips that cleanup. Here, there's no controller: the finalizer
`kube-learn.dev/never` is a trap.
