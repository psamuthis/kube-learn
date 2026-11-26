APPLY = None

# HINT: `kubectl get leases -A` shows one Lease per node in a dedicated namespace.
# HINT: Watch the lease with -w and compare consecutive renewTime values (the kubelet renews every leaseDuration/4).


def check(k):
    a = k.answers()
    node = k.node_names()[0]
    lease = k.get("lease", node, ns="kube-node-lease")
    k.expect_eq(a.get("node_lease_namespace"), "kube-node-lease", "node_lease_namespace")
    k.expect_eq(a.get("node_lease_duration"), str(lease["spec"]["leaseDurationSeconds"]), "node_lease_duration")
    r = a.get("renew_interval", "")
    k.expect(r.isdigit() and 8 <= int(r) <= 12, "renew_interval is about 10 s", f"you wrote {r!r}")
    holder = k.jp("lease", "kube-controller-manager", "{.spec.holderIdentity}", ns="kube-system")
    k.expect_eq(a.get("controller_manager_holder"), holder, "controller_manager_holder")
    owner = (lease["metadata"].get("ownerReferences") or [{}])[0].get("kind")
    k.expect_eq(a.get("node_lease_owner_kind"), owner, "node_lease_owner_kind")
