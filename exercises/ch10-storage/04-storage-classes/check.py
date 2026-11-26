

def check(k):
    a = k.answers()
    classes = k.items("storageclass", ns=False)
    default = next(c for c in classes
                   if c["metadata"].get("annotations", {}).get("storageclass.kubernetes.io/is-default-class") == "true")
    k.expect_eq(a.get("default_class"), default["metadata"]["name"], "default_class")
    k.expect_eq(a.get("provisioner"), default["provisioner"], "provisioner")
    k.expect_eq(a.get("binding_mode"), default.get("volumeBindingMode"), "binding_mode")
    k.expect_eq(a.get("phase_before_pod"), "Pending", "phase_before_pod")
    k.expect_eq(a.get("reclaim_policy"), default.get("reclaimPolicy"), "reclaim_policy")
    if k.solution and k.get("pod", "user") is None:
        k.apply("manual/pod.yaml")
    k.require(k.get("pod", "user") is not None, "you applied manual/pod.yaml")
    k.require(k.wait("pod/user", timeout=90), "the pod `user` is Ready")
    a = k.answers()
    pv_name = k.jp("pvc", "probe", "{.spec.volumeName}")
    k.expect_eq(a.get("pv_name"), pv_name, "pv_name")
    pv = k.get("pv", pv_name, ns=False)
    node = pv["spec"]["nodeAffinity"]["required"]["nodeSelectorTerms"][0]["matchExpressions"][0]["values"][0]
    k.expect_eq(a.get("pv_node"), node, "pv_node")
