# Exercise 15.4 — Write a Helm chart

Finish the chart in `chart/` for kubeapp. `Chart.yaml` and `values.yaml` are written; complete
the templates:

* `templates/_helpers.tpl`: define `kubeapp.fullname` (`<release name>-<chart name>`),
  `kubeapp.selectorLabels` (`app.kubernetes.io/name` and `app.kubernetes.io/instance`) and
  `kubeapp.labels` (selector labels + `app.kubernetes.io/version` + `helm.sh/chart`);
* `templates/deployment.yaml`: replicas, image (`repository:tag`, tag defaulting to the chart's
  `appVersion`), the env var `MESSAGE` from `.Values.message`, resources from `.Values.resources`;
* `templates/service.yaml`: port 80 → the container's `http` port;
* `templates/ingress.yaml`: **only if** `ingress.enabled`, routing `ingress.host` to the Service.

You need **Helm**: `sudo pacman -S helm`, or the checker falls back to the `alpine/helm` Docker
image. Try:

```console
$ helm lint chart
$ helm template web chart --set ingress.enabled=true,ingress.host=x.test | less
$ helm install web chart -n ex-15-4 --set replicaCount=3      # and helm list / history / uninstall
```

The checker lints the chart, renders it as release `web` with
`replicaCount=3, message="hi from helm", ingress.enabled=true, ingress.host=chart.ex154.kube-learn.test`,
applies the result, and fetches the page through the Ingress. It also checks that the default
values render **no** Ingress.
