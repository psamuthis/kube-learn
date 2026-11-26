# Exercise 2.3 — The API, raw

kubectl is just an HTTP client. Create a ConfigMap **without kubectl create/apply**, using only
`curl` against the API through `kubectl proxy`.

1. In one terminal: `kubectl proxy --port 8001` (it handles authentication for you).
2. Complete `create.sh`: it must `POST` a JSON ConfigMap named `made-by-curl` with the data
   `greeting: hello` and `language: http` into the namespace `ex-2-3`.
3. Run `./course check 2.3` once (it creates the namespace), then `bash create.sh`, then check again.

The checker verifies that the object exists and that its `managedFields` show it was written by
`curl` (the API server records each writer's User-Agent as the field manager).

Bonus: `curl -s "localhost:8001/api/v1/namespaces/ex-2-3/configmaps?watch=true"` in another
terminal while you run it, then `kubectl -n ex-2-3 delete cm made-by-curl` and watch the events
stream in.
