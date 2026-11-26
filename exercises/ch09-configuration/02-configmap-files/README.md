# Exercise 9.2 — Config as files

kubeapp's `/config` endpoint lists every file under `/config` with its content.

1. Write `configmap.yaml`: a ConfigMap `files` with two keys:
   * `app.properties`, a multi-line value:
     ```
     cache.ttl=300
     currency=EUR
     ```
   * `motd.txt` = `Welcome to the shop`
2. In `deployment.yaml`, mount it read-only at `/config` so that the files appear as
   `/config/settings/application.properties` (from `app.properties`) and `/config/motd`
   (from `motd.txt`).
