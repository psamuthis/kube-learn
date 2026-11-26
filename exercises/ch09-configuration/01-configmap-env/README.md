# Exercise 9.1 — Config as environment variables

1. Write `configmap.yaml`: a ConfigMap `shop-config` with the keys
   `MESSAGE` = `configured by a ConfigMap`, `LOG_LEVEL` = `debug`, `FEATURE_CHECKOUT` = `true`.
2. In `deployment.yaml`:
   * set the env var `MESSAGE` from the key `MESSAGE` (`configMapKeyRef`);
   * import **all** keys of `shop-config` with the prefix `SHOP_` (`envFrom`).

kubeapp's `/` shows `MESSAGE`; `/env` lists every variable. Remember: env vars are only read at
start. After changing the ConfigMap alone, you'd need `kubectl rollout restart`.
