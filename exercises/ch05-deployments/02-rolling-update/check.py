import subprocess
import time

from kube import container



def check(k):
    d = k.get("deployment", "web")
    s = d["spec"]
    ru = s.get("strategy", {}).get("rollingUpdate", {})
    k.expect(str(ru.get("maxSurge")) == "1" and str(ru.get("maxUnavailable")) == "0", "maxSurge 1, maxUnavailable 0",
             f"got {ru}")
    k.expect_eq(s.get("minReadySeconds"), 3, "minReadySeconds")
    k.expect_eq(container(d)["image"], "kubeapp:2.0", "the image")
    k.expect_eq(d["metadata"].get("annotations", {}).get("kubernetes.io/change-cause"), "upgrade to 2.0", "change-cause")
    k.require(k.rollout("web", timeout=180), "the rollout to 2.0 completes")
    hist = k.kubectl("rollout", "history", "deployment/web")
    k.expect("upgrade to 2.0" in hist, "`rollout history` shows the change cause", hist)
    k.info("restarting the rollout and sampling availability…")
    k.kubectl("rollout", "restart", "deployment/web")
    low, samples = 99, 0
    proc = subprocess.Popen(["kubectl", "-n", k.ns, "rollout", "status", "deployment/web", "--timeout=180s"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    while proc.poll() is None:
        avail = k.jp("deployment", "web", "{.status.availableReplicas}")
        low = min(low, int(avail or 0))
        samples += 1
        time.sleep(0.5)
    k.expect(proc.returncode == 0, "the restart rollout completes")
    k.expect(low >= 3, f"available pods never dropped below 3 ({samples} samples)", f"lowest seen: {low}")
