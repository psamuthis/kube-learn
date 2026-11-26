"""kubeapp — the demo application used throughout the course.

A small HTTP server (standard library only) with endpoints to poke at
Kubernetes features: probes, crashes, CPU/memory load, config files,
environment, persistent counters and a Redis-backed guestbook.

    GET  /               JSON: app, version, hostname, message, color
    GET  /healthz        liveness: 200, or 500 after /break
    GET  /break          makes /healthz fail from now on
    GET  /ready          readiness: 503 for READY_DELAY seconds after start, or while toggled off
    GET  /toggle-ready   flips readiness
    GET  /crash          exits the process with status 1
    GET  /cpu?ms=N       burns N ms of CPU (default 200)
    GET  /mem?mb=N       allocates and keeps N MiB (default 50)
    GET  /env            environment variables (values of *SECRET*/*PASSWORD* vars are masked)
    GET  /config         every file under CONFIG_DIR (default /config) with its content
    GET  /hits           increments and returns a counter: in Redis if REDIS_HOST is set,
                         else in DATA_DIR/hits if DATA_DIR is set, else in memory
    GET  /guestbook      entries; POST /guestbook (body = text) adds one (Redis or DATA_DIR)
    GET  /headers        the request headers
    GET  /hostname       just the hostname

Environment: PORT (8080), APP_VERSION, MESSAGE, COLOR, READY_DELAY (0),
SHUTDOWN_DELAY (0, seconds to keep serving after SIGTERM), CONFIG_DIR,
DATA_DIR, REDIS_HOST, REDIS_PORT (6379), REDIS_PASSWORD.
"""

import json
import os
import signal
import socket
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

START = time.time()
STATE = {"healthy": True, "ready_override": True, "hits": 0, "hoard": [], "terminating": False}
LOCK = threading.Lock()


def env(name, default=""):
    return os.environ.get(name, default)


def log(msg):
    print(f"{time.strftime('%Y-%m-%dT%H:%M:%S')} {msg}", flush=True)


# ------------------------------------------------------------- tiny Redis client
class Redis:
    def __init__(self, host, port, password=""):
        self.addr = (host, int(port))
        self.password = password

    def cmd(self, *args):
        with socket.create_connection(self.addr, timeout=3) as s:
            f = s.makefile("rb")
            if self.password:
                s.sendall(self._encode("AUTH", self.password))
                self._read(f)
            s.sendall(self._encode(*args))
            return self._read(f)

    @staticmethod
    def _encode(*args):
        out = [f"*{len(args)}\r\n".encode()]
        for a in args:
            b = str(a).encode()
            out.append(f"${len(b)}\r\n".encode() + b + b"\r\n")
        return b"".join(out)

    def _read(self, f):
        line = f.readline().rstrip(b"\r\n")
        kind, rest = line[:1], line[1:]
        if kind == b"+":
            return rest.decode()
        if kind == b"-":
            raise RuntimeError(rest.decode())
        if kind == b":":
            return int(rest)
        if kind == b"$":
            n = int(rest)
            if n < 0:
                return None
            data = f.read(n + 2)[:-2]
            return data.decode()
        if kind == b"*":
            return [self._read(f) for _ in range(int(rest))]
        raise RuntimeError(f"bad redis reply {line!r}")


def redis():
    host = env("REDIS_HOST")
    # A Service named `redis` makes Kubernetes inject REDIS_PORT=tcp://10.x.y.z:6379 into every
    # pod of the namespace (the legacy "service links" env vars), so accept that form too.
    port = env("REDIS_PORT", "6379").rsplit(":", 1)[-1]
    return Redis(host, port, env("REDIS_PASSWORD")) if host else None


def data_dir():
    d = env("DATA_DIR")
    if d:
        Path(d).mkdir(parents=True, exist_ok=True)
        return Path(d)
    return None


