# Exercise 0.2 — Your first Pod

Complete `pod.yaml` so that it describes a Pod that:

* is named `hello`, with the label `app: hello`;
* runs one container named `web` with the image `nginx:1.29`;
* declares `containerPort: 80`.

Then `./course check 0.2`. The checker applies your file into the namespace `ex-0-2`, waits
for the pod to be Ready, and fetches `http://<pod IP>/` from inside the cluster.

Afterwards, have a look around:

```console
$ kubectl -n ex-0-2 get pod hello -o wide
$ kubectl -n ex-0-2 describe pod hello      # read the Events at the bottom
$ kubectl -n ex-0-2 get pod hello -o yaml   # look at everything the system filled in (status, defaults…)
$ kubectl -n ex-0-2 logs hello
```
