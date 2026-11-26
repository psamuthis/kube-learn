import random
import time

APPLY = None


WORDS = ["kumquat", "zeppelin", "obsidian", "marmalade", "quasar", "tundra", "falafel", "nebula"]


def setup(k):
    word = random.choice(WORDS) + "-" + str(random.randint(100, 999))
    k.apply(f"""
apiVersion: v1
kind: Pod
metadata: {{name: vault, annotations: {{kube-learn.dev/answer-is-not-here: "nice try"}}}}
spec:
  containers:
    - name: main
      image: registry.k8s.io/pause:3.10
      env: [{{name: SECRET_WORD, value: "{word}"}}]
""")
    k.wait("pod/vault", timeout=60)


def check(k):
    pod = k.get("pod", "vault")
    if k.solution and not pod["spec"].get("ephemeralContainers"):
        k.kubectl("debug", "vault", "--image=busybox:1.37", "--target=main", "--profile=general", "--container=dbg",
                  "--", "sleep", "3600")
        k.wait_for(lambda: "running" in k.jp("pod", "vault", "{.status.ephemeralContainerStatuses[0].state}"), timeout=60)
        pod = k.get("pod", "vault")
    k.expect(pod["spec"].get("ephemeralContainers"), "the pod has an ephemeral debug container")
    want = next(e["value"] for e in pod["spec"]["containers"][0]["env"] if e["name"] == "SECRET_WORD")
    got = k.answer("secret_word")
    k.expect(got == want, "secret_word is right", f"you wrote {got!r}")
