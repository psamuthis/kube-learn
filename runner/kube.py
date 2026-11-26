"""Helpers for exercise checks: the `k` object passed to every `check(k)`.

Every exercise directory contains a `check.py` with a function

    def check(k):
        k.expect(k.get("deployment", "web") is not None, "a Deployment named `web` exists")
        ...

`k` is an instance of `Kube` below. Each `expect` prints a ✓ or ✗ line; the
exercise passes when no expectation failed and no exception escaped.

The module is standard library only. YAML is never parsed in Python: kubectl
converts everything to JSON for us (`-o json`).
"""

from __future__ import annotations

import json
import os
import re
import shlex
import subprocess
import time
from pathlib import Path

GREEN = "\033[32m"
RED = "\033[31m"
DIM = "\033[2m"
BOLD = "\033[1m"
RESET = "\033[0m"

PROFILE = os.environ.get("KUBE_LEARN_PROFILE", "kube-learn")
TOOLBOX_IMAGE = "busybox:1.37"


class CheckFailed(Exception):
    """Raised by `Kube.require` to stop a check early."""


class KubectlError(Exception):
    def __init__(self, args, code, out, err):
        self.args_ = args
        self.code = code
        self.out = out
        self.err = err.strip()
        super().__init__(f"`kubectl {' '.join(args)}` failed ({code}): {self.err}")


def run(cmd: list[str], input: str | None = None, timeout: float = 120) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, input=input, capture_output=True, text=True, timeout=timeout)


def kubectl_raw(*args: str, input: str | None = None, timeout: float = 120) -> subprocess.CompletedProcess:
    return run(["kubectl", *args], input=input, timeout=timeout)


