# Exercise 2.2 — Inside etcd

The setup step created a ConfigMap `plans` and a Secret `launch` in the namespace `ex-2-2`.
Find them in etcd, the database behind the API server.

etcd runs as a static pod on the control-plane node, and its image contains `etcdctl`.
etcd only accepts TLS clients, so you need the certificates mounted in the pod (look at the
`etcd` pod's spec to find their paths):

```console
$ kubectl -n kube-system exec etcd-kube-learn -- etcdctl \
    --endpoints=https://127.0.0.1:2379 \
    --cacert=<etcd CA> --cert=<a client cert> --key=<its key> \
    get / --prefix --keys-only | head
```

Then answer `answers.txt`. (Values are stored as protobuf, so `get` prints some binary; that's
normal. `-w json` shows the metadata etcd keeps per key, with the value in base64.)
