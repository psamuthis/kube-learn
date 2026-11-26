from kube import container



def check(k):
    web, app = k.get("pod", "web"), k.get("pod", "app")
    k.require(web and app, "both pods exist")
    img = container(web)["image"]
    k.expect("nginx" in img and "1.29" in img and "alpine" in img, "web runs nginx 1.29 alpine", img)
    k.expect(container(app)["image"] == "kubeapp:1.0", "app runs kubeapp:1.0")
    k.expect(container(app).get("imagePullPolicy") in ("IfNotPresent", "Never"),
             "app uses a pull policy that works with a node-local image")
    for name in ("web", "app"):
        k.expect(k.wait(f"pod/{name}", timeout=90), f"pod {name} becomes Ready",
                 k.jp("pod", name, "{.status.containerStatuses[0].state}"))
