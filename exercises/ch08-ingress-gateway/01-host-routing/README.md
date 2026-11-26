# Exercise 8.1 — Host-based routing

`apps.yaml` runs two apps, each behind a Service: `blue` and `green` (port named `http`).
Write `ingress.yaml`: one Ingress `colors` (class `nginx`) that routes

* `blue.ex81.kube-learn.test` → Service `blue`,
* `green.ex81.kube-learn.test` → Service `green`,

for every path. Test it from your machine:

```console
$ curl -H 'Host: blue.ex81.kube-learn.test' http://$(minikube -p kube-learn ip)/
```

(The ingress controller is shared by the whole cluster, which is why the host names include the
exercise number.)
