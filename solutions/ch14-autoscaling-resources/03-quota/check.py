APPLY = ["quota.yaml", "fleet.yaml"]  # the quota must exist before the pods are created

# HINT: `kubectl -n ex-14-3 describe quota budget` shows Used vs Hard.
# HINT: The Deployment controller doesn't create pods; its ReplicaSet does, and that's who gets refused.
# HINT: 4 pods × (50m, 64Mi) = (200m, 256Mi): which limit is full?


def check(k):
    q = k.get("resourcequota", "budget")
    k.require(q is not None, "a ResourceQuota `budget` exists")
    hard = q["spec"].get("hard", {})
    k.expect(hard.get("pods") == "4" and hard.get("requests.cpu") == "400m" and hard.get("requests.memory") == "512Mi",
             "pods 4, requests.cpu 400m, requests.memory 512Mi", f"{hard}")
    k.wait_for(lambda: len(k.pods("app=fleet")) >= 4, timeout=60)
    n = len(k.pods("app=fleet"))
    k.expect(n == 4, "the quota caps fleet at 4 pods",
             f"{n} pods. Pods created before the quota existed aren't removed: try --fresh")
    a = k.answers()
    k.expect_eq(a.get("fleet_pods"), str(n), "fleet_pods")
    k.expect_eq(a.get("reporting_kind"), "ReplicaSet", "reporting_kind")
    k.expect_eq(a.get("event_reason"), "FailedCreate", "event_reason")
    k.expect_eq(a.get("limit_hit"), "pods", "limit_hit")
