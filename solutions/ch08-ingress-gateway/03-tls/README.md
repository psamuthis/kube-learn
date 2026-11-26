# Exercise 8.3 — HTTPS

Serve `app.yaml`'s Service `secure` over HTTPS at `secure.ex83.kube-learn.test`.

1. Create a self-signed certificate for that host name with `openssl` (section 8.4), and store it
   in a TLS Secret named **`secure-tls`** in `ex-8-3`
   (`kubectl -n ex-8-3 create secret tls …`). Keep the key out of git!
2. Write `ingress.yaml`: an Ingress `secure` that routes the host to the Service and terminates
   TLS with that Secret.

```console
$ curl -kv --resolve secure.ex83.kube-learn.test:443:$(minikube -p kube-learn ip) https://secure.ex83.kube-learn.test/
```

The checker verifies that the controller presents *your* certificate (not its fake default one),
that HTTPS works, and that plain HTTP is redirected to HTTPS.
