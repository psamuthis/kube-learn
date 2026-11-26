"""`./course`: the runner for this course.

It's standard library Python only, so you can read it start to finish. It
mirrors `cargo course` from rust-learn:

* The **source of truth** is `solutions/chNN-*/NN-*/`. `generate` copies each one
  to `exercises/`, replacing every region

      #>>
      #| stub line(s) shown to the learner (optional, defaults to nothing)
      solution lines
      #<<

  with its stub lines, and dropping `# HINT:` lines (`./course hint` prints them).
  A file that's empty after this (a "write it from scratch" file) isn't copied.

* **Checking** an exercise means: make sure the namespace `ex-N-M` exists (running
  `setup(k)` from check.py the first time), `kubectl apply` its manifests, then
  call `check(k)` from its `check.py`. See `runner/kube.py` for what `k` offers.
"""

from __future__ import annotations

import fnmatch
import importlib.util
import os
import shutil
import subprocess
import sys
import time
import traceback
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kube  # noqa: E402
from kube import BOLD, DIM, GREEN, RED, RESET, Kube, KubectlError, CheckFailed  # noqa: E402

YELLOW = "\033[33m"
CYAN = "\033[36m"

ROOT = Path(__file__).resolve().parent.parent
SOLUTIONS = ROOT / "solutions"
EXERCISES = ROOT / "exercises"
PROGRESS = ROOT / ".course-progress"
PROFILE = kube.PROFILE

# Files that go through the marker transform (they all use `#` comments).
TRANSFORM_SUFFIXES = {".yaml", ".yml", ".py", ".txt", ".sh", ".conf", ".toml", ".tpl", ".cfg", ""}
SKIP_NAMES = {"__pycache__", ".DS_Store"}
SKIP_SUFFIXES = {".key", ".crt", ".csr", ".kubeconfig"}  # credentials made while verifying: never copy them

CLUSTER_START = [
    "minikube", "start", "-p", PROFILE, "--nodes", "3", "--cni", "calico",
    "--cpus", "2", "--memory", "3g", "--driver", "docker", "--container-runtime", "containerd",
]
ADDONS = ["ingress", "metrics-server", "storage-provisioner-rancher"]


# --------------------------------------------------------------------- model
@dataclass
class Exercise:
    id: str            # "5.1"
    chapter: str       # "ch05-deployments"
    name: str          # "01-first-deployment"
    solution_dir: Path
    exercise_dir: Path

    @property
    def ns(self) -> str:
        return "ex-" + self.id.replace(".", "-")

    @property
    def label(self) -> str:
        return f"{self.id:>5}  {self.name}"


def leading_number(s: str) -> int | None:
    digits = ""
    for c in s:
        if not c.isdigit():
            break
        digits += c
    return int(digits) if digits else None


def discover() -> list[Exercise]:
    out = []
    if not SOLUTIONS.exists():
        return out
    for chapter_dir in sorted(p for p in SOLUTIONS.iterdir() if p.is_dir()):
        ch = chapter_dir.name
        if not ch.startswith("ch") or leading_number(ch[2:]) is None:
            continue
        ch_num = leading_number(ch[2:])
        for ex_dir in sorted(p for p in chapter_dir.iterdir() if p.is_dir()):
            if not (ex_dir / "check.py").exists():
                continue
            n = leading_number(ex_dir.name)
            if n is None:
                continue
            out.append(Exercise(f"{ch_num}.{n}", ch, ex_dir.name, ex_dir, EXERCISES / ch / ex_dir.name))
    return out


def find(all_: list[Exercise], query: str) -> Exercise:
    for e in all_:
        if e.id == query:
            return e
    matches = [e for e in all_ if query in e.name or query in f"{e.chapter}/{e.name}"]
    if len(matches) == 1:
        return matches[0]
    if not matches:
        die(f"no exercise matches `{query}` (try `./course list`)")
    die(f"`{query}` is ambiguous: " + ", ".join(f"{e.id} ({e.name})" for e in matches))


def die(msg: str):
    print(f"{RED}error:{RESET} {msg}")
    sys.exit(1)


