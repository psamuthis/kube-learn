# Exercise 1.2 — Inside an image

The course image `kubeapp:1.0` was built on your machine by `./course cluster images` (see
`apps/kubeapp/Dockerfile`). Use `docker image inspect kubeapp:1.0` and `docker history kubeapp:1.0`
to fill in `answers.txt`. Nothing to apply.

Bonus: `docker save kubeapp:1.0 -o /tmp/k.tar && tar -tf /tmp/k.tar` shows the raw OCI layout
(an index, a manifest, a config blob and one tarball per layer).
