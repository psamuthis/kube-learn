# Exercise 7.1 — A ClusterIP Service

`deployment.yaml` runs two kubeapp pods with a container port **named** `http` (8080).

Write `service.yaml`: a Service `web` that listens on **port 80** and forwards to the pods'
`http` port **by name** (not by number: if the app's port changes, only the Deployment needs
editing).

Then explore:

```console
$ kubectl -n ex-7-1 get svc,endpointslices
$ kubectl -n ex-7-1 run -it --rm t --image=busybox:1.37 -- wget -qO- http://web/
```

The checker fetches `http://web/` and `http://web.ex-7-1.svc.cluster.local/` and expects both
pods to show up among the answers.
