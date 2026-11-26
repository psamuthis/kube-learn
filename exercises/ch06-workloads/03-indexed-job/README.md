# Exercise 6.3 — An Indexed Job

Complete `job.yaml`: an **Indexed** Job `squares` with 5 completions, all 5 running in parallel.
Each pod must print exactly one line,

```text
index=<i> square=<i*i>
```

using the `JOB_COMPLETION_INDEX` env var that Kubernetes sets in indexed pods (busybox `sh` can
compute: `$((JOB_COMPLETION_INDEX * JOB_COMPLETION_INDEX))`).

Use `--fresh` after editing (Jobs are immutable).
