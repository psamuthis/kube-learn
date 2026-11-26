import json
import shutil
import subprocess

from ingress import fetch
from kube import labels

APPLY = None

# HINT: `{{- define "kubeapp.fullname" -}}{{ printf "%s-%s" .Release.Name .Chart.Name }}{{- end }}`
# HINT: Indentation: `{{- include "kubeapp.labels" . | nindent 4 }}` puts the snippet on new lines indented by 4.
# HINT: Wrap the whole ingress.yaml in `{{- if .Values.ingress.enabled }} … {{- end }}`.

HOST = "chart.ex154.kube-learn.test"
SET = f"replicaCount=3,message=hi from helm,ingress.enabled=true,ingress.host={HOST}"


def helm(k, *args):
    chart = str(k.dir / "chart")
    if shutil.which("helm"):
        cmd = ["helm", *[a.replace("@CHART", chart) for a in args]]
    else:
        cmd = ["docker", "run", "--rm", "-v", f"{chart}:/chart:ro", "alpine/helm:3.19.0",
               *[a.replace("@CHART", "/chart") for a in args]]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=180)


def check(k):
    p = helm(k, "lint", "@CHART")
    k.require(p.returncode == 0, "`helm lint chart` passes", (p.stdout + p.stderr)[-1500:])
    p = helm(k, "template", "web", "@CHART")
    k.require(p.returncode == 0, "the chart renders with default values", p.stderr[-1500:])
    k.expect("kind: Ingress" not in p.stdout, "default values render no Ingress")
    p = helm(k, "template", "web", "@CHART", "--namespace", k.ns, "--set", SET)
    k.require(p.returncode == 0, "the chart renders with the test values", p.stderr[-1500:])
    code, out, err = k.try_kubectl("apply", "-f", "-", input=p.stdout)
    k.require(code == 0, "the rendered manifests apply", err)
    d = k.get("deployment", "web-kubeapp")
    k.require(d is not None, "the Deployment is named web-kubeapp")
    k.expect_eq(d["spec"]["replicas"], 3, "replicas")
    lab = labels(d)
    k.expect(lab.get("app.kubernetes.io/instance") == "web" and lab.get("helm.sh/chart") == "kubeapp-0.1.0",
             "standard labels (instance, helm.sh/chart)", f"{lab}")
    k.expect(d["spec"]["template"]["spec"]["containers"][0]["image"] == "kubeapp:1.0", "the image tag defaults to appVersion")
    k.require(k.rollout("web-kubeapp", timeout=90), "the Deployment is rolled out")
    k.require(k.get("ingress", "web-kubeapp") is not None, "an Ingress web-kubeapp exists")
    status, body = fetch(k, HOST, "/")
    k.expect(status == 200 and json.loads(body).get("message") == "hi from helm", f"http://{HOST}/ answers `hi from helm`",
             f"HTTP {status} {body[:200]}")
