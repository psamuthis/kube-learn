from kube import container, pod_spec

# HINT: restricted requires: allowPrivilegeEscalation: false, capabilities.drop: [ALL], runAsNonRoot: true, seccompProfile.type: RuntimeDefault (or Localhost), and no privileged.
# HINT: `readOnlyRootFilesystem: true` is a container securityContext field; then mount an emptyDir at /tmp.


def setup(k):
    k.kubectl("label", "namespace", k.ns, "pod-security.kubernetes.io/enforce=restricted",
              "pod-security.kubernetes.io/warn=restricted", "--overwrite", ns=False)


def check(k):
    k.expect(k.jp("namespace", k.ns, "{.metadata.labels.pod-security\\.kubernetes\\.io/enforce}", ns=False) == "restricted",
             "the namespace still enforces `restricted`")
    k.require(k.rollout("hardened", timeout=90), "the Deployment's pod gets created and becomes Ready",
              "\n".join(e.get("message", "") for e in k.events() if e.get("reason") == "FailedCreate")[-800:])
    d = k.get("deployment", "hardened")
    c = container(d)
    k.expect(c.get("securityContext", {}).get("readOnlyRootFilesystem") is True, "readOnlyRootFilesystem: true")
    pod = k.ready_pods("app=hardened")[0]["metadata"]["name"]
    _, ids = k.exec(pod, "id")
    k.expect("uid=10001" in ids and "gid=10001" in ids, "it runs as uid/gid 10001", ids)
    code, _ = k.exec(pod, "sh", "-c", "touch /app/x")
    k.expect(code != 0, "the root filesystem is read-only")
    code, _ = k.exec(pod, "sh", "-c", "touch /tmp/x")
    k.expect(code == 0, "/tmp is writable")
