# HINT: `volumes:` is a pod-level list (sibling of `containers:`); each container then has `volumeMounts: [{name, mountPath}]`.
# HINT: `emptyDir: {}` creates an empty directory that lives as long as the pod.


def check(k):
    pod = k.get("pod", "web")
    k.require(pod is not None, "a Pod `web` exists")
    vols = {v["name"]: v for v in pod["spec"].get("volumes", [])}
    k.expect("html" in vols and "emptyDir" in vols["html"], "it has an emptyDir volume named `html`")
    k.require(k.wait("pod/web", timeout=90), "the pod becomes Ready")
    ip = k.jp("pod", "web", "{.status.podIP}")
    status, body = k.http(f"http://{ip}/")
    k.expect(status == 200 and "written by web" in body, "nginx serves the page the writer wrote", body[:300])
    code, out = k.exec("web", "wget", "-qO-", "http://localhost/", container="writer")
    k.expect(code == 0 and "written by" in out, "the writer reaches nginx on localhost", out[:300])
