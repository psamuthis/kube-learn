"""Unit tests for reconcile.py. No cluster needed."""
import copy
import importlib.util
import traceback

APPLY = None

# HINT: Start with owner_reference: apiVersion and kind come from the KeyValueStore itself; `controller: True`.
# HINT: In reconcile, compare only what you own (replicas and the container image), not whole objects: the API server adds lots of defaults to live objects.
# HINT: `(sts or {}).get("status", {}).get("readyReplicas", 0)`: a fresh StatefulSet has no readyReplicas field at all.

KV = {"apiVersion": "kube-learn.dev/v1", "kind": "KeyValueStore",
      "metadata": {"name": "cache", "namespace": "shop", "uid": "u-123", "generation": 4},
      "spec": {"replicas": 2, "version": "7.4"}}


def load(k):
    spec = importlib.util.spec_from_file_location("reconcile_under_test", k.dir / "reconcile.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def live(obj, **status):
    """What the API server would return: our object plus defaults and status."""
    o = copy.deepcopy(obj)
    o["metadata"]["resourceVersion"] = "999"
    o["metadata"]["managedFields"] = [{"manager": "kv-operator"}]
    if o["kind"] == "StatefulSet":
        o["spec"]["podManagementPolicy"] = "OrderedReady"
        o["spec"]["template"]["spec"]["containers"][0]["imagePullPolicy"] = "IfNotPresent"
        o["status"] = status
    else:
        o["spec"]["clusterIP"] = "10.96.1.2"
    return o


def test(k, name, fn):
    try:
        fn()
        k.expect(True, name)
    except AssertionError as e:
        k.expect(False, name, str(e) or traceback.format_exc(limit=1))
    except NotImplementedError:
        k.expect(False, name, "not implemented yet")
    except Exception:
        k.expect(False, name, traceback.format_exc(limit=3))


def check(k):
    r = load(k)

    def owner():
        ref = r.owner_reference(KV)
        assert ref.get("kind") == "KeyValueStore" and ref.get("apiVersion") == "kube-learn.dev/v1", ref
        assert ref.get("name") == "cache" and ref.get("uid") == "u-123", ref
        assert ref.get("controller") is True, "controller must be True"

    def service():
        s = r.desired_service(KV)
        assert s["kind"] == "Service" and s["metadata"]["name"] == "cache" and s["metadata"]["namespace"] == "shop", s["metadata"]
        assert s["spec"]["selector"] == r.selector_labels(KV), s["spec"].get("selector")
        p = s["spec"]["ports"][0]
        assert p["port"] == 6379 and p.get("name") == "redis", p
        assert s["metadata"].get("ownerReferences") == [r.owner_reference(KV)], "the Service needs the ownerReference"

    def statefulset():
        s = r.desired_statefulset(KV)
        assert s["apiVersion"] == "apps/v1" and s["kind"] == "StatefulSet", (s["apiVersion"], s["kind"])
        assert s["metadata"]["name"] == "cache" and s["metadata"].get("ownerReferences") == [r.owner_reference(KV)]
        assert s["spec"]["replicas"] == 2 and s["spec"]["serviceName"] == "cache"
        assert s["spec"]["selector"]["matchLabels"] == r.selector_labels(KV)
        tmpl = s["spec"]["template"]
        assert r.selector_labels(KV).items() <= tmpl["metadata"]["labels"].items(), "pod labels must include the selector"
        c = tmpl["spec"]["containers"][0]
        assert c["name"] == "redis" and c["image"] == "redis:7.4-alpine", c.get("image")
        assert {"name": "redis", "containerPort": 6379} in c["ports"], c.get("ports")
        assert c["readinessProbe"]["exec"]["command"] == ["redis-cli", "ping"]
        eight = copy.deepcopy(KV)
        eight["spec"]["version"] = "8.0"
        assert r.desired_statefulset(eight)["spec"]["template"]["spec"]["containers"][0]["image"] == "redis:8.0-alpine"

    def from_scratch():
        acts = r.reconcile(KV, {"service": None, "statefulset": None})
        assert sorted(a["kind"] for a in acts) == ["Service", "StatefulSet"], [a["kind"] for a in acts]

    def converged():
        obs = {"service": live(r.desired_service(KV)), "statefulset": live(r.desired_statefulset(KV), readyReplicas=2)}
        acts = r.reconcile(KV, obs)
        assert acts == [], f"expected no actions when everything matches (ignoring defaults), got {[a['kind'] for a in acts]}"

    def scaled():
        obs = {"service": live(r.desired_service(KV)), "statefulset": live(r.desired_statefulset(KV))}
        more = copy.deepcopy(KV)
        more["spec"]["replicas"] = 3
        acts = r.reconcile(more, obs)
        assert [a["kind"] for a in acts] == ["StatefulSet"] and acts[0]["spec"]["replicas"] == 3, acts

    def upgraded():
        obs = {"service": live(r.desired_service(KV)), "statefulset": live(r.desired_statefulset(KV))}
        new = copy.deepcopy(KV)
        new["spec"]["version"] = "8.0"
        acts = r.reconcile(new, obs)
        assert [a["kind"] for a in acts] == ["StatefulSet"], [a["kind"] for a in acts]

    def statuses():
        assert r.compute_status(KV, None) == {"phase": "Pending", "readyReplicas": 0, "observedGeneration": 4}
        sts = live(r.desired_statefulset(KV))
        assert r.compute_status(KV, sts)["phase"] == "Progressing", "no readyReplicas yet means Progressing"
        assert r.compute_status(KV, sts)["readyReplicas"] == 0
        sts = live(r.desired_statefulset(KV), readyReplicas=2)
        assert r.compute_status(KV, sts) == {"phase": "Ready", "readyReplicas": 2, "observedGeneration": 4}

    for name, fn in [("owner_reference", owner), ("desired_service", service), ("desired_statefulset", statefulset),
                     ("reconcile: nothing exists → create both", from_scratch),
                     ("reconcile: converged → no actions", converged),
                     ("reconcile: replicas changed → update the StatefulSet", scaled),
                     ("reconcile: version changed → update the StatefulSet", upgraded),
                     ("compute_status", statuses)]:
        test(k, name, fn)
