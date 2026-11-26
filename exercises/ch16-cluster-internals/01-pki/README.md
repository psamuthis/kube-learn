# Exercise 16.1 — The cluster's PKI

Inspect the certificates (section 16.2) and fill in `answers.txt`. Useful commands:

```console
$ minikube -p kube-learn ssh -- sudo ls /var/lib/minikube/certs/
$ minikube -p kube-learn ssh -- sudo openssl x509 -in /var/lib/minikube/certs/apiserver.crt -noout -text
$ kubectl config view --minify          # where's *your* client certificate?
$ openssl x509 -in <it> -noout -subject
$ kubectl auth whoami
$ minikube -p kube-learn ssh -n kube-learn-m02 -- sudo openssl x509 -in /var/lib/kubelet/pki/kubelet-client-current.pem -noout -subject
```
