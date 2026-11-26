# Exercise 10.1 — What an emptyDir survives

kubeapp's `/hits` endpoint counts requests in the file `$DATA_DIR/hits` when `DATA_DIR` is set.

1. Complete `deployment.yaml`: an `emptyDir` volume named `data` mounted at `/data`, and the env var
   `DATA_DIR=/data`.
2. Experiment, then fill in `answers.txt`:

```console
$ kubectl -n ex-10-1 port-forward deploy/counter 8080:8080 &
$ curl localhost:8080/hits; curl localhost:8080/hits     # 1, 2
$ curl localhost:8080/crash                              # the container exits and is restarted
$ curl localhost:8080/hits                               # ? (restart the port-forward if needed)
$ kubectl -n ex-10-1 delete pod -l app=counter           # a brand-new pod
$ curl localhost:8080/hits                               # ?
```
