from kube import container, pod_spec

# HINT: `tolerations: [{key: node-role.kubernetes.io/control-plane, operator: Exists, effect: NoSchedule}]`
# HINT: `env: [{name: NODE_NAME, valueFrom: {fieldRef: {fieldPath: spec.nodeName}}}]`
# HINT: `volumes: [{name: varlog, hostPath: {path: /var/log}}]` plus a `volumeMounts` entry with `readOnly: true`.


def check(k):
    ds = k.get("daemonset", "node-agent")
    k.require(ds is not None, "a DaemonSet `node-agent` exists")
    spec = pod_spec(ds)
    tol = spec.get("tolerations", [])
    k.expect(any(t.get("key") == "node-role.kubernetes.io/control-plane" for t in tol), "it tolerates the control-plane taint")
    c = container(ds)
    env = {e["name"]: e for e in c.get("env", [])}
    k.expect(env.get("NODE_NAME", {}).get("valueFrom", {}).get("fieldRef", {}).get("fieldPath") == "spec.nodeName",
             "NODE_NAME comes from spec.nodeName")
    mounts = {m["mountPath"]: m for m in c.get("volumeMounts", [])}
    k.expect(mounts.get("/host/var/log", {}).get("readOnly") is True, "/host/var/log is mounted read-only")
    k.require(k.rollout("node-agent", kind="daemonset"), "the DaemonSet is rolled out")
    nodes = set(k.node_names())
    pods = k.ready_pods("app=node-agent")
    on = {p["spec"]["nodeName"] for p in pods}
    k.expect(on == nodes and len(pods) == len(nodes), "exactly one Ready agent on each node", f"agents on {sorted(on)}")
    for p in pods:
        logs = k.kubectl("logs", p["metadata"]["name"])
        k.expect(f"agent on {p['spec']['nodeName']}" in logs, f"the agent on {p['spec']['nodeName']} knows its node", logs[:200])
