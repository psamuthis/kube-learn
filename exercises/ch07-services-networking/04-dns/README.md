# Exercise 7.4 — Cluster DNS

`deployment.yaml` and `service.yaml` give you a Service `web` (port named `http`, 80 → 8080).
Investigate DNS from a pod in the namespace:

```console
$ kubectl -n ex-7-4 run -it --rm t --image=busybox:1.37 -- sh
/ # cat /etc/resolv.conf
/ # nslookup web.ex-7-4.svc.cluster.local
/ # nslookup -type=srv _http._tcp.web.ex-7-4.svc.cluster.local
```

and fill in `answers.txt`.
