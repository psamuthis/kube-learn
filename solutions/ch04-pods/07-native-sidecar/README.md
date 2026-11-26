# Exercise 4.7 — A native sidecar in a Job

`job.yaml` runs a Job whose main container writes 5 log lines to a file and exits. A
**log-shipper** sidecar should `tail -F` that file (so the lines end up in `kubectl logs`).

Old-style sidecars (a second regular container) never exit, so the Job never completes. Turn
`shipper` into a **native sidecar**: move it into `initContainers` and give it
`restartPolicy: Always`. Kubernetes then starts it first and stops it when the main container
is done.

The checker expects the Job to **complete**, and the shipper's logs to contain the 5 lines.
Jobs are immutable: after editing, `./course check 4.7 --fresh`.
