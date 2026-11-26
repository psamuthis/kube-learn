# Exercise 4.1 — A complete pod spec

Complete `pod.yaml`: a Pod `app` running `kubeapp:1.0` that

* has the labels `app: kubeapp` and `tier: demo`;
* listens on port **9090** instead of the default 8080 (kubeapp reads the `PORT` env var), and
  declares that port with the **name** `http`;
* sets the env vars `MESSAGE` = `hello pods` and `COLOR` = `purple`;
* overrides the image's entrypoint with `command: ["python", "-u", "/app/app.py"]`.

The checker fetches `http://<pod IP>:9090/` and looks at the JSON.

Pods are mostly immutable: if `kubectl apply` refuses your change, use `./course check 4.1 --fresh`.
