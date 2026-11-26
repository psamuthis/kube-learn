import json
import re
import subprocess
import sys
import tempfile
import time

APPLY = ["crd.yaml"]



def start(k):
    proxy = subprocess.Popen(["kubectl", "proxy", "--port=0"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    line = proxy.stdout.readline()
    port = re.search(r":(\d+)", line).group(1)
    log = tempfile.NamedTemporaryFile("w+", prefix="kv-operator-", suffix=".log", delete=False)
    op = subprocess.Popen([sys.executable, str(k.dir / "kv_operator.py"), "--namespace", k.ns,
                           "--api", f"http://127.0.0.1:{port}", "--resync", "3"],
                          stdout=log, stderr=subprocess.STDOUT)
    return proxy, op, log


def check(k):
    k.require(k.wait("crd/keyvaluestores.kube-learn.dev", "condition=Established", timeout=30), "the KeyValueStore CRD is installed")
    k.delete("keyvaluestore", "cache")
    k.delete("statefulset,service", "cache")
    proxy, op, log = start(k)
    try:
        time.sleep(2)
        k.require(op.poll() is None, "kv_operator.py starts", open(log.name).read()[-1500:])
        k.apply("kv.yaml")
        sts = k.wait_for(lambda: k.get("statefulset", "cache"), timeout=30)
        k.require(sts, "the operator creates the StatefulSet `cache`", open(log.name).read()[-1500:])
        k.expect(k.get("service", "cache") is not None, "…and the Service `cache`")
        owners = [o.get("kind") for o in sts["metadata"].get("ownerReferences", [])]
        k.expect(owners == ["KeyValueStore"], "the StatefulSet is owned by the KeyValueStore", f"{owners}")
        k.require(k.rollout("cache", kind="statefulset", timeout=180), "2 Redis pods become Ready (pulling redis may take a minute)")
        ready = k.wait_for(lambda: k.jp("kvs", "cache", "{.status.phase}") == "Ready"
                           and k.jp("kvs", "cache", "{.status.readyReplicas}") == "2", timeout=30)
        k.expect(ready, "the KeyValueStore's status says Ready with 2 ready replicas",
                 k.jp("kvs", "cache", "{.status}") + "\n" + open(log.name).read()[-800:])
        gen = k.jp("kvs", "cache", "{.metadata.generation}")
        k.expect(k.jp("kvs", "cache", "{.status.observedGeneration}") == gen, "status.observedGeneration matches")
        k.kubectl("scale", "kvs", "cache", "--replicas=3")
        scaled = k.wait_for(lambda: k.jp("statefulset", "cache", "{.spec.replicas}") == "3", timeout=30)
        k.expect(scaled, "scaling the KeyValueStore to 3 scales the StatefulSet")
        k.rollout("cache", kind="statefulset", timeout=120)
        k.expect(k.wait_for(lambda: k.jp("kvs", "cache", "{.status.readyReplicas}") == "3", timeout=30),
                 "the status follows: 3 ready replicas")
        code, out = k.exec("cache-0", "redis-cli", "-h", "cache", "ping")
        k.expect("PONG" in out, "redis answers through the Service `cache`", out)
        k.kubectl("delete", "kvs", "cache")
        gone = k.wait_for(lambda: k.get("statefulset", "cache") is None, timeout=60)
        k.expect(gone, "deleting the KeyValueStore garbage-collects the StatefulSet")
        k.expect(op.poll() is None, "the operator is still running at the end", open(log.name).read()[-1500:])
    finally:
        op.terminate()
        proxy.terminate()
        if k.failures:
            k.info("operator output (last lines):")
            for line in open(log.name).read().splitlines()[-15:]:
                k.info("  " + line)
