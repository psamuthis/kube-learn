# Exercise 12.5 — NetworkPolicy: ingress

`backend.yaml` runs a `backend` Deployment and Service (port 80 → 8080). The checker starts two
client pods in the namespace: one labelled `app: frontend` and one labelled `app: intruder`.
Right now both can reach the backend.

Write `netpol.yaml` with two policies:

1. `default-deny-ingress`: no pod in the namespace accepts any ingress traffic, by default;
2. `backend-from-frontend`: the backend accepts traffic **from `app: frontend` pods only**, on
   **TCP 8080** only.

Try it yourself:

```console
$ kubectl -n ex-12-5 exec frontend -- wget -qO- -T 3 http://backend/
$ kubectl -n ex-12-5 exec intruder -- wget -qO- -T 3 http://backend/     # must time out
```
(The client pods exist after the first `./course check 12.5`.)
