import time

from kube import container, mem_bytes

# HINT: `kubectl describe pod` → "Last State: Terminated  Reason: …  Exit Code: …".
# HINT: Exit codes above 128 mean "killed by signal (code − 128)". Signal 9 is SIGKILL.
# HINT: The program needs ~100 MiB plus the Python interpreter itself (~10 MiB): a 64Mi limit can never work.


def check(k):
    a = k.answers()
    k.expect_eq(a.get("reason"), "OOMKilled", "reason")
    k.expect_eq(a.get("exit_code"), "137", "exit_code")
    k.expect_eq(a.get("signal"), "9", "signal")
    lim = container(k.get("deployment", "hog")).get("resources", {}).get("limits", {}).get("memory", "0")
    k.expect(128 * 2**20 <= mem_bytes(lim) <= 256 * 2**20, "the memory limit is between 128Mi and 256Mi", f"it is {lim}")
    k.require(k.rollout("hog", timeout=90), "the rollout completes")
    time.sleep(5)
    pods = k.ready_pods("app=hog")
    k.require(pods, "a hog pod is Running")
    st = pods[0]["status"]["containerStatuses"][0]
    k.expect(st.get("restartCount", 0) == 0 and "running" in st.get("state", {}), "it stays up (no restarts)")
    logs = k.kubectl("logs", pods[0]["metadata"]["name"])
    k.expect("allocated 100 MiB" in logs, "it managed to allocate its 100 MiB", logs[-300:])
