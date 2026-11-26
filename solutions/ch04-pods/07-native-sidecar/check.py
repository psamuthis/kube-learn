# HINT: A native sidecar is an entry under `initContainers:` with `restartPolicy: Always` (on the container, not the pod).
# HINT: The pod-level `restartPolicy: Never` stays: it applies to the regular containers.


def check(k):
    job = k.get("job", "report")
    k.require(job is not None, "the Job `report` exists")
    spec = job["spec"]["template"]["spec"]
    side = {c["name"]: c for c in spec.get("initContainers", [])}
    k.expect("shipper" in side and side["shipper"].get("restartPolicy") == "Always",
             "shipper is an init container with restartPolicy: Always")
    k.expect([c["name"] for c in spec["containers"]] == ["main"], "the only regular container is `main`")
    done = k.wait("job/report", "condition=Complete", timeout=90)
    k.require(done, "the Job completes", k.kubectl("describe", "job", "report")[-1000:])
    pod = k.pods("job-name=report")[0]["metadata"]["name"]
    logs = k.kubectl("logs", pod, "-c", "shipper")
    k.expect(all(f"line {i}" in logs for i in range(1, 6)), "the shipper's logs contain the 5 lines", logs[-300:])
