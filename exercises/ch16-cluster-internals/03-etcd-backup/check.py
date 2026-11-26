import json

APPLY = None  # the check applies status-pod.yaml itself, after looking for the snapshot


SNAP = "/var/lib/minikube/etcd/snapshot-ex163.db"


def cleanup(k):
    k.ssh(k.node_names()[0], f"sudo rm -f {SNAP}")


def save(k):
    pod = k.items("pods", "component=etcd", ns="kube-system")[0]
    f = {c.split("=", 1)[0]: c.split("=", 1)[1] for c in pod["spec"]["containers"][0]["command"] if "=" in c}
    k.kubectl("-n", "kube-system", "exec", pod["metadata"]["name"], "--", "etcdctl", "--endpoints=https://127.0.0.1:2379",
              f"--cacert={f['--trusted-ca-file']}", f"--cert={f['--cert-file']}", f"--key={f['--key-file']}",
              "snapshot", "save", SNAP, ns=False)


def check(k):
    cp = k.node_names()[0]
    if k.solution:
        save(k)
    code, out = k.ssh(cp, f"sudo stat -c %s {SNAP}")
    k.require(code == 0 and out.strip().isdigit() and int(out.strip()) > 100_000, f"the snapshot {SNAP} exists on {cp}", out)
    k.delete("pod", "snapshot-status")
    k.apply("status-pod.yaml")
    done = k.wait_for(lambda: k.jp("pod", "snapshot-status", "{.status.phase}") in ("Succeeded", "Failed"), timeout=120)
    k.require(done and k.jp("pod", "snapshot-status", "{.status.phase}") == "Succeeded", "the snapshot-status pod succeeds",
              k.try_kubectl("logs", "snapshot-status")[1][-500:])
    status = json.loads(k.kubectl("logs", "snapshot-status"))
    a = k.answers()
    k.expect_eq(a.get("revision"), str(status["revision"]), "revision")
    k.expect_eq(a.get("total_keys"), str(status["totalKey"]), "total_keys")
    k.expect_eq(a.get("hash"), str(status["hash"]), "hash")
