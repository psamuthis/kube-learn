# Exercise 4.6 — OOMKilled

The Deployment `hog` runs a program that needs about **100 MiB** of memory. It keeps dying.
Apply it (`./course check 4.6`) and investigate:

```console
$ kubectl -n ex-4-6 get pods                # STATUS, RESTARTS
$ kubectl -n ex-4-6 describe pod <pod>      # Last State: Terminated, Reason: …, Exit Code: …
```

1. Fill in `answers.txt`.
2. Fix `deployment.yaml` by giving the container a memory limit that fits the program
   (at least 128Mi, at most 256Mi). Don't change the program.
