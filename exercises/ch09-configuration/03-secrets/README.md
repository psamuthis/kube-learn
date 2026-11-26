# Exercise 9.3 — Secrets

1. Write `secret.yaml`: a Secret `db-credentials` (type `Opaque`), using `stringData`, with
   `username` = `shop` and `password` = `hunter2`. (In real life you'd never commit this file.)
2. In `deployment.yaml`:
   * set the env var `DB_USER` from the key `username` (`secretKeyRef`);
   * mount the whole Secret **read-only** at `/secrets`, with file mode **0440**;
   * kubeapp runs as UID/GID 10001, and Secret files are owned by root. Set the pod's
     `securityContext.fsGroup: 10001` so the files' *group* is 10001 and the app can read them.
3. Fill in `answers.txt`.

Then try it: `kubectl -n ex-9-3 get secret db-credentials -o yaml`. Is the password hidden?