class Kube:
    """The toolbox handed to `check(k)`."""

    def __init__(self, ns: str, ex_dir: Path, ex_id: str, verbose: bool = False):
        self.ns = ns
        self.dir = Path(ex_dir)
        self.id = ex_id
        self.verbose = verbose
        self.failures = 0
        self.passes = 0
        # True when `./course verify --solutions` runs the reference solution: checks then do
        # the manual steps a learner would do by hand (run a script, delete a pod…) themselves.
        self.solution = False

    # ------------------------------------------------------------------ output
    def expect(self, cond, msg: str, detail: str | None = None) -> bool:
        """Records one expectation. `msg` describes what *should* be true."""
        if cond:
            self.passes += 1
            print(f"  {GREEN}✓{RESET} {msg}")
        else:
            self.failures += 1
            print(f"  {RED}✗ {msg}{RESET}")
            if detail:
                for line in str(detail).rstrip().splitlines():
                    print(f"      {DIM}{line}{RESET}")
        return bool(cond)

    def require(self, cond, msg: str, detail: str | None = None):
        """Like `expect`, but stops the check if it fails (later checks would be noise)."""
        if not self.expect(cond, msg, detail):
            raise CheckFailed(msg)

    def expect_eq(self, actual, expected, what: str) -> bool:
        return self.expect(actual == expected, f"{what} is {expected!r}", f"got {actual!r}")

    def info(self, msg: str):
        print(f"    {DIM}{msg}{RESET}")

    # ----------------------------------------------------------------- kubectl
    def kubectl(self, *args: str, input: str | None = None, ns: bool = True, timeout: float = 120,
                check: bool = True) -> str:
        """Runs kubectl in the exercise namespace and returns stdout."""
        full = list(args)
        if ns and self.ns and "-n" not in full and "--namespace" not in full and "-A" not in full:
            full = ["-n", self.ns, *full]
        if self.verbose:
            print(f"    {DIM}$ kubectl {' '.join(shlex.quote(a) for a in full)}{RESET}")
        p = kubectl_raw(*full, input=input, timeout=timeout)
        if check and p.returncode != 0:
            raise KubectlError(full, p.returncode, p.stdout, p.stderr)
        return p.stdout

    def try_kubectl(self, *args: str, **kw) -> tuple[int, str, str]:
        """Runs kubectl, never raises: returns (returncode, stdout, stderr)."""
        full = list(args)
        if kw.pop("ns", True) and self.ns and "-n" not in full and "-A" not in full:
            full = ["-n", self.ns, *full]
        p = kubectl_raw(*full, **kw)
        return p.returncode, p.stdout, p.stderr

    def json(self, *args: str, ns: bool = True) -> dict:
        return json.loads(self.kubectl(*args, "-o", "json", ns=ns))

    def get(self, kind: str, name: str, ns: bool | str = True, managed: bool = False) -> dict | None:
        """One object as a dict, or None if it does not exist. `managed=True` keeps managedFields."""
        args = ["get", kind, name, "-o", "json"] + (["--show-managed-fields"] if managed else [])
        if isinstance(ns, str):
            args = ["-n", ns, *args]
        code, out, err = self.try_kubectl(*args, ns=ns is True)
        if code != 0:
            if "NotFound" in err or "not found" in err:
                return None
            raise KubectlError(args, code, out, err)
        return json.loads(out)

    def items(self, kind: str, selector: str | None = None, ns: bool | str = True) -> list[dict]:
        """All objects of a kind (optionally filtered by a label selector)."""
        args = ["get", kind, "-o", "json"]
        if selector:
            args += ["-l", selector]
        if isinstance(ns, str):
            args = ["-n", ns, *args]
        return json.loads(self.kubectl(*args, ns=ns is True))["items"]

    def jp(self, kind: str, name: str, path: str, ns: bool | str = True) -> str:
        """`kubectl get KIND NAME -o jsonpath=PATH` ("" when absent)."""
        args = ["get", kind, name, "-o", f"jsonpath={path}"]
        if isinstance(ns, str):
            args = ["-n", ns, *args]
        code, out, _ = self.try_kubectl(*args, ns=ns is True)
        return out if code == 0 else ""

    def apply(self, path_or_yaml: str | Path, **kw) -> str:
        p = Path(path_or_yaml) if not str(path_or_yaml).lstrip().startswith(("apiVersion", "---", "{")) else None
        if p is not None:
            return self.kubectl("apply", "-f", str(p if p.is_absolute() else self.dir / p), **kw)
        return self.kubectl("apply", "-f", "-", input=str(path_or_yaml), **kw)

    def delete(self, *what: str, wait: bool = True):
        self.try_kubectl("delete", *what, "--ignore-not-found", f"--wait={str(wait).lower()}", timeout=180)

    # ----------------------------------------------------------------- waiting
    def wait_for(self, fn, timeout: float = 60, interval: float = 1.0, what: str = "condition"):
        """Polls `fn()` until it returns something truthy; returns it (or None on timeout)."""
        deadline = time.time() + timeout
        last = None
        while time.time() < deadline:
            try:
                last = fn()
            except (KubectlError, KeyError, IndexError, TypeError, ValueError):
                last = None
            if last:
                return last
            time.sleep(interval)
        if self.verbose:
            self.info(f"timed out waiting for {what}")
        return None

    def rollout(self, name: str, kind: str = "deployment", timeout: int = 120) -> bool:
        """Waits for a Deployment/StatefulSet/DaemonSet rollout to finish."""
        code, _, _ = self.try_kubectl("rollout", "status", f"{kind}/{name}", f"--timeout={timeout}s",
                                      timeout=timeout + 10)
        return code == 0

    def wait(self, target: str, condition: str = "condition=Ready", timeout: int = 90,
             selector: str | None = None) -> bool:
        """`kubectl wait --for=CONDITION TARGET`."""
        args = ["wait", f"--for={condition}", f"--timeout={timeout}s"]
        args += [target, "-l", selector] if selector else [target]
        code, _, _ = self.try_kubectl(*args, timeout=timeout + 10)
        return code == 0

    def pods(self, selector: str | None = None) -> list[dict]:
        return self.items("pods", selector)

    def ready_pods(self, selector: str | None = None) -> list[dict]:
        def ready(p):
            conds = p.get("status", {}).get("conditions", [])
            return p.get("metadata", {}).get("deletionTimestamp") is None and any(
                c["type"] == "Ready" and c["status"] == "True" for c in conds)
        return [p for p in self.pods(selector) if ready(p)]

    def events(self, involved: str | None = None) -> list[dict]:
        args = ["get", "events", "-o", "json"]
        if involved:
            args += ["--field-selector", f"involvedObject.name={involved}"]
        return json.loads(self.kubectl(*args))["items"]

    # ---------------------------------------------------- in-cluster commands
    def exec(self, pod: str, *cmd: str, container: str | None = None, timeout: float = 30) -> tuple[int, str]:
        args = ["exec", pod]
        if container:
            args += ["-c", container]
        p = kubectl_raw("-n", self.ns, *args, "--", *cmd, timeout=timeout)
        return p.returncode, p.stdout + p.stderr

    def toolbox(self, labels: dict[str, str] | None = None, name: str = "toolbox") -> str:
        """Ensures a long-lived busybox pod exists in the namespace; returns its name."""
        if self.get("pod", name) is None:
            lab = {"app": name, "kube-learn/toolbox": "true", **(labels or {})}
            spec = {
                "apiVersion": "v1", "kind": "Pod",
                "metadata": {"name": name, "labels": lab},
                "spec": {
                    "terminationGracePeriodSeconds": 0,
                    "containers": [{
                        "name": "tools", "image": TOOLBOX_IMAGE,
                        "command": ["sleep", "infinity"],
                        "resources": {"requests": {"cpu": "10m", "memory": "8Mi"},
                                      "limits": {"cpu": "100m", "memory": "32Mi"}},
                        "securityContext": {"allowPrivilegeEscalation": False, "runAsNonRoot": True,
                                            "runAsUser": 65534,
                                            "capabilities": {"drop": ["ALL"]},
                                            "seccompProfile": {"type": "RuntimeDefault"}},
                    }],
                },
            }
            self.kubectl("apply", "-f", "-", input=json.dumps(spec))
        self.wait(f"pod/{name}", timeout=90)
        return name

    def sh(self, script: str, pod: str | None = None, timeout: float = 30) -> tuple[int, str]:
        """Runs a shell snippet inside the toolbox pod (busybox: wget, nslookup, nc…)."""
        pod = pod or self.toolbox()
        return self.exec(pod, "sh", "-c", script, timeout=timeout)

    def http(self, url: str, pod: str | None = None, timeout: int = 5) -> tuple[int | None, str]:
        """GETs `url` from inside the cluster. Returns (status code or None, body)."""
        script = (f"rm -f /tmp/b /tmp/h; wget -S -T {timeout} -O /tmp/b {shlex.quote(url)} 2>/tmp/h; "
                  "cat /tmp/h; echo '<<<BODY>>>'; cat /tmp/b 2>/dev/null")
        _, out = self.sh(script, pod=pod, timeout=timeout + 15)
        headers, _, body = out.partition("<<<BODY>>>")
        m = re.findall(r"HTTP/\d(?:\.\d)?\s+(\d{3})", headers)
        status = int(m[-1]) if m else None
        return status, body.strip() if status else headers.strip()

    # ------------------------------------------------------------ the cluster
    def nodes(self) -> list[dict]:
        return json.loads(self.kubectl("get", "nodes", "-o", "json", ns=False))["items"]

    def node_names(self) -> list[str]:
        return [n["metadata"]["name"] for n in self.nodes()]

    def ssh(self, node: str, cmd: str, timeout: float = 60) -> tuple[int, str]:
        """Runs `cmd` on a minikube node (the node name is the minikube node name)."""
        p = run(["minikube", "-p", PROFILE, "ssh", "-n", node, "--", cmd], timeout=timeout)
        return p.returncode, (p.stdout + p.stderr).strip()

    # ---------------------------------------------------------------- answers
    def answers(self, filename: str = "answers.txt") -> dict[str, str]:
        """Parses `key: value` lines. A value starting with `$ ` is run as a shell command
        and replaced by its trimmed output (that's how the reference solutions answer)."""
        path = self.dir / filename
        out: dict[str, str] = {}
        if not path.exists():
            return out
        for raw in path.read_text().splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or ":" not in line:
                continue
            key, value = line.split(":", 1)
            value = value.strip()
            if value.startswith("$ "):
                p = subprocess.run(value[2:], shell=True, capture_output=True, text=True, timeout=60,
                                   env={**os.environ, "NS": self.ns})
                value = p.stdout.strip()
            out[key.strip()] = value
        return out

    def answer(self, key: str) -> str:
        return self.answers().get(key, "")

    def file(self, name: str) -> str:
        p = self.dir / name
        return p.read_text() if p.exists() else ""


