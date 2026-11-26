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
    raise NotImplementedError


def desired_service(kv: dict) -> dict:
    """Service <name>: port 6379 named `redis`, selecting selector_labels(kv), owned by kv."""
    raise NotImplementedError


def desired_statefulset(kv: dict) -> dict:
    """StatefulSet <name>: spec.replicas pods of IMAGES[spec.version], a container named `redis`
    with a port named `redis` (6379), readiness probe `redis-cli ping`, requests 10m/16Mi,
    serviceName <name>, the labels above, and an ownerReference to kv."""
    raise NotImplementedError


def reconcile(kv: dict, observed: dict) -> list[dict]:
    """`observed` is {"service": <live Service or None>, "statefulset": <live StatefulSet or None>}.
    Returns the desired objects that must be applied: the Service if it's missing, the StatefulSet
    if it's missing or its replicas or image differ from what we want. [] when converged."""
    raise NotImplementedError


def compute_status(kv: dict, sts: dict | None) -> dict:
    """phase: "Pending" if there's no StatefulSet yet, "Ready" if readyReplicas == spec.replicas,
    else "Progressing". readyReplicas: from the StatefulSet's status (0 if absent).
    observedGeneration: the KeyValueStore's metadata.generation."""
    raise NotImplementedError
