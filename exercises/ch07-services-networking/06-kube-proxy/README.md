# Exercise 7.6 — Inside kube-proxy

`deployment.yaml` + `service.yaml` give you a Service `web` with 2 endpoints. Find out how
packets to its ClusterIP get to a pod. On a node:

```console
$ minikube -p kube-learn ssh -n kube-learn-m02
$ sudo iptables-save -t nat | grep 'ex-7-6/web'
$ sudo iptables-save -t nat | grep -A5 '^-A KUBE-SVC-<…>'
```

Also look at kube-proxy itself: `kubectl -n kube-system logs -l k8s-app=kube-proxy | head`
and `kubectl -n kube-system get cm kube-proxy -o yaml`.

Fill in `answers.txt`.