def norm(s: str) -> str:
    """Lower-case, collapse whitespace: for comparing free-text answers."""
    return " ".join(str(s).lower().split())


def cpu_millis(q: str) -> int:
    q = str(q)
    if q.endswith("m"):
        return int(q[:-1])
    return int(float(q) * 1000)


_MEM = {"Ki": 2**10, "Mi": 2**20, "Gi": 2**30, "Ti": 2**40, "k": 10**3, "M": 10**6, "G": 10**9, "T": 10**12}


def mem_bytes(q: str) -> int:
    q = str(q)
    for suf, mul in _MEM.items():
        if q.endswith(suf):
            return int(float(q[: -len(suf)]) * mul)
    return int(q)


def container(obj: dict, name: str | None = None) -> dict | None:
    """First (or named) container of a Pod, or of a workload's pod template."""
    spec = obj.get("spec", {})
    if "template" in spec:
        spec = spec["template"]["spec"]
    elif "jobTemplate" in spec:
        spec = spec["jobTemplate"]["spec"]["template"]["spec"]
    cs = spec.get("containers", [])
    if name is None:
        return cs[0] if cs else None
    return next((c for c in cs if c.get("name") == name), None)


def pod_spec(obj: dict) -> dict:
    spec = obj.get("spec", {})
    if "template" in spec:
        return spec["template"]["spec"]
    if "jobTemplate" in spec:
        return spec["jobTemplate"]["spec"]["template"]["spec"]
    return spec


def labels(obj: dict) -> dict:
    return (obj or {}).get("metadata", {}).get("labels", {}) or {}
