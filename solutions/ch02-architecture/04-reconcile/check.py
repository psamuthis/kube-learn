# HINT: `kubectl -n ex-2-4 get events -o wide` has a SOURCE column.
# HINT: `kubectl apply` makes the live object match the file for every field the file sets.


def check(k):
    k.require(k.rollout("web"), "deployment web is rolled out")
    if k.solution:
        # verifying the reference solution: do the deletion ourselves
        pod = k.pods("app=web")[0]["metadata"]["name"]
        k.kubectl("delete", "pod", pod, "--wait=false")
        k.rollout("web")
    a = k.answers()
    k.expect_eq(a.get("pod_owner_kind"), "ReplicaSet", "pod_owner_kind")
    k.expect_eq(a.get("owner_owner_kind"), "Deployment", "owner_owner_kind")
    k.expect(a.get("recreated_by") in ("replicaset-controller", "replicaset_controller"), "recreated_by",
             f"you wrote {a.get('recreated_by')!r}")
    k.expect_eq(a.get("create_reason"), "SuccessfulCreate", "create_reason")
    k.expect_eq(a.get("replicas_after_apply"), "3", "replicas_after_apply")
    created = 0
    for e in k.events():
        if e.get("reason") == "SuccessfulCreate" and e["involvedObject"]["kind"] == "ReplicaSet":
            created += e.get("count") or (e.get("series") or {}).get("count") or 1
    k.expect(created > 3,
             "the ReplicaSet had to create more than 3 pods (you deleted at least one)",
             f"the ReplicaSet's events show {created} pod creations")
