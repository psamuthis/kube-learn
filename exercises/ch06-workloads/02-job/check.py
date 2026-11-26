

def check(k):
    job = k.get("job", "crunch")
    k.require(job is not None, "a Job `crunch` exists")
    s = job["spec"]
    k.expect_eq(s.get("completions"), 6, "completions")
    k.expect_eq(s.get("parallelism"), 2, "parallelism")
    k.expect_eq(s.get("backoffLimit"), 3, "backoffLimit")
    k.expect_eq(s.get("ttlSecondsAfterFinished"), 600, "ttlSecondsAfterFinished")
    k.expect_eq(s["template"]["spec"].get("restartPolicy"), "Never", "restartPolicy")
    k.require(k.wait("job/crunch", "condition=Complete", timeout=120), "the Job completes")
    k.expect_eq(k.get("job", "crunch")["status"].get("succeeded"), 6, "succeeded pods")
    pods = k.pods("job-name=crunch")
    starts = sorted(p["status"].get("startTime", "") for p in pods)
    k.expect(len(pods) >= 6, f"{len(pods)} pods ran")
    logs = k.kubectl("logs", "-l", "job-name=crunch", "--tail=1")
    k.expect(logs.count("crunching on crunch-") >= 6, "every pod logged its work", logs[:300])
