# Exercise 12.4 — The `restricted` Pod Security level

The setup labelled the namespace `ex-12-4` with
`pod-security.kubernetes.io/enforce=restricted`. The Deployment in `deployment.yaml` is accepted,
but no pod ever appears:

```console
$ kubectl -n ex-12-4 get deploy,rs,pods
$ kubectl -n ex-12-4 describe rs        # Events: "… violates PodSecurity "restricted:latest": …"
```

Fix the pod template so it satisfies `restricted` **and** also:

* has a **read-only root filesystem** (kubeapp only needs to write to `/tmp`: give it an `emptyDir`
  there);
* runs as user and group 10001.

Read the violation messages: they list exactly what's missing.
