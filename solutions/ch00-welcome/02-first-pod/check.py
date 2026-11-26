from kube import labels, container

# HINT: `metadata` takes `name:` and a `labels:` map (`app: hello`).
# HINT: `containers` is a *list*: each item starts with `- name: …` and has `image:` and `ports:`.
# HINT: Look at the Pod example in section 0.5 of the book.


def check(k):
    pod = k.get("pod", "hello")
    k.require(pod is not None, "a Pod named `hello` exists")
    k.expect_eq(labels(pod).get("app"), "hello", "label `app`")
    c = container(pod, "web")
    k.require(c is not None, "it has a container named `web`")
    k.expect_eq(c.get("image"), "nginx:1.29", "the image")
    k.expect(any(p.get("containerPort") == 80 for p in c.get("ports", [])), "it declares containerPort 80")
    k.require(k.wait("pod/hello", timeout=120), "the pod becomes Ready",
              k.kubectl("describe", "pod", "hello")[-1500:])
    ip = k.jp("pod", "hello", "{.status.podIP}")
    status, body = k.http(f"http://{ip}/")
    k.expect(status == 200 and "nginx" in body.lower(), f"http://{ip}/ answers with the nginx welcome page",
             body[:300])
