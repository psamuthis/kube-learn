from kube import labels

KUSTOMIZE = "base"

# HINT: `resources:` lists the files; `labels:` is a list of `{pairs: {…}, includeSelectors: true|false}`.


def check(k):
    d = k.get("deployment", "shop")
    k.require(d is not None, "the Deployment `shop` exists")
    k.expect(labels(d).get("app.kubernetes.io/name") == "shop", "the Deployment has app.kubernetes.io/name=shop")
    k.expect(labels(d).get("app.kubernetes.io/part-of") == "kube-learn", "…and app.kubernetes.io/part-of=kube-learn")
    sel = d["spec"]["selector"]["matchLabels"]
    k.expect(sel.get("app.kubernetes.io/name") == "shop", "the selector includes app.kubernetes.io/name", f"{sel}")
    k.expect("app.kubernetes.io/part-of" not in sel, "the selector doesn't include part-of", f"{sel}")
    tmpl = d["spec"]["template"]["metadata"]["labels"]
    k.expect(tmpl.get("app.kubernetes.io/name") == "shop", "the pod template has app.kubernetes.io/name")
    svc = k.get("service", "shop")
    k.expect(svc["spec"]["selector"].get("app.kubernetes.io/name") == "shop", "the Service selector includes it too")
    k.require(k.rollout("shop"), "the Deployment is rolled out")
    status, _ = k.http("http://shop/")
    k.expect(status == 200, "http://shop/ works (selectors still match)")
