import json
import re

APPLY = None

# HINT: `openssl x509 -noout -issuer -enddate -ext subjectAltName -in …`
# HINT: `kubectl auth whoami` prints your username and groups.
# HINT: Kubelets authenticate as system:node:<node name> in the group system:nodes.


def check(k):
    a = k.answers()
    cp = k.node_names()[0]
    _, text = k.ssh(cp, "sudo openssl x509 -in /var/lib/minikube/certs/apiserver.crt -noout -issuer -enddate -ext subjectAltName")
    issuer = re.search(r"issuer=.*CN\s*=\s*([^,\n]+)", text).group(1).strip()
    year = re.search(r"notAfter=\w+\s+\d+\s+[\d:]+\s+(\d{4})", text).group(1)
    svc_ip = k.jp("service", "kubernetes", "{.spec.clusterIP}", ns="default")
    k.expect_eq(a.get("apiserver_issuer"), issuer, "apiserver_issuer")
    k.expect(a.get("service_ip_san") == svc_ip and f"IP Address:{svc_ip}" in text, "service_ip_san",
             f"you wrote {a.get('service_ip_san')!r}")
    k.expect_eq(a.get("apiserver_expiry_year"), year, "apiserver_expiry_year")
    who = json.loads(k.kubectl("auth", "whoami", "-o", "json", ns=False))["status"]["userInfo"]
    k.expect_eq(a.get("my_user"), who["username"], "my_user")
    k.expect(a.get("my_admin_group") == "system:masters" and "system:masters" in who.get("groups", []), "my_admin_group",
             f"you wrote {a.get('my_admin_group')!r}")
    if "kube-learn-m02" in k.node_names():
        _, sub = k.ssh("kube-learn-m02", "sudo openssl x509 -in /var/lib/kubelet/pki/kubelet-client-current.pem -noout -subject")
        cn = re.search(r"CN\s*=\s*(\S+)", sub).group(1)
        k.expect_eq(a.get("kubelet_m02_user"), cn, "kubelet_m02_user")