# ------------------------------------------------------------------ progress
def load_progress() -> set[str]:
    if not PROGRESS.exists():
        return set()
    return {l.strip() for l in PROGRESS.read_text().splitlines() if l.strip()}


def save_progress(done: set[str]):
    def key(i):
        a, b = i.split(".")
        return int(a), int(b)
    PROGRESS.write_text("".join(f"{i}\n" for i in sorted(done, key=key)))


def mark_done(ex: Exercise, ok: bool):
    done = load_progress()
    (done.add if ok else done.discard)(ex.id)
    save_progress(done)


def next_todo(all_: list[Exercise], after: Exercise | None = None) -> Exercise | None:
    done = load_progress()
    started = after is None
    for e in all_:
        if not started:
            started = e.id == after.id
            continue
        if e.id not in done:
            return e
    return None


# ----------------------------------------------------------------- transform
def transform(src: str) -> str:
    out: list[str] = []
    in_region = False
    stub: list[str] = []
    for line in src.splitlines():
        trimmed = line.lstrip()
        indent = line[: len(line) - len(trimmed)]
        if trimmed.startswith("# HINT:"):
            continue
        if trimmed.startswith("#>>"):
            in_region, stub = True, []
            continue
        if trimmed.startswith("#<<"):
            in_region = False
            out.extend(stub)
            continue
        if in_region:
            if trimmed.startswith("#|"):
                rest = trimmed[2:]
                rest = rest[1:] if rest.startswith(" ") else rest
                stub.append(f"{indent}{rest}" if rest else "")
            continue
        out.append(line)
    return "\n".join(out) + ("\n" if out else "")


def hints(ex: Exercise) -> list[str]:
    found = []
    for path in sorted(ex.solution_dir.rglob("*")):
        if path.is_file() and transformable(path):
            for line in path.read_text().splitlines():
                t = line.strip()
                if t.startswith("# HINT:"):
                    found.append(t[len("# HINT:"):].strip())
    return found


def transformable(p: Path) -> bool:
    return p.suffix in TRANSFORM_SUFFIXES or p.name == "Dockerfile"


def generate_one(ex: Exercise):
    if ex.exercise_dir.exists():
        shutil.rmtree(ex.exercise_dir)
    for src in sorted(ex.solution_dir.rglob("*")):
        rel = src.relative_to(ex.solution_dir)
        if any(part in SKIP_NAMES for part in rel.parts) or src.is_dir() or src.suffix in SKIP_SUFFIXES:
            continue
        dst = ex.exercise_dir / rel
        if transformable(src):
            text = transform(src.read_text())
            if not text.strip():
                continue  # written from scratch by the learner
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(text)
            shutil.copymode(src, dst)
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
    ex.exercise_dir.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------------------------- check
