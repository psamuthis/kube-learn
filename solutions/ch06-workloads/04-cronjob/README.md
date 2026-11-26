# Exercise 6.4 — A CronJob

1. Write `cronjob.yaml`: a CronJob `report` that
   * runs **every 5 minutes**, in the **Europe/Paris** time zone;
   * never runs two at once (if the previous one is still running, **skip**);
   * keeps **2** successful and **1** failed Job in its history;
   * runs `busybox:1.37` with `sh -c 'echo "report generated at $(date)"'`, `restartPolicy: OnFailure`.
2. You don't want to wait 5 minutes to know it works: trigger it by hand, creating a Job named
   **`report-manual`** from the CronJob (one kubectl command).

Then `./course check 6.4`.
