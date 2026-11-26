# Exercise 7.3 — NodePort: in from the outside

Write `service.yaml`: a Service `web` of type **NodePort** that exposes the pods' `http` port on
port **30080** of every node.

Then, from **your machine** (not from a pod):

```console
$ minikube -p kube-learn ip                       # the control-plane node's IP
$ curl http://$(minikube -p kube-learn ip):30080/
$ kubectl get nodes -o wide                       # every node's INTERNAL-IP works, try another one
```

The checker connects from your machine to port 30080 of **each** node.
