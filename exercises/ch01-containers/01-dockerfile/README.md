# Exercise 1.1 — Write a Dockerfile

`hello.py` is a tiny HTTP server (standard library only) listening on port 8000.

Write a `Dockerfile` in this directory that:

* starts from a **small** Python base image (the final image must be under 150 MB, so `python:3.13`
  at ~1 GB won't do; look at the `-alpine` or `-slim` variants);
* copies `hello.py` in;
* runs as a **non-root numeric user** (`USER 10001`);
* starts the server with the **exec form** of `ENTRYPOINT`/`CMD`.

The checker builds it as `hello-ch01:1.0` with your local Docker, loads it onto the cluster's
nodes, applies `pod.yaml` (already written, have a look at `imagePullPolicy`), and fetches
`http://<pod IP>:8000/`.
