import json



def check(k):
    k.require(k.rollout("whoami"), "the Deployment is rolled out")
    pod = k.ready_pods("app=whoami")[0]
    ip = pod["status"]["podIP"]
    env = json.loads(k.http(f"http://{ip}:8080/env")[1])
    k.expect_eq(env.get("POD_NAME"), pod["metadata"]["name"], "POD_NAME")
    k.expect_eq(env.get("POD_NAMESPACE"), k.ns, "POD_NAMESPACE")
    k.expect_eq(env.get("POD_IP"), ip, "POD_IP")
    k.expect_eq(env.get("NODE_NAME"), pod["spec"]["nodeName"], "NODE_NAME")
    k.expect_eq(env.get("MEMORY_LIMIT_MI"), "96", "MEMORY_LIMIT_MI")
    files = json.loads(k.http(f"http://{ip}:8080/config")[1]).get("files", {})
    labels = files.get("podinfo/labels", "")
    k.expect('team="platform"' in labels and 'app="whoami"' in labels, "/config/podinfo/labels lists the pod's labels",
             labels or f"files: {sorted(files)}")
