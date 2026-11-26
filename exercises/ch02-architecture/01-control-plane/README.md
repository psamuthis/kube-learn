# Exercise 2.1 — Meet the control plane

Explore your cluster's control plane and fill in `answers.txt`. Nothing to apply.

Useful places:

```console
$ kubectl -n kube-system get pods -o wide
$ kubectl get node kube-learn -o yaml                 # status.nodeInfo
$ kubectl -n kube-system get leases
$ minikube -p kube-learn ssh                          # a shell on the control-plane node, then:
    sudo cat /var/lib/kubelet/config.yaml
    ls /etc/kubernetes/manifests/
    sudo cat /etc/kubernetes/manifests/kube-apiserver.yaml
    sudo cat /etc/kubernetes/manifests/etcd.yaml
```
