# Exercise 7.2 — The Service that doesn't work

`app.yaml` contains a Deployment `api` and a Service `api`. `http://api/` doesn't answer.
Find out why with the debugging method from section 7.6:

```console
$ kubectl -n ex-7-2 get svc api -o wide
$ kubectl -n ex-7-2 get endpointslices -l kubernetes.io/service-name=api
$ kubectl -n ex-7-2 get pods --show-labels
$ kubectl -n ex-7-2 get pod <pod> -o jsonpath='{.spec.containers[0].ports}'
```

Fix the **Service** (not the Deployment) so that `http://api/` works. There are two bugs.
