

def check(k):
    job = k.get("job", "squares")
    k.require(job is not None, "a Job `squares` exists")
    k.expect_eq(job["spec"].get("completionMode"), "Indexed", "completionMode")
    k.expect_eq(job["spec"].get("completions"), 5, "completions")
    k.expect_eq(job["spec"].get("parallelism"), 5, "parallelism")
    k.require(k.wait("job/squares", "condition=Complete", timeout=120), "the Job completes")
    seen = {}
    for p in k.pods("job-name=squares"):
        if p["status"].get("phase") != "Succeeded":
            continue
        idx = p["metadata"]["annotations"].get("batch.kubernetes.io/job-completion-index")
        seen[idx] = k.kubectl("logs", p["metadata"]["name"]).strip()
    for i in range(5):
        k.expect(seen.get(str(i)) == f"index={i} square={i * i}", f"pod {i} printed `index={i} square={i * i}`",
                 f"got {seen.get(str(i))!r}")
