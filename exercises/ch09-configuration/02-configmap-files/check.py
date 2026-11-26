import json



def check(k):
    k.require(k.rollout("shop"), "the Deployment is rolled out")
    ip = k.ready_pods("app=shop")[0]["status"]["podIP"]
    files = k.wait_for(lambda: (f := json.loads(k.http(f"http://{ip}:8080/config")[1])["files"])
                       and "motd" in f and f, timeout=60) or {}
    k.expect(sorted(files) == ["motd", "settings/application.properties"],
             "/config contains exactly motd and settings/application.properties", f"{sorted(files)}")
    k.expect_eq(files.get("motd", "").strip(), "Welcome to the shop", "motd")
    k.expect_eq(files.get("settings/application.properties", "").split(), ["cache.ttl=300", "currency=EUR"],
                "application.properties lines")
