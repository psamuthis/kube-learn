"""The pure part of kv-operator: from a KeyValueStore to the objects that implement it.

No I/O here. kv_operator.py (exercise 17.4) does the talking to the API server.
"""

IMAGES = {"7.4": "redis:7.4-alpine", "8.0": "redis:8.0-alpine"}
MANAGER = "kv-operator"


def selector_labels(kv: dict) -> dict:
    """Labels that identify the pods of one KeyValueStore (used in selectors: never change them)."""
    return {"app.kubernetes.io/name": "redis", "app.kubernetes.io/instance": kv["metadata"]["name"]}


def labels(kv: dict) -> dict:
    """All labels we put on the objects we create."""
    return {**selector_labels(kv), "app.kubernetes.io/managed-by": MANAGER}


def owner_reference(kv: dict) -> dict:
    """An ownerReference pointing at the KeyValueStore, marking it as the managing controller."""
    #>>
    #| raise NotImplementedError
    return {
        "apiVersion": kv["apiVersion"],
        "kind": kv["kind"],
        "name": kv["metadata"]["name"],
        "uid": kv["metadata"]["uid"],
        "controller": True,
        "blockOwnerDeletion": True,
    }
    #<<


def desired_service(kv: dict) -> dict:
    """Service <name>: port 6379 named `redis`, selecting selector_labels(kv), owned by kv."""
    #>>
    #| raise NotImplementedError
    md = kv["metadata"]
    return {
        "apiVersion": "v1",
        "kind": "Service",
        "metadata": {"name": md["name"], "namespace": md["namespace"], "labels": labels(kv),
                     "ownerReferences": [owner_reference(kv)]},
        "spec": {
            "selector": selector_labels(kv),
            "ports": [{"name": "redis", "port": 6379, "targetPort": "redis"}],
        },
    }
    #<<


def desired_statefulset(kv: dict) -> dict:
    """StatefulSet <name>: spec.replicas pods of IMAGES[spec.version], a container named `redis`
    with a port named `redis` (6379), readiness probe `redis-cli ping`, requests 10m/16Mi,
    serviceName <name>, the labels above, and an ownerReference to kv."""
    #>>
    #| raise NotImplementedError
    md, spec = kv["metadata"], kv["spec"]
    return {
        "apiVersion": "apps/v1",
        "kind": "StatefulSet",
        "metadata": {"name": md["name"], "namespace": md["namespace"], "labels": labels(kv),
                     "ownerReferences": [owner_reference(kv)]},
        "spec": {
            "replicas": spec.get("replicas", 1),
            "serviceName": md["name"],
            "selector": {"matchLabels": selector_labels(kv)},
            "template": {
                "metadata": {"labels": labels(kv)},
                "spec": {
                    "containers": [{
                        "name": "redis",
                        "image": IMAGES[spec["version"]],
                        "ports": [{"name": "redis", "containerPort": 6379}],
                        "readinessProbe": {"exec": {"command": ["redis-cli", "ping"]}, "periodSeconds": 2},
                        "resources": {"requests": {"cpu": "10m", "memory": "16Mi"}},
                    }],
                },
            },
        },
    }
    #<<


def reconcile(kv: dict, observed: dict) -> list[dict]:
    """`observed` is {"service": <live Service or None>, "statefulset": <live StatefulSet or None>}.
    Returns the desired objects that must be applied: the Service if it's missing, the StatefulSet
    if it's missing or its replicas or image differ from what we want. [] when converged."""
    #>>
    #| raise NotImplementedError
    actions = []
    if observed.get("service") is None:
        actions.append(desired_service(kv))
    want = desired_statefulset(kv)
    live = observed.get("statefulset")
    if live is None:
        actions.append(want)
    else:
        live_image = live["spec"]["template"]["spec"]["containers"][0]["image"]
        want_image = want["spec"]["template"]["spec"]["containers"][0]["image"]
        if live["spec"].get("replicas") != want["spec"]["replicas"] or live_image != want_image:
            actions.append(want)
    return actions
    #<<


def compute_status(kv: dict, sts: dict | None) -> dict:
    """phase: "Pending" if there's no StatefulSet yet, "Ready" if readyReplicas == spec.replicas,
    else "Progressing". readyReplicas: from the StatefulSet's status (0 if absent).
    observedGeneration: the KeyValueStore's metadata.generation."""
    #>>
    #| raise NotImplementedError
    ready = (sts or {}).get("status", {}).get("readyReplicas", 0) or 0
    if sts is None:
        phase = "Pending"
    elif ready == kv["spec"].get("replicas", 1):
        phase = "Ready"
    else:
        phase = "Progressing"
    return {"phase": phase, "readyReplicas": ready, "observedGeneration": kv["metadata"].get("generation", 0)}
    #<<
