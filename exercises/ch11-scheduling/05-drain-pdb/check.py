import json



def evict(k, pod):
    body = json.dumps({"apiVersion": "policy/v1", "kind": "Eviction",
                       "metadata": {"name": pod, "namespace": k.ns}})
    code, out, err = k.try_kubectl("create", "--raw", f"/api/v1/namespaces/{k.ns}/pods/{pod}/eviction", "-f", "-",
                                   input=body, ns=False)
    return code == 0, err


def check(k):
    pdb = k.get("pdb", "web")
    k.require(pdb is not None, "a PodDisruptionBudget `web` exists")
    k.expect_eq(pdb["spec"].get("minAvailable"), 2, "minAvailable")
    k.require(k.rollout("web"), "the Deployment is rolled out")
    k.require(k.wait_for(lambda: k.jp("pdb", "web", "{.status.disruptionsAllowed}") == "1", timeout=30),
              "the PDB allows 1 disruption")
    a = k.answers()
    k.expect_eq(a.get("cordon_taint"), "node.kubernetes.io/unschedulable", "cordon_taint")
    k.expect(a.get("blocking_kind", "").lower() in ("daemonset", "daemonsets"), "blocking_kind")
    k.expect_eq(a.get("disruptions_allowed"), "1", "disruptions_allowed")
    k.expect_eq(a.get("refused_status"), "429", "refused_status")
    pods = [p["metadata"]["name"] for p in k.ready_pods("app=web")]
    ok1, err1 = evict(k, pods[0])
    ok2, err2 = evict(k, pods[1])
    k.expect(ok1, "the first eviction is allowed", err1)
    k.expect(not ok2 and ("disruption budget" in err2 or "429" in err2 or "TooManyRequests" in err2),
             "the second eviction is refused by the PDB", err2 or "it was allowed!")
    k.rollout("web")
    cordoned = [n["metadata"]["name"] for n in k.nodes() if n["spec"].get("unschedulable")]
    k.expect(not cordoned, "every node is schedulable again (uncordoned)", f"still cordoned: {cordoned}")