# ---------------------------------------------------------------------- handler
class Handler(BaseHTTPRequestHandler):
    server_version = "kubeapp"
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):
        log(f"{self.client_address[0]} {fmt % args}")

    def send(self, code, body, ctype="application/json"):
        if not isinstance(body, (str, bytes)):
            body = json.dumps(body, indent=2) + "\n"
        if isinstance(body, str):
            body = body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        url = urlparse(self.path)
        q = parse_qs(url.query)
        route = {
            "/": self.index, "/healthz": self.healthz, "/break": self.break_,
            "/ready": self.ready, "/toggle-ready": self.toggle_ready, "/crash": self.crash,
            "/cpu": lambda: self.cpu(q), "/mem": lambda: self.mem(q), "/env": self.env,
            "/config": self.config, "/hits": self.hits, "/guestbook": self.guestbook_get,
            "/headers": lambda: self.send(200, dict(self.headers)),
            "/hostname": lambda: self.send(200, socket.gethostname() + "\n", "text/plain"),
        }.get(url.path.rstrip("/") or "/")
        if route is None:
            self.send(404, {"error": "not found", "path": url.path})
        else:
            try:
                route()
            except Exception as e:  # report backend errors as 502 instead of dropping the socket
                self.send(502, {"error": str(e)})

    def do_POST(self):
        if urlparse(self.path).path.rstrip("/") == "/guestbook":
            n = int(self.headers.get("Content-Length") or 0)
            text = self.rfile.read(n).decode(errors="replace").strip() or "(empty)"
            try:
                self.guestbook_add(text)
            except Exception as e:
                return self.send(502, {"error": str(e)})
            return self.send(201, {"added": text})
        self.send(404, {"error": "not found"})

    # -- endpoints
    def index(self):
        self.send(200, {
            "app": "kubeapp",
            "version": env("APP_VERSION", "dev"),
            "hostname": socket.gethostname(),
            "message": env("MESSAGE", "hello from kubeapp"),
            "color": env("COLOR", "blue"),
            "uptime_s": round(time.time() - START, 1),
        })

    def healthz(self):
        if STATE["healthy"]:
            self.send(200, "ok\n", "text/plain")
        else:
            self.send(500, "broken\n", "text/plain")

    def break_(self):
        STATE["healthy"] = False
        log("/healthz will now fail")
        self.send(200, "healthz is now failing\n", "text/plain")

    def ready(self):
        delay = float(env("READY_DELAY", "0") or 0)
        warming = time.time() - START < delay
        if warming or not STATE["ready_override"] or STATE["terminating"]:
            why = "warming up" if warming else "terminating" if STATE["terminating"] else "toggled off"
            self.send(503, f"not ready ({why})\n", "text/plain")
        else:
            self.send(200, "ready\n", "text/plain")

    def toggle_ready(self):
        STATE["ready_override"] = not STATE["ready_override"]
        self.send(200, f"ready={STATE['ready_override']}\n", "text/plain")

    def crash(self):
        self.send(200, "crashing\n", "text/plain")
        log("crash requested, exiting with status 1")
        threading.Timer(0.1, lambda: os._exit(1)).start()

    def cpu(self, q):
        ms = int(q.get("ms", ["200"])[0])
        end = time.process_time() + ms / 1000
        x = 0
        while time.process_time() < end:
            x += 1
        self.send(200, {"burned_ms": ms})

    def mem(self, q):
        mb = int(q.get("mb", ["50"])[0])
        with LOCK:
            STATE["hoard"].append(bytearray(os.urandom(1)) * (mb * 1024 * 1024))
            total = sum(len(b) for b in STATE["hoard"]) // (1024 * 1024)
        log(f"now holding {total} MiB")
        self.send(200, {"holding_mib": total})

    def env(self):
        masked = {k: ("***" if any(s in k.upper() for s in ("SECRET", "PASSWORD", "TOKEN")) else v)
                  for k, v in sorted(os.environ.items())}
        self.send(200, masked)

    def config(self):
        root = Path(env("CONFIG_DIR", "/config"))
        files = {}
        if root.is_dir():
            # ConfigMap volumes are made of symlinks (key → ..data/key, ..data → ..<timestamp>):
            # follow them, but skip the hidden `..` plumbing itself.
            for dirpath, dirnames, filenames in os.walk(root, followlinks=True):
                dirnames[:] = sorted(d for d in dirnames if not d.startswith(".."))
                for name in sorted(filenames):
                    if name.startswith(".."):
                        continue
                    p = Path(dirpath) / name
                    rel = str(p.relative_to(root))
                    try:
                        files[rel] = p.read_text()
                    except (OSError, UnicodeDecodeError) as e:
                        files[rel] = f"<unreadable: {e}>"
        self.send(200, {"dir": str(root), "files": files})

    def hits(self):
        r = redis()
        if r:
            n, where = r.cmd("INCR", "hits"), f"redis {r.addr[0]}"
        elif data_dir():
            f = data_dir() / "hits"
            with LOCK:
                n = int(f.read_text() or 0) + 1 if f.exists() else 1
                f.write_text(str(n))
            where = str(f)
        else:
            with LOCK:
                STATE["hits"] += 1
                n = STATE["hits"]
            where = "memory"
        self.send(200, {"hits": n, "stored_in": where, "hostname": socket.gethostname()})

    def guestbook_get(self):
        r = redis()
        if r:
            entries = r.cmd("LRANGE", "guestbook", 0, -1)
        elif data_dir():
            f = data_dir() / "guestbook"
            entries = f.read_text().splitlines() if f.exists() else []
        else:
            entries = STATE.setdefault("guestbook", [])
        self.send(200, {"entries": entries})

    def guestbook_add(self, text):
        r = redis()
        if r:
            r.cmd("RPUSH", "guestbook", text)
        elif data_dir():
            with LOCK, open(data_dir() / "guestbook", "a") as f:
                f.write(text.replace("\n", " ") + "\n")
        else:
            STATE.setdefault("guestbook", []).append(text)


def main():
    port = int(env("PORT", "8080"))
    srv = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    srv.daemon_threads = True

    def on_term(signum, _frame):
        delay = float(env("SHUTDOWN_DELAY", "0") or 0)
        STATE["terminating"] = True
        log(f"got signal {signum}, draining for {delay}s then exiting")

        def stop():
            time.sleep(delay)
            srv.shutdown()
        threading.Thread(target=stop, daemon=True).start()

    signal.signal(signal.SIGTERM, on_term)
    signal.signal(signal.SIGINT, on_term)
    log(f"kubeapp {env('APP_VERSION', 'dev')} listening on :{port} (pid {os.getpid()})")
    srv.serve_forever()
    log("bye")
    sys.exit(0)


if __name__ == "__main__":
    main()
