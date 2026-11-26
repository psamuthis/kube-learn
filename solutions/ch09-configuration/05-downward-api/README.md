# Exercise 9.5 — The downward API

Complete `deployment.yaml` so that the container gets:

| Env var | From |
|---|---|
| `POD_NAME` | the pod's name |
| `POD_NAMESPACE` | its namespace |
| `POD_IP` | its IP |
| `NODE_NAME` | the node it runs on |
| `MEMORY_LIMIT_MI` | the container's memory limit, **in MiB** (the limit is 96Mi, so the value must be `96`) |

and a `downwardAPI` volume mounted at `/config/podinfo` with a file `labels` containing the
pod's labels.

kubeapp's `/env` and `/config` let the checker see all of it.
