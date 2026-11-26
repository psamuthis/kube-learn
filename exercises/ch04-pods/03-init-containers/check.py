import json
import time

APPLY = None  # the check applies the files itself, in order



def check(k):
    k.delete("service", "db")
    k.delete("pod", "app")
    k.apply("pod.yaml")
    pod = k.get("pod", "app")
    names = [c["name"] for c in pod["spec"].get("initContainers", [])]
    k.require(names == ["wait-for-db", "render-config"], "init containers are wait-for-db, then render-config",
              f"got {names}")
    time.sleep(12)
    phase = k.jp("pod", "app", "{.status.phase}")
    k.expect(phase == "Pending", "without a `db` Service, the pod waits in its first init container", f"phase: {phase}")
    k.apply("db-service.yaml")
    k.require(k.wait("pod/app", timeout=120), "once `db` exists, the pod becomes Ready")
    ip = k.jp("pod", "app", "{.status.podIP}")
    status, body = k.http(f"http://{ip}:8080/config")
    files = json.loads(body).get("files", {}) if status == 200 else {}
    k.expect(files.get("settings.txt", "").strip() == "database=db.ex-4-3.svc.cluster.local",
             "kubeapp sees the rendered /config/settings.txt", body[:300])
