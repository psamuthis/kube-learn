# Exercise 9.4 — Live config updates

`deployment.yaml` mounts the key `greeting.txt` of the ConfigMap `live` as the file
`/config/greeting.txt`, using `subPath`. The ops team expects that editing the ConfigMap
updates the file in the running pods, without a restart. It doesn't.

Try it:

```console
$ kubectl -n ex-9-4 edit configmap live           # change the greeting
$ kubectl -n ex-9-4 exec deploy/greeter -- cat /config/greeting.txt    # wait a minute… still old
```

Fix the **mount** so that changes propagate. The file must still appear as
`/config/greeting.txt`. The checker edits the ConfigMap and waits up to 90 seconds for the
new content to show up in `/config`, with no pod restart.
