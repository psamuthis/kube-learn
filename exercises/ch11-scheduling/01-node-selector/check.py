

def cleanup(k):
    k.try_kubectl("label", "nodes", "--all", "disktype-", ns=False)


def check(k):
    if "kube-learn-m02" not in k.node_names():
        k.require(False, "this exercise needs the 3-node cluster (./course cluster up)")
    if k.solution:
        k.kubectl("label", "node", "kube-learn-m02", "disktype=ssd", "--overwrite", ns=False)
    ssd = [n["metadata"]["name"] for n in k.nodes() if n["metadata"]["labels"].get("disktype") == "ssd"]
    k.expect(ssd == ["kube-learn-m02"], "only kube-learn-m02 has the label disktype=ssd", f"labelled: {ssd}")
    k.require(k.rollout("fast", timeout=90), "the Deployment is rolled out")
    nodes = {p["spec"]["nodeName"] for p in k.pods("app=fast")}
    k.expect(nodes == {"kube-learn-m02"}, "all pods run on kube-learn-m02", f"they run on {sorted(nodes)}")
