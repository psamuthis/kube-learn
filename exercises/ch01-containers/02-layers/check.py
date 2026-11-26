import json
import subprocess

APPLY = None



def check(k):
    p = subprocess.run(["docker", "image", "inspect", "kubeapp:1.0"], capture_output=True, text=True)
    k.require(p.returncode == 0, "kubeapp:1.0 exists in your local Docker (run `./course cluster images`)", p.stderr)
    info = json.loads(p.stdout)[0]
    a = k.answers()
    cfg = info["Config"]
    env = dict(e.split("=", 1) for e in cfg.get("Env", []))
    k.expect(a.get("layers") == str(len(info["RootFS"]["Layers"])), "layers", f"you wrote {a.get('layers')!r}")
    k.expect(a.get("user") == cfg.get("User"), "user", f"you wrote {a.get('user')!r}")
    k.expect(a.get("app_version") == env.get("APP_VERSION"), "app_version", f"you wrote {a.get('app_version')!r}")
    k.expect(a.get("entrypoint") == " ".join(cfg.get("Entrypoint") or []), "entrypoint", f"you wrote {a.get('entrypoint')!r}")
    k.expect(a.get("image_id") == info["Id"], "image_id", f"you wrote {a.get('image_id')!r}")
