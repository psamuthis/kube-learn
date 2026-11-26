# Exercise 6.2 — A batch Job

Write `job.yaml`: a Job `crunch` that

* needs **6 successful completions**, running **at most 2 pods at a time**;
* gives up after **3** failed pods;
* is deleted automatically **10 minutes** after it finishes;
* uses `restartPolicy: Never`;
* runs `busybox:1.37` with `sh -c 'echo "crunching on $(hostname)"; sleep 2'`.

Watch it: `kubectl -n ex-6-2 get pods -w`. Jobs are immutable: use `--fresh` after editing.
