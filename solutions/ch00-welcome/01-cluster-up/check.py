import json

APPLY = None  # nothing to apply: this exercise only reads the cluster

# HINT: `kubectl get nodes` lists the nodes; the ROLES column shows the control plane.
# HINT: `kubectl version` prints both the client and the server version. You want the server's.
# HINT: `kubectl config current-context`.


def check(k):
    a = k.answers()
    nodes = k.nodes()
    k.expect(a.get("nodes", "").strip() == str(len(nodes)), "nodes: the number of nodes",
             f"you wrote {a.get('nodes')!r}")
    version = json.loads(k.kubectl("version", "-o", "json", ns=False))["serverVersion"]["gitVersion"]
    k.expect(a.get("server_version", "").lstrip("v") == version.lstrip("v"), "server_version: the server's version",
             f"you wrote {a.get('server_version')!r}")
    cp = [n["metadata"]["name"] for n in nodes
          if "node-role.kubernetes.io/control-plane" in n["metadata"].get("labels", {})]
    k.expect(a.get("control_plane_node") in cp, "control_plane_node: the control-plane node's name",
             f"you wrote {a.get('control_plane_node')!r}")
    ctx = k.kubectl("config", "current-context", ns=False).strip()
    k.expect(a.get("context") == ctx, "context: the current context", f"you wrote {a.get('context')!r}")
    if len(nodes) < 3:
        k.info("note: you're on a single-node cluster; chapter 11 (scheduling) needs 3 nodes.")
