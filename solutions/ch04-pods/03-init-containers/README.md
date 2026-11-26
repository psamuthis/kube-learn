# Exercise 4.3 — Init containers

`pod.yaml` runs kubeapp and shows its config directory (`/config`) at `/config`. Add two **init
containers**, in this order:

1. `wait-for-db` (`busybox:1.37`): loops until the Service name resolves in DNS
   (`until nslookup db.ex-4-3.svc.cluster.local; do echo waiting; sleep 2; done`).
   Use the full name: busybox's `nslookup` returns an error when *any* of the DNS search
   domains fails, even if one succeeded;
2. `render-config` (`busybox:1.37`): writes the line `database=db.ex-4-3.svc.cluster.local`
   to `/config/settings.txt`.

The `/config` directory must be an `emptyDir` volume shared between `render-config` and the app.

The checker does the applying itself, in two steps: first only `pod.yaml` (the pod must stay in
`Init:0/2`, since there's no `db` yet), then `db-service.yaml` (and then the pod must become
Ready and serve the rendered file on `/config`).
