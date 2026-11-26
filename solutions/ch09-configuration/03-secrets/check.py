import base64
import json

# HINT: `stringData:` takes plain values; the API server encodes them into `data:`.
# HINT: `volumes: [{name: creds, secret: {secretName: db-credentials, defaultMode: 0440}}]`. In YAML, 0440 is octal.
# HINT: `kubectl -n ex-9-3 exec deploy/shop -- mount | grep secrets`


def check(k):
    sec = k.get("secret", "db-credentials")
    k.require(sec is not None, "a Secret `db-credentials` exists")
    k.expect_eq(base64.b64decode(sec["data"].get("password", "")).decode(), "hunter2", "the password")
    k.kubectl("rollout", "restart", "deployment/shop")
    k.require(k.rollout("shop"), "the Deployment is rolled out")
    pod = k.ready_pods("app=shop")[0]
    name, ip = pod["metadata"]["name"], pod["status"]["podIP"]
    env = json.loads(k.http(f"http://{ip}:8080/env")[1])
    k.expect_eq(env.get("DB_USER"), "shop", "DB_USER")
    code, out = k.exec(name, "cat", "/secrets/password")
    k.expect(code == 0 and out.strip() == "hunter2", "the app (UID 10001) can read /secrets/password", out[:200])
    _, mode = k.exec(name, "stat", "-L", "-c", "%a", "/secrets/password")
    k.expect_eq(mode.strip(), "440", "the file mode")
    code, _ = k.exec(name, "sh", "-c", "echo x > /secrets/password")
    k.expect(code != 0, "the volume is read-only")
    a = k.answers()
    k.expect_eq(a.get("password_in_data"), "aHVudGVyMg==", "password_in_data")
    k.expect_eq(a.get("decoder"), "base64", "decoder")
    k.expect_eq(a.get("fs_type"), "tmpfs", "fs_type")
