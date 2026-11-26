# Exercise 3.5 — Sharing an object: server-side apply

Two teams manage the same Deployment `web`:

* **team-platform** owns the replica count and the resources. The setup applied that part with
  `--server-side --field-manager=team-platform`.
* **team-app** (you) owns the image, and only the image.

1. Look at who owns what: `kubectl -n ex-3-5 get deploy web -o yaml --show-managed-fields`.
2. Write `image.yaml`: a **partial** Deployment containing only what team-app owns (apiVersion,
   kind, metadata.name, and the container `kubeapp` with image `kubeapp:2.0`).
3. Apply it as team-app:

   ```console
   $ kubectl -n ex-3-5 apply --server-side --field-manager=team-app -f image.yaml
   ```

   You get a **conflict**: team-platform's apply also set the image. Read the error, then take
   ownership of that field on purpose (look at the flags the error suggests).

The checker doesn't apply anything here; it checks the result. The image must be `kubeapp:2.0`,
team-app must own the image field, and team-platform must still own `replicas`. Your apply
must not have touched anything else.
