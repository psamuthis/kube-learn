import re



def check(k):
    svc = k.get("service", "web")
    k.require(svc is not None, "a Service `web` exists")
    k.expect_eq(svc["spec"].get("clusterIP"), "None", "the Service's clusterIP (headless)")
    sts = k.get("statefulset", "web")
    k.require(sts is not None, "a StatefulSet `web` exists")
    k.expect_eq(sts["spec"].get("serviceName"), "web", "serviceName")
    k.require(k.rollout("web", kind="statefulset", timeout=180), "the StatefulSet is rolled out")
    pods = {p["metadata"]["name"]: p for p in k.pods("app=web")}
    k.expect(sorted(pods) == ["web-0", "web-1", "web-2"], "pods are web-0, web-1, web-2", f"{sorted(pods)}")
    starts = [pods[n]["metadata"]["creationTimestamp"] for n in ("web-0", "web-1", "web-2") if n in pods]
    k.expect(starts == sorted(starts), "they were created in order")
    ip1 = pods.get("web-1", {}).get("status", {}).get("podIP")
    out = k.wait_for(lambda: (o := k.sh(f"nslookup web-1.web.{k.ns}.svc.cluster.local")[1]) and ip1 in o and o, timeout=30)
    k.expect(ip1 and out, "web-1.web.<ns>.svc.cluster.local resolves to web-1's IP")
    status, body = k.http("http://web-2.web:8080/hostname")
    k.expect(status == 200 and body.strip() == "web-2", "http://web-2.web:8080/hostname reaches web-2", body)
    uid = pods["web-1"]["metadata"]["uid"]
    k.kubectl("delete", "pod", "web-1")
    back = k.wait_for(lambda: (p := k.get("pod", "web-1")) and p["metadata"]["uid"] != uid, timeout=60)
    k.expect(back, "after deleting web-1, a new pod with the same name replaces it")
    k.rollout("web", kind="statefulset", timeout=90)
