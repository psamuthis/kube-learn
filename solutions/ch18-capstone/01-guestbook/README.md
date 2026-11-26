# Exercise 18.1 — The guestbook platform

The full specification is in **`book/ch18-capstone.md`**, section 18.2. Build it in:

```text
base/kustomization.yaml          + whatever files you want in base/
overlays/prod/kustomization.yaml + the Ingress and anything prod-specific
```

The checker runs `kubectl apply -k overlays/prod` into the namespace `ex-18-1` (labelled
`pod-security.kubernetes.io/enforce=restricted` by the setup), then grades the sections of 18.3.

Before the first check, create the TLS Secret:

```console
$ openssl req -x509 -newkey rsa:2048 -nodes -days 30 -keyout tls.key -out tls.crt \
    -subj "/CN=guestbook.ex18.kube-learn.test" -addext "subjectAltName=DNS:guestbook.ex18.kube-learn.test"
$ kubectl -n ex-18-1 create secret tls guestbook-tls --cert=tls.crt --key=tls.key
```

(The namespace exists after your first `./course check 18.1`, even if it fails.) Test by hand:

```console
$ IP=$(minikube -p kube-learn ip)
$ curl -k --resolve guestbook.ex18.kube-learn.test:443:$IP https://guestbook.ex18.kube-learn.test/guestbook -d 'hello!'
$ curl -k --resolve guestbook.ex18.kube-learn.test:443:$IP https://guestbook.ex18.kube-learn.test/guestbook
```

Use `./course hint 18.1` sparingly; most hints are pointers back to the chapter that covers it.
