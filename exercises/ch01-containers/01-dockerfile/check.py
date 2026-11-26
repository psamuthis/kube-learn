import json
import subprocess

from kube import PROFILE

TAG = "hello-ch01:1.0"



def build(k):
    dockerfile = k.dir / "Dockerfile"
    k.require(dockerfile.exists(), "a Dockerfile exists in the exercise directory")
    text = dockerfile.read_text()
    p = subprocess.run(["docker", "build", "-q", "-t", TAG, str(k.dir)], capture_output=True, text=True, timeout=600)
    k.require(p.returncode == 0, "`docker build` succeeds", p.stderr[-2000:])
    info = json.loads(subprocess.run(["docker", "image", "inspect", TAG], capture_output=True, text=True).stdout)[0]
    size_mb = info["Size"] / 1e6
    k.expect(size_mb < 150, f"the image is under 150 MB", f"it is {size_mb:.0f} MB; try an -alpine or -slim base")
    user = info["Config"].get("User", "")
    k.expect(user.split(":")[0].isdigit() and user.split(":")[0] != "0", "the image runs as a numeric non-root USER",
             f"USER is {user!r}")
    ep = info["Config"].get("Entrypoint") or []
    cmd = info["Config"].get("Cmd") or []
    shell_form = (ep[:2] == ["/bin/sh", "-c"]) or (not ep and cmd[:2] == ["/bin/sh", "-c"])
    k.expect(not shell_form and (ep or cmd), "the entrypoint uses the exec form", f"Entrypoint={ep} Cmd={cmd}")
    k.info("loading the image onto the nodes…")
    p = subprocess.run(["minikube", "-p", PROFILE, "image", "load", "--overwrite", TAG], capture_output=True, text=True, timeout=300)
    k.require(p.returncode == 0, "the image loads into the cluster", p.stderr[-1000:])
    # A new image under the same tag: replace the pod so it picks it up.
    k.delete("pod", "hello")
    k.apply("pod.yaml")


def check(k):
    build(k)
    k.require(k.wait("pod/hello", timeout=90), "the pod becomes Ready", k.kubectl("describe", "pod", "hello")[-1500:])
    ip = k.jp("pod", "hello", "{.status.podIP}")
    status, body = k.http(f"http://{ip}:8000/")
    k.expect(status == 200 and "hello from hello" in body, "the server answers on port 8000", body[:300])
    k.expect("uid 0" not in body, "it doesn't run as root", body[:300])
