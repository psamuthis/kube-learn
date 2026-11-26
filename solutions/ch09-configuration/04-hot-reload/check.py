import json
import time

# HINT: A `subPath` mount is a bind mount of a single file, frozen at container start. Mount the whole volume as a directory instead.


def files(k, ip):
    return json.loads(k.http(f"http://{ip}:8080/config")[1]).get("files", {})


def check(k):
    k.kubectl("apply", "-f", str(k.dir / "configmap.yaml"))  # reset to version 1
    k.require(k.rollout("greeter"), "the Deployment is rolled out")
    m = k.get("deployment", "greeter")["spec"]["template"]["spec"]["containers"][0]["volumeMounts"][0]
    k.expect("subPath" not in m, "the ConfigMap isn't mounted with subPath")
    pod = k.ready_pods("app=greeter")[0]
    name, ip = pod["metadata"]["name"], pod["status"]["podIP"]
    k.expect(k.wait_for(lambda: files(k, ip).get("greeting.txt", "").strip() == "hello, version 1", timeout=60),
             "/config/greeting.txt says version 1")
    stamp = f"hello, version 2 ({int(time.time())})"
    k.kubectl("patch", "configmap", "live", "-p", json.dumps({"data": {"greeting.txt": stamp}}))
    k.info("updated the ConfigMap; waiting for the kubelet to sync (up to 90 s)…")
    t0 = time.time()
    ok = k.wait_for(lambda: files(k, ip).get("greeting.txt", "").strip() == stamp, timeout=90, interval=3)
    k.expect(ok, "the running pod sees the new content", f"after {time.time() - t0:.0f} s")
    if ok:
        k.info(f"propagated in {time.time() - t0:.0f} s")
    k.expect(k.jp("pod", name, "{.status.containerStatuses[0].restartCount}") == "0", "without restarting the container")
