# Exercise 10.5 — Postgres on a StatefulSet

Write `postgres.yaml` with three objects:

1. A Secret `pg` with `POSTGRES_PASSWORD` = `kube-learn` (use `stringData`).
2. A headless Service `pg` (port 5432, selector `app: pg`).
3. A StatefulSet `pg`, 1 replica, image `postgres:17-alpine`:
   * all env vars from the Secret (`envFrom`), plus `PGDATA=/var/lib/postgresql/data/pgdata`
     (a subdirectory of the mount, as postgres requires);
   * a **readiness probe** that runs `pg_isready -U postgres` (an `exec` probe);
   * a `volumeClaimTemplates` entry `data` (RWO, 500Mi, `local-path`) mounted at
     `/var/lib/postgresql/data`;
   * requests 50m CPU and 128Mi memory.

The checker creates a table and inserts a row through `psql`, deletes the pod `pg-0`, and
expects the row to still be there in the new `pg-0`.
