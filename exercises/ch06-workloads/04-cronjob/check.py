

def check(k):
    cj = k.get("cronjob", "report")
    k.require(cj is not None, "a CronJob `report` exists")
    s = cj["spec"]
    k.expect_eq(s.get("schedule"), "*/5 * * * *", "schedule")
    k.expect_eq(s.get("timeZone"), "Europe/Paris", "timeZone")
    k.expect_eq(s.get("concurrencyPolicy"), "Forbid", "concurrencyPolicy")
    k.expect_eq(s.get("successfulJobsHistoryLimit"), 2, "successfulJobsHistoryLimit")
    k.expect_eq(s.get("failedJobsHistoryLimit"), 1, "failedJobsHistoryLimit")
    if k.solution and k.get("job", "report-manual") is None:
        k.kubectl("create", "job", "report-manual", "--from=cronjob/report")
    job = k.get("job", "report-manual")
    k.require(job is not None, "a Job `report-manual` exists", "kubectl create job … --from=cronjob/report")
    owners = [o.get("kind") for o in job["metadata"].get("ownerReferences", [])]
    k.expect(owners == ["CronJob"], "it was created from the CronJob", f"owners: {owners}")
    k.require(k.wait("job/report-manual", "condition=Complete", timeout=90), "report-manual completes")
    logs = k.kubectl("logs", "job/report-manual")
    k.expect("report generated at" in logs, "it printed the report line", logs[:200])
