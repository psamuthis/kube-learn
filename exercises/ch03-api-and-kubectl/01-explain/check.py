APPLY = None


EXPECTED = {
    "deployment_group": "apps",
    "pvc_short": "pvc",
    "node_namespaced": "false",
    "netpol_kind": "NetworkPolicy",
    "hpa_api_version": "autoscaling/v2",
    "cron_schedule_type": "string",
    "default_restart_policy": "Always",
    "pdb_resource": "poddisruptionbudgets",
}


def check(k):
    a = k.answers()
    for key, want in EXPECTED.items():
        got = a.get(key, "")
        k.expect(got.lower() == want.lower(), key, f"you wrote {got!r}")
