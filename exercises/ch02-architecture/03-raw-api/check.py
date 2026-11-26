import subprocess
import time

APPLY = None



def check(k):
    if k.get("configmap", "made-by-curl") is None and k.solution:
        # verifying the reference solution: start a proxy and run the script ourselves
        proxy = subprocess.Popen(["kubectl", "proxy", "--port", "8001"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            time.sleep(2)
            subprocess.run(["bash", str(k.dir / "create.sh")], capture_output=True, timeout=30)
        finally:
            proxy.terminate()
    cm = k.get("configmap", "made-by-curl", managed=True)
    k.require(cm is not None, "a ConfigMap `made-by-curl` exists in ex-2-3",
              "run `kubectl proxy --port 8001` in another terminal, then `bash create.sh`")
    k.expect_eq(cm.get("data", {}).get("greeting"), "hello", "data.greeting")
    k.expect_eq(cm.get("data", {}).get("language"), "http", "data.language")
    managers = [m.get("manager", "") for m in cm["metadata"].get("managedFields", [])]
    k.expect(any(m.startswith("curl") for m in managers), "it was created by curl (managedFields)",
             f"managers: {managers}")
