import re

# HINT: kube-proxy logs a line like "Using iptables Proxier" at start-up. An empty `mode:` in its config means the default.
# HINT: Each Service has a `-A KUBE-SERVICES … --comment "ns/name:port cluster IP" … -j KUBE-SVC-XXXX` rule.
# HINT: With 2 endpoints, the first jump has probability 0.5 (the last one has no probability: it catches the rest).


def check(k):
    k.require(k.rollout("web"), "the Deployment is rolled out")
    node = k.node_names()[0]
    # kube-proxy syncs a moment after the endpoints become ready: wait until both are in the rules
    rules = k.wait_for(lambda: (r := k.ssh(node, "sudo iptables-save -t nat")[1]).count("ex-7-6/web:http ->") >= 2 and r,
                       timeout=30) or k.ssh(node, "sudo iptables-save -t nat")[1]
    a = k.answers()
    m = re.search(r'-A KUBE-SERVICES .*"ex-7-6/web:http cluster IP".*-j (KUBE-SVC-\w+)', rules)
    k.require(m, "kube-proxy has a rule for the Service")
    chain = m.group(1)
    jumps = re.findall(rf"^-A {chain} .*-j (KUBE-SEP-\w+)", rules, re.M)
    probs = re.findall(rf"^-A {chain} .*--probability (\S+)", rules, re.M)
    k.expect_eq(a.get("mode"), "iptables", "mode")
    k.expect_eq(a.get("svc_chain"), chain, "svc_chain")
    k.expect_eq(a.get("endpoints"), str(len(jumps)), "endpoints")
    k.expect(probs and a.get("first_probability") == probs[0], "first_probability", f"you wrote {a.get('first_probability')!r}")
    targets = set(re.findall(r"-j DNAT --to-destination (\S+)", "\n".join(
        l for l in rules.splitlines() if "ex-7-6/web:http" in l)))
    k.expect(a.get("one_dnat_target") in targets, "one_dnat_target is one of the DNAT destinations", f"they are {sorted(targets)}")
