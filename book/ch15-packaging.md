# Chapter 15 — Packaging: Kustomize and Helm

> **Reading time:** ~45 min · **Exercises:** `exercises/ch15-packaging/` (4)

Real apps are a dozen manifests, deployed to several environments that differ in a few
values: replicas, image tag, domain, resources. Copy-pasting YAML per environment rots fast.
The two standard answers:

* **Kustomize**: *patch* plain YAML. Template-free, built into kubectl (`kubectl apply -k`).
* **Helm**: *template* YAML with Go templates, packaged as versioned **charts**, installed as
  **releases**. It's also the ecosystem's distribution format: nearly every third-party component
  ships a chart.

Use Kustomize for your own apps when overlays are enough; use Helm to consume third-party software
and when you need real parametrisation or distribution. Many teams combine them.

## 15.1 Kustomize: bases and overlays

```text
app/
├── base/
│   ├── kustomization.yaml
│   ├── deployment.yaml
│   └── service.yaml
└── overlays/
    ├── dev/kustomization.yaml
    └── prod/
        ├── kustomization.yaml
        └── replicas-patch.yaml
```

```yaml
# base/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - deployment.yaml
  - service.yaml
labels:
  - pairs: {app.kubernetes.io/name: shop}
    includeSelectors: true          # also add to selectors and pod templates
```

```yaml
# overlays/prod/kustomization.yaml
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - ../../base
namePrefix: prod-
labels:
  - pairs: {env: prod}
images:
  - name: kubeapp                   # rewrite every image named kubeapp…
    newTag: "2.0"                   # …to this tag (or newName:, digest:)
replicas:
  - {name: shop, count: 3}
configMapGenerator:
  - name: shop-config
    literals: [LOG_LEVEL=warn, FEATURE_CHECKOUT=true]
patches:
  - path: replicas-patch.yaml       # a strategic-merge patch (partial YAML)
  - target: {kind: Deployment, name: shop}
    patch: |-                       # a JSON 6902 patch
      - op: add
        path: /spec/template/spec/containers/0/env/-
        value: {name: ENV, value: prod}
```

```console
$ kubectl kustomize overlays/prod          # render: always look before you apply
$ kubectl apply -k overlays/prod
$ kubectl diff -k overlays/prod
```

Key ideas:

* **Bases are complete and valid on their own**; overlays only state differences.
* **Generators** (`configMapGenerator`, `secretGenerator`) add a **content hash** to the name
  (`shop-config-7g2f9k4m5t`) and rewrite references to it. Changing config then changes the pod
  template, which triggers a rollout. That fixes the "config change without restart" problem from
  chapter 9.
* **Strategic-merge patches** are partial YAML merged by key (containers merge by `name`).
  **JSON 6902 patches** are precise operations (`add`/`replace`/`remove` at a path) for what
  merge can't express.
* `namePrefix`/`nameSuffix` and `namespace` rewrite names and references consistently.
* `components` are reusable optional pieces (e.g. "add monitoring").

## 15.2 Helm: charts, values, releases

```text
mychart/
├── Chart.yaml            # name, version (of the chart), appVersion (of the app)
├── values.yaml           # default parameters
├── values.schema.json    # optional: JSON-schema validation of values
├── templates/
│   ├── _helpers.tpl      # named template snippets
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── NOTES.txt         # printed after install
│   └── tests/            # `helm test` pods
└── charts/               # dependencies (subcharts)
```

```yaml
# Chart.yaml
apiVersion: v2
name: kubeapp
version: 0.1.0
appVersion: "1.0"
```

```yaml
# values.yaml
replicaCount: 2
image:
  repository: kubeapp
  tag: ""                 # defaults to .Chart.AppVersion
message: hello from helm
ingress:
  enabled: false
  host: ""
resources:
  requests: {cpu: 10m, memory: 32Mi}
```

```yaml
# templates/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ include "kubeapp.fullname" . }}
  labels:
    {{- include "kubeapp.labels" . | nindent 4 }}
spec:
  replicas: {{ .Values.replicaCount }}
  selector:
    matchLabels:
      {{- include "kubeapp.selectorLabels" . | nindent 6 }}
  template:
    metadata:
      labels:
        {{- include "kubeapp.selectorLabels" . | nindent 8 }}
      annotations:
        checksum/config: {{ include (print $.Template.BasePath "/configmap.yaml") . | sha256sum }}
    spec:
      containers:
        - name: app
          image: "{{ .Values.image.repository }}:{{ .Values.image.tag | default .Chart.AppVersion }}"
          env:
            - name: MESSAGE
              value: {{ .Values.message | quote }}
          resources:
            {{- toYaml .Values.resources | nindent 12 }}
```

```yaml
# templates/ingress.yaml: conditional resources
{{- if .Values.ingress.enabled }}
apiVersion: networking.k8s.io/v1
kind: Ingress
...
{{- end }}
```

The template language in five lines: `{{ .Values.x }}` (values), `.Release.Name`,
`.Release.Namespace`, `.Chart.Name` (built-ins); pipelines `| default "x" | quote | upper`;
`{{- … -}}` trims whitespace; `if/else`, `range`, `with`; `include "name" .` plus `nindent N`
for snippets; `toYaml`, `required "msg" .Values.x`, `lookup`, `tpl`. **YAML indentation is the
#1 source of Helm bugs**: render and read the output.

```console
$ helm create mychart                          # a scaffold with best practices
$ helm lint mychart
$ helm template web ./mychart -f prod.yaml     # render locally (no cluster)
$ helm install web ./mychart -n shop --create-namespace --set replicaCount=3
$ helm upgrade --install web ./mychart -f prod.yaml   # idempotent: use this in CI
$ helm list -n shop; helm history web -n shop
$ helm rollback web 1 -n shop
$ helm uninstall web -n shop
$ helm repo add bitnami https://charts.bitnami.com/bitnami; helm search repo redis
$ helm install cache oci://registry-1.docker.io/bitnamicharts/redis --version 20.x
```

A **release** is one installation of a chart (name + namespace). Helm stores each revision in a
Secret in the release namespace (`sh.helm.release.v1.web.v3`), which is what `history` and
`rollback` read. Values are merged with this precedence: chart defaults < `-f` files (in order) <
`--set`.

## 15.3 GitOps, briefly

Both tools render manifests; something has to apply them. **GitOps** controllers (Argo CD,
Flux) watch a git repository and continuously reconcile the cluster to it: the chapter 2
pattern applied to your whole deployment process. They natively understand Kustomize
directories and Helm charts. Rollback becomes `git revert`, and drift (someone ran `kubectl edit`)
gets detected and corrected.

## Exercises

| # | Name | What you practise |
|---|---|---|
| 15.1 | `kustomize-base` | a base with common labels |
| 15.2 | `kustomize-overlays` | dev and prod overlays: prefix, image tag, replicas, generated config |
| 15.3 | `kustomize-patches` | strategic-merge and JSON 6902 patches |
| 15.4 | `helm-chart` | write a chart with values, helpers and a conditional Ingress |
