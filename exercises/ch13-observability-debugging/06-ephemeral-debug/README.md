# Exercise 13.6 — Debugging a container with no shell

The pod `vault` runs the `pause` image: a single static binary, with no shell, no `ls`, no
`cat`. Its container `main` has an environment variable `SECRET_WORD`. Find its value **without
looking at the pod spec** (pretend you're not allowed to: in real life it would come from a
Secret you can't read):

```console
$ kubectl -n ex-13-6 exec vault -- sh             # fails: no shell in the image
$ kubectl -n ex-13-6 debug -it vault --image=busybox:1.37 --target=main --profile=general
/ # ps                                            # you see the pause process: shared PID namespace
/ # tr '\0' '\n' < /proc/<pid>/environ            # (`--profile=general` grants the ptrace capability this needs)
```

Write the word in `answers.txt`. The checker also verifies that you used an ephemeral container.
