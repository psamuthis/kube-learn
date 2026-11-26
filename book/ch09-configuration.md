# Chapter 9 — Configuration: ConfigMaps, Secrets and the downward API

> **Reading time:** ~35 min · **Exercises:** `exercises/ch09-configuration/` (5)

Images should be **built once and promoted** through environments unchanged. Everything that
differs between dev and prod (URLs, feature flags, credentials, tuning) is injected at run time.
Kubernetes gives you three sources: **ConfigMaps** (plain config), **Secrets** (sensitive config)
and the **downward API** (facts about the pod itself). Each can be consumed as **environment
variables** or as **files**.

## 9.1 ConfigMaps

```yaml
apiVersion: v1
kind: ConfigMap
metadata: {name: shop-config}
data:
  LOG_LEVEL: info                  # simple keys, good for env vars
  FEATURE_CHECKOUT: "true"         # values are always strings: quote them
  app.properties: |                # whole files, good for volumes
    cache.ttl=300
    currency=EUR
```

Create them from the command line too:

```console
$ kubectl create configmap shop-config --from-literal=LOG_LEVEL=info --from-file=app.properties
$ kubectl create configmap nginx-conf --from-file=conf.d/            # one key per file
$ kubectl create configmap x --from-env-file=.env
```

Limits: 1 MiB per object (it's in etcd), and they aren't for large or binary blobs
(there's `binaryData` for small ones).

## 9.2 Consuming config as environment variables

```yaml
containers:
  - name: app
    env:
      - name: LOG_LEVEL                          # one key
        valueFrom:
          configMapKeyRef: {name: shop-config, key: LOG_LEVEL}
      - name: DB_PASSWORD
        valueFrom:
          secretKeyRef: {name: db-credentials, key: password}
      - name: GREETING
        value: "Hello $(USER_NAME)"              # $(VAR) expands earlier env vars
    envFrom:                                     # every key at once
      - configMapRef: {name: shop-config}
        prefix: SHOP_                            # optional
      - secretRef: {name: db-credentials}
```

* Env vars are read **once, at container start**. Changing the ConfigMap doesn't affect running
  pods: you need a rollout (`kubectl rollout restart`, or a template change).
* A missing ConfigMap or key keeps the pod in `CreateContainerConfigError`, unless
  `optional: true`.
* Keys that aren't valid env var names are skipped by `envFrom`.

## 9.3 Consuming config as files

```yaml
spec:
  containers:
    - name: app
      volumeMounts:
        - {name: config, mountPath: /etc/shop, readOnly: true}       # whole directory
        - {name: nginx, mountPath: /etc/nginx/conf.d/default.conf, subPath: default.conf}
  volumes:
    - name: config
      configMap:
        name: shop-config
        items:                                   # optional: pick keys and rename them
          - {key: app.properties, path: application.properties}
        defaultMode: 0444
    - name: nginx
      configMap: {name: nginx-conf}
```

* Each key becomes a file. Without `items`, every key is a file.
* **Mounted ConfigMaps update live.** The kubelet syncs changes within about a minute (its
  sync period plus a cache TTL), by atomically swapping a `..data` symlink. Your app must
  re-read the files (watch them, or re-read on SIGHUP). That's exercise 9.4.
* **…except with `subPath`**: a subPath mount is a bind mount of one file and **never updates**.
  It's convenient for dropping one file into an existing directory, but remember this trade-off.
* Mounting over a directory *hides* what the image had there.

**Projected volumes** combine several sources in one directory: configMap, secret, downwardAPI
and serviceAccountToken.

## 9.4 Secrets

```yaml
apiVersion: v1
kind: Secret
metadata: {name: db-credentials}
type: Opaque                         # or kubernetes.io/tls, kubernetes.io/dockerconfigjson, …
stringData:                          # write plain text here; the API stores it base64-encoded in `data`
  username: shop
  password: s3cr3t!
```

A Secret is a ConfigMap with a few extra protections, *not* a vault:

* **base64 is an encoding, not encryption**: `kubectl get secret db-credentials -o
  jsonpath='{.data.password}' | base64 -d` prints it. Anyone who can `get` Secrets in a namespace
  can read them, and so can anyone who can **create pods** there (mount it and print it). Treat
  `get secrets` and `create pods` as sensitive RBAC permissions (chapter 12).
* In etcd they're **plain** unless the API server has an `EncryptionConfiguration` (often KMS-backed
  in managed clusters). Exercise 2.2 showed this.
* What you do get: they're kept in **tmpfs** on nodes (never written to node disk), sent only to
  nodes running pods that use them, kept out of `kubectl describe` output, and given distinct RBAC.
* **Prefer files over env vars** for secrets: env vars leak into crash dumps, child processes,
  `/proc/<pid>/environ` and debug endpoints (kubeapp's `/env` masks them for exactly that reason).
  Restrict the file mode (`defaultMode: 0400`). Secret files are owned by root, so a non-root app
  needs `0440` plus a pod `securityContext.fsGroup` matching its group.
* Keep secrets **out of git**: generate them in CI, or use Sealed Secrets, SOPS, or the External
  Secrets Operator (syncs from Vault / AWS Secrets Manager / GCP Secret Manager), or mount them
  straight from a vault with the Secrets Store CSI driver.

## 9.5 The downward API

A pod can learn about itself without talking to the API server:

```yaml
env:
  - name: POD_NAME
    valueFrom: {fieldRef: {fieldPath: metadata.name}}
  - name: POD_NAMESPACE
    valueFrom: {fieldRef: {fieldPath: metadata.namespace}}
  - name: POD_IP
    valueFrom: {fieldRef: {fieldPath: status.podIP}}
  - name: NODE_NAME
    valueFrom: {fieldRef: {fieldPath: spec.nodeName}}
  - name: MEMORY_LIMIT
    valueFrom: {resourceFieldRef: {containerName: app, resource: limits.memory, divisor: 1Mi}}
volumes:
  - name: podinfo
    downwardAPI:
      items:
        - {path: labels, fieldRef: {fieldPath: metadata.labels}}          # file, updated live
        - {path: annotations, fieldRef: {fieldPath: metadata.annotations}}
```

Typical uses: put the pod name in logs and metrics, size thread pools or heaps from the
container's limits (the JVM's `-XX:MaxRAMPercentage`, `GOMEMLIMIT`), know the node for
locality.

## 9.6 Config change management

Because env-var config and many apps don't reload, a common pattern is to make config part of
the pod template, so that changing it triggers a rollout:

* **Immutable, versioned ConfigMaps**: `shop-config-v7` with `immutable: true` (also cheaper
  for the kubelet, which stops watching it). Change the name in the Deployment to roll out.
  Kustomize's `configMapGenerator` does this automatically with a content hash suffix
  (chapter 15).
* **Checksum annotation**: Helm charts often put `checksum/config: <sha256 of the ConfigMap>` on
  the pod template.

Either way you get a rolling update with probes, and you can roll back. Live-reloading files is
nicer for apps that support it, but nothing guards against a bad config hitting every pod at once.

## Exercises

| # | Name | What you practise |
|---|---|---|
| 9.1 | `configmap-env` | `configMapKeyRef`, `envFrom` with a prefix |
| 9.2 | `configmap-files` | mounting keys as files, renaming with `items` |
| 9.3 | `secrets` | `stringData`, a Secret mounted read-only, base64 |
| 9.4 | `hot-reload` | live updates of mounted config, and why `subPath` breaks them |
| 9.5 | `downward-api` | pod name, IP, node, limits and labels inside the container |
