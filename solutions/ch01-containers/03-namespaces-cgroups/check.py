# HINT: Inside the container, `ps` shows the python process as PID 1: it's alone in its PID namespace.
# HINT: 64Mi = 64 × 1024 × 1024 bytes. cpu.max is "<quota> <period>" in microseconds.
# HINT: On the node: `sudo crictl ps --name app` gives the container ID, then `sudo crictl inspect ID | grep '"pid"'`.


def check(k):
    k.require(k.wait("pod/inspect", timeout=90), "the pod `inspect` is Ready")
    a = k.answers()
    _, pid = k.exec("inspect", "sh", "-c", "pgrep -f app.py | head -1")
    k.expect(a.get("pid_inside") == pid.strip(), "pid_inside", f"you wrote {a.get('pid_inside')!r}")
    k.expect(a.get("hostname") == "inspect", "hostname", f"you wrote {a.get('hostname')!r}")
    _, mem = k.exec("inspect", "cat", "/sys/fs/cgroup/memory.max")
    k.expect(a.get("memory_max") == mem.strip(), "memory_max", f"you wrote {a.get('memory_max')!r}")
    _, cpu = k.exec("inspect", "cat", "/sys/fs/cgroup/cpu.max")
    k.expect(a.get("cpu_max") == cpu.strip(), "cpu_max", f"you wrote {a.get('cpu_max')!r}")
    node = k.jp("pod", "inspect", "{.spec.nodeName}")
    uid = k.jp("pod", "inspect", "{.metadata.uid}")
    pid_node = a.get("pid_on_node", "")
    ok = False
    if pid_node.isdigit():
        code, out = k.ssh(node, f"cat /proc/{pid_node}/cmdline | tr '\\0' ' '; echo; cat /proc/{pid_node}/cgroup")
        ok = code == 0 and "app.py" in out and uid.replace("-", "_") in out.replace("-", "_")
    k.expect(ok, "pid_on_node: that PID on the node is this pod's python process", f"you wrote {pid_node!r}")
