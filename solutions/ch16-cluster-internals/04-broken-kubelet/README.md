# Exercise 16.4 — A broken node

The setup broke something on **kube-learn-m03**. After a minute, it goes `NotReady`:

```console
$ kubectl get nodes
$ kubectl describe node kube-learn-m03          # Conditions, and the last heartbeat time
```

Find out why **on the node**, and repair it:

```console
$ minikube -p kube-learn ssh -n kube-learn-m03
$ sudo systemctl status kubelet
$ sudo journalctl -u kubelet --no-pager -n 50
```

The fix is an edit of one file plus a `systemctl restart kubelet`. Fill in `answers.txt` too.
`./course clean 16.4` (or `--fresh`) restores the node from the setup's backup if you get lost.