def load_check_module(directory: Path):
    path = directory / "check.py"
    if not path.exists():
        die(f"{path} is missing (try `./course reset`)")
    spec = importlib.util.spec_from_file_location(f"check_{abs(hash(str(path)))}", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def namespace_exists(ns: str) -> bool:
    return kube.kubectl_raw("get", "namespace", ns).returncode == 0


def delete_namespace(ns: str, wait: bool = True):
    kube.kubectl_raw("delete", "namespace", ns, "--ignore-not-found", f"--wait={str(wait).lower()}",
                     timeout=300)


def ensure_namespace(ex: Exercise, mod, k: Kube):
    if namespace_exists(ex.ns):
        phase = kube.kubectl_raw("get", "namespace", ex.ns, "-o", "jsonpath={.status.phase}").stdout
        if phase != "Terminating":
            return
        print(f"  {DIM}waiting for the old namespace {ex.ns} to finish terminating…{RESET}")
        k.wait_for(lambda: not namespace_exists(ex.ns), timeout=240, what="namespace deletion")
    k.kubectl("create", "namespace", ex.ns, ns=False)
    k.kubectl("label", "namespace", ex.ns, f"kube-learn/exercise={ex.id}", ns=False)
    if hasattr(mod, "setup"):
        print(f"  {DIM}setting up the exercise…{RESET}")
        mod.setup(k)


def manifests(directory: Path, mod) -> list[Path]:
    patterns = getattr(mod, "APPLY", ["*.yaml", "*.yml"])
    if patterns is None:
        return []
    files = []
    for pat in patterns:
        files += sorted(p for p in directory.glob(pat) if p.is_file())
    return files


def run_check(ex: Exercise, directory: Path | None = None, fresh: bool = False, verbose: bool = False) -> bool:
    directory = directory or ex.exercise_dir
    print(f"{BOLD}{CYAN}━━ {ex.id} {ex.chapter}/{ex.name}{RESET}  {DIM}(namespace {ex.ns}){RESET}")
    if not directory.exists():
        print(f"  {RED}✗ {directory} doesn't exist. Run `./course generate` first.{RESET}")
        return False
    if not cluster_reachable():
        print(f"  {RED}✗ can't reach the cluster. Is it running? Try `./course cluster up`.{RESET}")
        return False
    try:
        mod = load_check_module(directory)
    except Exception:
        print(f"  {RED}✗ check.py doesn't load:{RESET}\n{traceback.format_exc()}")
        return False
    k = Kube(ex.ns, directory, ex.id, verbose=verbose)
    k.solution = directory.resolve() == ex.solution_dir.resolve()
    try:
        if fresh:
            print(f"  {DIM}deleting namespace {ex.ns} for a fresh start…{RESET}")
            reset_cluster_state(ex, mod, k)
        ensure_namespace(ex, mod, k)

        kust = getattr(mod, "KUSTOMIZE", None)
        if kust:
            if not (directory / kust).exists():
                k.require(False, f"{kust}/ exists")
            code, out, err = k.try_kubectl("apply", "-k", str(directory / kust))
            k.require(code == 0, f"`kubectl apply -k {kust}` succeeds", err or out)
            k.info(out.strip().replace("\n", "\n    "))
        files = manifests(directory, mod)
        if files:
            args = ["apply"] + sum((["-f", str(f)] for f in files), [])
            if getattr(mod, "SERVER_SIDE", False):
                args.append("--server-side")
            code, out, err = k.try_kubectl(*args)
            if code != 0 and "immutable" not in err and "may not change" not in err:
                # Objects in one file may depend on objects in another (a pod on its ServiceAccount,
                # a custom resource on its CRD): a second pass usually resolves the ordering.
                time.sleep(2)
                code, out, err = k.try_kubectl(*args)
            if code != 0 and ("immutable" in err or "may not change" in err):
                err += ("\nSome fields can't be changed on a live object. Delete it first, or start over with "
                        f"`./course check {ex.id} --fresh`.")
            k.require(code == 0, "`kubectl apply` of " + ", ".join(f.name for f in files) + " succeeds",
                      err or out)
            for line in out.strip().splitlines():
                k.info(line)
        elif getattr(mod, "APPLY", ["*.yaml"]) is not None and not kust:
            k.require(False, "there are manifests (*.yaml) to apply",
                      f"write them in {directory.relative_to(ROOT)}/ (see README.md there)")
        mod.check(k)
    except CheckFailed:
        pass
    except KubectlError as e:
        k.expect(False, "kubectl call succeeds", str(e))
    except subprocess.TimeoutExpired as e:
        k.expect(False, "command finished in time", str(e))
    except Exception:
        k.expect(False, "check ran without crashing", traceback.format_exc())
    ok = k.failures == 0
    if ok:
        print(f"{GREEN}{BOLD}✓ {ex.id} passed{RESET} {DIM}({k.passes} checks){RESET}")
    else:
        print(f"{RED}{BOLD}✗ {ex.id}: {k.failures} check(s) failed{RESET}  "
              f"{DIM}(README: {ex.exercise_dir.relative_to(ROOT)}/README.md · hint: ./course hint {ex.id}){RESET}")
    return ok


def reset_cluster_state(ex: Exercise, mod, k: Kube):
    if hasattr(mod, "cleanup"):
        try:
            mod.cleanup(k)
        except Exception as e:  # cleanup is best-effort
            print(f"  {DIM}cleanup: {e}{RESET}")
    delete_namespace(ex.ns)


def cluster_reachable() -> bool:
    try:
        return kube.kubectl_raw("version", "--request-timeout=5s", timeout=15).returncode == 0
    except subprocess.TimeoutExpired:
        return False


# ------------------------------------------------------------------ commands
def cmd_list(all_: list[Exercise]):
    done = load_progress()
    current = ""
    first_todo = True
    for e in all_:
        if e.chapter != current:
            current = e.chapter
            print(f"\n{BOLD}{e.chapter}{RESET}")
        if e.id in done:
            mark = f"{GREEN}✓{RESET}"
        elif first_todo:
            mark, first_todo = f"{YELLOW}→{RESET}", False
        else:
            mark = " "
        print(f"  {mark} {e.label}")
    print(f"\n{len(done & {e.id for e in all_})}/{len(all_)} done")


def cmd_check(ex: Exercise, fresh: bool, verbose: bool) -> bool:
    ok = run_check(ex, fresh=fresh, verbose=verbose)
    mark_done(ex, ok)
    if ok:
        print(f"{DIM}The namespace {ex.ns} is still there for you to look around. "
              f"`./course clean {ex.id}` removes it.{RESET}")
    return ok


def snapshot(directory: Path) -> dict[str, float]:
    if not directory.exists():
        return {}
    return {str(p): p.stat().st_mtime for p in directory.rglob("*") if p.is_file()}


def cmd_watch(all_: list[Exercise], start: Exercise | None, verbose: bool):
    ex = start or next_todo(all_)
    if ex is None:
        print(f"{GREEN}Everything is done!{RESET}")
        return
    while True:
        print("\033[2J\033[H", end="")
        ok = run_check(ex, verbose=verbose)
        mark_done(ex, ok)
        if ok:
            print(f"\nPress {BOLD}Enter{RESET} for the next exercise "
                  f"(k + Enter keeps namespace {ex.ns}, q + Enter quits): ", end="", flush=True)
            line = sys.stdin.readline().strip().lower()
            if line != "k":
                delete_namespace(ex.ns, wait=False)
            if line == "q":
                return
            nxt = next_todo(all_, ex) or next_todo(all_)
            if nxt is None:
                print(f"{GREEN}{BOLD}Everything is done! 🎉{RESET}")
                return
            ex = nxt
            continue
        print(f"\n{DIM}Watching {ex.exercise_dir.relative_to(ROOT)}/ — save a file to re-check. "
              f"Ctrl-C to quit. (Cluster changes aren't watched: save any file, or press Enter.){RESET}")
        before = snapshot(ex.exercise_dir)
        try:
            while True:
                time.sleep(0.5)
                if snapshot(ex.exercise_dir) != before or stdin_has_enter():
                    break
        except KeyboardInterrupt:
            print()
            return


def stdin_has_enter() -> bool:
    import select
    try:
        r, _, _ = select.select([sys.stdin], [], [], 0)
    except (OSError, ValueError):
        return False
    if r:
        sys.stdin.readline()
        return True
    return False


def cmd_hint(ex: Exercise):
    hs = hints(ex)
    if not hs:
        print("No hints for this one. Re-read the chapter section and the README!")
        return
    print(f"{BOLD}Hints for {ex.id} {ex.name}{RESET} (Enter for the next one, q to stop)")
    for i, h in enumerate(hs, 1):
        print(f"  {YELLOW}{i}.{RESET} {h}", end="")
        if i < len(hs):
            if sys.stdin.isatty():
                if sys.stdin.readline().strip().lower() == "q":
                    return
            else:
                print()
        else:
            print()


def confirm(question: str) -> bool:
    print(f"{question} [y/N] ", end="", flush=True)
    return sys.stdin.readline().strip().lower() in ("y", "yes")


def cmd_reset(ex: Exercise):
    if not confirm(f"Reset {ex.exercise_dir.relative_to(ROOT)} to its initial state? Your work there is lost."):
        return
    generate_one(ex)
    delete_namespace(ex.ns, wait=False)
    mark_done(ex, False)
    print(f"{GREEN}Reset {ex.id}.{RESET}")


def cmd_generate(all_: list[Exercise], force: bool):
    created = 0
    for e in all_:
        if e.exercise_dir.exists() and not force:
            continue
        generate_one(e)
        created += 1
    print(f"Generated {created} exercise(s) in exercises/." +
          ("" if force else " (Existing ones were left alone; --force overwrites everything.)"))


def cmd_clean(all_: list[Exercise], target: str | None):
    targets = all_ if target in (None, "--all") else [find(all_, target)]
    for e in targets:
        if namespace_exists(e.ns):
            print(f"deleting namespace {e.ns}")
            try:
                mod = load_check_module(e.exercise_dir if e.exercise_dir.exists() else e.solution_dir)
                if hasattr(mod, "cleanup"):
                    mod.cleanup(Kube(e.ns, e.exercise_dir, e.id))
            except Exception as err:
                print(f"  {DIM}cleanup: {err}{RESET}")
            delete_namespace(e.ns, wait=False)


def cmd_verify(all_: list[Exercise], solutions: bool, only: str | None, verbose: bool):
    chosen = all_
    if only:
        chosen = [e for e in all_ if e.id == only or e.id.startswith(only.rstrip(".") + ".")
                  or e.chapter.startswith(only)]
    failed = []
    t0 = time.time()
    for e in chosen:
        directory = e.solution_dir if solutions else e.exercise_dir
        ok = run_check(e, directory=directory, fresh=solutions, verbose=verbose)
        if not solutions:
            mark_done(e, ok)
        else:
            try:
                reset_cluster_state(e, load_check_module(directory), Kube(e.ns, directory, e.id))
            except Exception:
                delete_namespace(e.ns, wait=False)
        if not ok:
            failed.append(e)
        print()
    took = int(time.time() - t0)
    print(f"{BOLD}{len(chosen) - len(failed)}/{len(chosen)} passed{RESET} in {took // 60}m{took % 60:02d}s")
    for e in failed:
        print(f"  {RED}✗{RESET} {e.id} {e.chapter}/{e.name}")
    sys.exit(1 if failed else 0)


def cmd_solution(ex: Exercise):
    print(f"The reference solution is in {BOLD}{ex.solution_dir.relative_to(ROOT)}/{RESET}")
    print(f"{DIM}Regions between `#>>` and `#<<` are what you had to write; `#|` lines are the stub.{RESET}")
    print(f"{DIM}To check the reference solution itself: ./course verify --solutions {ex.id}{RESET}")


# ------------------------------------------------------------------- cluster
def sh(cmd: list[str], check: bool = True) -> int:
    print(f"{DIM}$ {' '.join(cmd)}{RESET}")
    code = subprocess.call(cmd)
    if check and code != 0:
        die(f"`{' '.join(cmd)}` failed with exit code {code}")
    return code


def build_images():
    """Builds every app in apps/ that has an IMAGES file (one `name:tag [build-arg=value…]` per line)
    and loads it onto every node of the cluster."""
    for app in sorted((ROOT / "apps").iterdir()):
        spec = app / "IMAGES"
        if not spec.exists():
            continue
        for line in spec.read_text().splitlines():
            line = line.split("#", 1)[0].strip()
            if not line:
                continue
            tag, *build_args = line.split()
            cmd = ["docker", "build", "-q", "-t", tag]
            for a in build_args:
                cmd += ["--build-arg", a]
            sh(cmd + [str(app)])
            sh(["minikube", "-p", PROFILE, "image", "load", tag])


def cmd_cluster(args: list[str]):
    sub = args[0] if args else "status"
    if sub == "up":
        nodes = "1" if "--single" in args else "3"
        start = list(CLUSTER_START)
        start[start.index("--nodes") + 1] = nodes
        sh(start)
        # Calico's images are big: wait for the network before enabling addons, which time out otherwise.
        print(f"{DIM}waiting for the pod network (calico) to be ready on every node…{RESET}")
        sh(["kubectl", "-n", "kube-system", "rollout", "status", "daemonset/calico-node", "--timeout=15m"], check=False)
        sh(["kubectl", "-n", "kube-system", "rollout", "status", "deployment/coredns", "--timeout=5m"], check=False)
        for a in ADDONS:
            if sh(["minikube", "-p", PROFILE, "addons", "enable", a], check=False) != 0:
                print(f"{YELLOW}addon {a} didn't become ready in time; retrying once…{RESET}")
                sh(["minikube", "-p", PROFILE, "addons", "enable", a], check=False)
        build_images()
        sh(["kubectl", "get", "nodes", "-o", "wide"])
    elif sub == "images":
        build_images()
    elif sub == "down":
        sh(["minikube", "-p", PROFILE, "stop"])
    elif sub == "delete":
        if confirm(f"Delete the minikube profile `{PROFILE}` and everything in it?"):
            sh(["minikube", "-p", PROFILE, "delete"])
    elif sub == "status":
        sh(["minikube", "-p", PROFILE, "status"], check=False)
    else:
        die("usage: ./course cluster up [--single] | down | delete | status | images")


USAGE = f"""{BOLD}./course{RESET} — the kube-learn runner

  list                    progress overview (✓ done, → current)
  watch [ID]              re-checks the current exercise every time you save; Enter moves on
  next                    checks the first unfinished exercise once
  check ID [--fresh]      checks one exercise (ID is chapter.exercise, or part of a name)
                          --fresh deletes its namespace first (and re-runs its setup)
  hint ID                 progressive hints
  reset ID                restores an exercise's files to their initial state (asks first)
  solution ID             where the reference solution is
  clean [ID|--all]        deletes exercise namespaces to free the cluster
  verify [--solutions] [CH|ID]
                          re-checks everything (or one chapter) and refreshes progress;
                          --solutions checks the reference solutions instead
  generate [--force]      (re)builds exercises/ from solutions/ (--force ERASES your work)
  cluster up [--single] | down | delete | status | images
                          manages the minikube profile `{PROFILE}`

  -v / --verbose          print every kubectl command a check runs
"""


def main(argv: list[str]):
    sys.stdout.reconfigure(line_buffering=True)  # progress shows up promptly even when piped
    verbose = any(a in ("-v", "--verbose") for a in argv)
    argv = [a for a in argv if a not in ("-v", "--verbose")]
    if not argv or argv[0] in ("-h", "--help", "help"):
        print(USAGE)
        return
    cmd, rest = argv[0], argv[1:]
    if cmd == "cluster":
        return cmd_cluster(rest)
    all_ = discover()
    if cmd == "generate":
        return cmd_generate(all_, "--force" in rest)
    if cmd == "list":
        return cmd_list(all_)
    if cmd == "watch":
        return cmd_watch(all_, find(all_, rest[0]) if rest else None, verbose)
    if cmd == "next":
        ex = next_todo(all_)
        if ex is None:
            print(f"{GREEN}Everything is done!{RESET}")
            return
        sys.exit(0 if cmd_check(ex, False, verbose) else 1)
    if cmd == "verify":
        sols = "--solutions" in rest
        only = next((a for a in rest if not a.startswith("--")), None)
        return cmd_verify(all_, sols, only, verbose)
    if cmd == "clean":
        return cmd_clean(all_, rest[0] if rest else None)
    if not rest:
        die(f"`{cmd}` needs an exercise ID (see `./course list`)")
    ex = find(all_, rest[0])
    if cmd == "check":
        sys.exit(0 if cmd_check(ex, "--fresh" in rest, verbose) else 1)
    elif cmd == "hint":
        cmd_hint(ex)
    elif cmd == "reset":
        cmd_reset(ex)
    elif cmd == "solution":
        cmd_solution(ex)
    else:
        die(f"unknown command `{cmd}`\n\n{USAGE}")


if __name__ == "__main__":
    try:
        main(sys.argv[1:])
    except KeyboardInterrupt:
        print()
        sys.exit(130)
