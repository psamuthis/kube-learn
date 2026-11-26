# HINT: kubectl label node kube-learn-m03 dedicated=gpu && kubectl taint node kube-learn-m03 dedicated=gpu:NoSchedule
# HINT: A toleration only *allows* the node; the nodeSelector makes it the *only* choice.
# HINT: If `others` pods were already on m03 before the taint, NoSchedule doesn't evict them: `kubectl -n ex-11-3 rollout restart deploy/others`.


def cleanup(k):
    k.try_kubectl("taint", "nodes", "--all", "dedicated-", ns=False)
    k.try_kubectl("label", "nodes", "--all", "dedicated-", ns=False)


def check(k):
    if "kube-learn-m03" not in k.node_names():
        k.require(False, "this exercise needs the 3-node cluster (./course cluster up)")
    if k.solution:
        k.kubectl("label", "node", "kube-learn-m03", "dedicated=gpu", "--overwrite", ns=False)
        k.try_kubectl("taint", "node", "kube-learn-m03", "dedicated=gpu:NoSchedule", "--overwrite", ns=False)
        k.kubectl("rollout", "restart", "deployment/others")
    m03 = k.get("node", "kube-learn-m03", ns=False)
    k.expect(m03["metadata"]["labels"].get("dedicated") == "gpu", "m03 is labelled dedicated=gpu")
    taints = m03["spec"].get("taints", [])
    k.expect(any(t.get("key") == "dedicated" and t.get("value") == "gpu" and t.get("effect") == "NoSchedule" for t in taints),
             "m03 is tainted dedicated=gpu:NoSchedule", f"taints: {taints}")
    k.require(k.rollout("gpu-job", timeout=90), "gpu-job is rolled out")
    k.require(k.rollout("others", timeout=90), "others is rolled out")
    gpu_nodes = {p["spec"]["nodeName"] for p in k.ready_pods("app=gpu-job")}
    k.expect(gpu_nodes == {"kube-learn-m03"}, "gpu-job runs only on m03", f"{sorted(gpu_nodes)}")
    other_nodes = {p["spec"]["nodeName"] for p in k.ready_pods("app=others")}
    k.expect("kube-learn-m03" not in other_nodes, "no `others` pod on m03", f"{sorted(other_nodes)}")
