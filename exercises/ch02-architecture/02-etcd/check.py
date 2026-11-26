import json

APPLY = None



def setup(k):
    k.kubectl("create", "configmap", "plans", "--from-literal=target=moon", "--from-literal=when=friday")
    k.kubectl("create", "secret", "generic", "launch", "--from-literal=code=swordfish-42")


def etcdctl(k, *args):
    pod = k.items("pods", "component=etcd", ns="kube-system")[0]
    cmd = pod["spec"]["containers"][0]["command"]
    f = {c.split("=", 1)[0]: c.split("=", 1)[1] for c in cmd if "=" in c}
    return k.kubectl("-n", "kube-system", "exec", pod["metadata"]["name"], "--", "etcdctl",
                     "--endpoints=https://127.0.0.1:2379", f"--cacert={f['--trusted-ca-file']}",
                     f"--cert={f['--cert-file']}", f"--key={f['--key-file']}", *args, ns=False)


def check(k):
    a = k.answers()
    key = f"/registry/configmaps/{k.ns}/plans"
    k.expect(a.get("configmap_key") == key, "configmap_key", f"you wrote {a.get('configmap_key')!r}")
    kvs = json.loads(etcdctl(k, "get", key, "-w", "json")).get("kvs", [])
    k.require(kvs, "the key exists in etcd")
    rev = str(kvs[0]["mod_revision"])
    k.expect(a.get("mod_revision") == rev, "mod_revision", f"you wrote {a.get('mod_revision')!r}")
    k.expect(a.get("secret_plaintext", "").lower() in ("yes", "y", "true"), "secret_plaintext",
             "look again: etcdctl get /registry/secrets/ex-2-2/launch")
    rv = k.jp("configmap", "plans", "{.metadata.resourceVersion}")
    k.expect(a.get("resource_version") == rv, "resource_version", f"you wrote {a.get('resource_version')!r}")
    if rv == rev:
        k.info("resourceVersion == etcd mod_revision: that's how optimistic concurrency works.")
