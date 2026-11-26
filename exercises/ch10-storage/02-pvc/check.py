import json



def hits(k):
    ip = k.ready_pods("app=counter")[0]["status"]["podIP"]
    return json.loads(k.http(f"http://{ip}:8080/hits")[1])["hits"]


def check(k):
    pvc = k.get("pvc", "data")
    k.require(pvc is not None, "a PVC `data` exists")
    k.expect_eq(pvc["spec"].get("storageClassName"), "local-path", "storageClassName")
    k.expect_eq(pvc["spec"].get("accessModes"), ["ReadWriteOnce"], "accessModes")
    k.expect_eq(k.get("deployment", "counter")["spec"]["strategy"].get("type"), "Recreate", "the strategy")
    k.require(k.rollout("counter", timeout=120), "the Deployment is rolled out")
    k.expect_eq(k.jp("pvc", "data", "{.status.phase}"), "Bound", "the claim's phase")
    hits(k)
    n = hits(k)
    old = k.ready_pods("app=counter")[0]["metadata"]["name"]
    k.kubectl("delete", "pod", old)
    k.require(k.wait_for(lambda: [p for p in k.ready_pods("app=counter") if p["metadata"]["name"] != old], timeout=90),
              "a new pod is Ready")
    after = hits(k)
    k.expect(after == n + 1, "the new pod continues the count", f"{n} → {after}")
    pv = k.get("pv", k.jp("pvc", "data", "{.spec.volumeName}"), ns=False)
    terms = pv["spec"].get("nodeAffinity", {}).get("required", {}).get("nodeSelectorTerms", [])
    node = terms[0]["matchExpressions"][0]["values"][0] if terms else None
    pod_node = k.ready_pods("app=counter")[0]["spec"]["nodeName"]
    k.expect(node == pod_node, "the PV is pinned to the node the pod runs on", f"PV node {node}, pod node {pod_node}")
