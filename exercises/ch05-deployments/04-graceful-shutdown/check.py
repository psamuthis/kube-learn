import time

from kube import container, pod_spec



def check(k):
    d = k.get("deployment", "web")
    c = container(d)
    k.expect_eq(pod_spec(d).get("terminationGracePeriodSeconds"), 20, "terminationGracePeriodSeconds")
    k.expect_eq(c.get("lifecycle", {}).get("preStop", {}).get("sleep", {}).get("seconds"), 5, "preStop sleep seconds")
    env = {e["name"]: e.get("value") for e in c.get("env", [])}
    k.expect_eq(env.get("SHUTDOWN_DELAY"), "3", "SHUTDOWN_DELAY")
    k.require(k.rollout("web"), "the rollout completes")
    pod = k.ready_pods("app=web")[0]["metadata"]["name"]
    t0 = time.time()
    k.kubectl("delete", "pod", pod, "--wait=false")
    gone = k.wait_for(lambda: k.get("pod", pod) is None, timeout=40, interval=0.5)
    took = time.time() - t0
    k.require(gone, "the pod eventually terminates")
    k.expect(8 <= took < 19, "termination takes between 8 and 19 seconds", f"it took {took:.1f} s")
