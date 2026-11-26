import json

# HINT: Compare the Service's selector with the pods' labels, character by character.
# HINT: Once there are endpoints, look at their port: is anything listening there in the pod?


def check(k):
    k.require(k.rollout("api"), "the Deployment is rolled out")
    slices = k.items("endpointslices", "kubernetes.io/service-name=api")
    eps = [e for s in slices for e in s.get("endpoints") or []]
    k.expect(len(eps) == 2, "the Service has 2 endpoints", f"{len(eps)} endpoints")
    status, body = k.http("http://api/")
    k.expect(status == 200 and json.loads(body).get("message") == "api is up", "http://api/ answers", body[:200])
