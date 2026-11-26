import json
from collections import Counter



def check(k):
    d = k.get("deployment", "web-canary")
    k.require(d is not None, "a Deployment `web-canary` exists")
    k.expect_eq(d["spec"]["replicas"], 1, "canary replicas")
    sel = d["spec"]["selector"].get("matchLabels", {})
    k.expect(sel.get("track") not in (None, "stable"), "the canary's selector doesn't overlap the stable one", f"{sel}")
    k.require(k.rollout("web-canary") and k.rollout("web-stable"), "both Deployments are rolled out")
    k.expect(len(k.ready_pods("app=shop")) == 4, "the Service has 4 Ready pods behind it")
    seen = Counter()
    for _ in range(40):
        status, body = k.http("http://shop/")
        seen[json.loads(body).get("version") if status == 200 else f"HTTP {status}"] += 1
    k.expect(seen.get("1.0", 0) > 0 and seen.get("2.0", 0) > 0, "both versions answer through the Service", f"{dict(seen)}")
    k.info(f"traffic split over 40 requests: {dict(seen)}")
