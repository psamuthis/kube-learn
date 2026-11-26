APPLY = None

# HINT: The kubelet logs say what it couldn't connect to. Compare with `ls /run/containerd/`.
# HINT: The kubelet's config file is in /var/lib/kubelet/. After fixing it: `sudo systemctl restart kubelet`.

NODE = "kube-learn-m03"
CFG = "/var/lib/kubelet/config.yaml"
BACKUP = "/var/lib/kubelet/config.yaml.kube-learn-backup"


def setup(k):
    if NODE not in k.node_names():
        return
    k.ssh(NODE, f"sudo cp {CFG} {BACKUP} && sudo sed -i 's#containerd/containerd.sock#containerd/containerd.socket#' {CFG} "
                "&& sudo systemctl restart kubelet")
    k.info("waiting for the node to go NotReady (about 40 s)…")
    k.wait_for(lambda: k.jp("node", NODE, '{.status.conditions[?(@.type=="Ready")].status}', ns=False) != "True",
               timeout=120, interval=3)


def cleanup(k):
    if NODE in k.node_names():
        k.ssh(NODE, f"test -f {BACKUP} && sudo cp {BACKUP} {CFG} && sudo rm -f {BACKUP} && sudo systemctl restart kubelet || true")


def check(k):
    k.require(NODE in k.node_names(), "this exercise needs the 3-node cluster (./course cluster up)")
    if k.solution:
        k.ssh(NODE, f"sudo sed -i 's#containerd/containerd.socket#containerd/containerd.sock#' {CFG} && sudo systemctl restart kubelet")
    _, cfg = k.ssh(NODE, f"sudo grep containerRuntimeEndpoint {CFG}")
    k.expect("unix:///run/containerd/containerd.sock" in cfg and "socket" not in cfg, "the runtime endpoint is fixed", cfg)
    ready = k.wait_for(lambda: k.jp("node", NODE, '{.status.conditions[?(@.type=="Ready")].status}', ns=False) == "True",
                       timeout=90, interval=3)
    k.expect(ready, f"{NODE} is Ready again")
    a = k.answers()
    k.expect_eq(a.get("broken_file"), CFG, "broken_file")
    k.expect_eq(a.get("broken_setting"), "containerRuntimeEndpoint", "broken_setting")
    if ready:
        k.ssh(NODE, f"sudo rm -f {BACKUP}")
