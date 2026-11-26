import re



def check(k):
    a = k.answers()
    _, conf = k.sh("cat /etc/resolv.conf")
    search = re.search(r"^search (.+)$", conf, re.M).group(1).split()
    ns = re.search(r"^nameserver (\S+)", conf, re.M).group(1)
    ndots = re.search(r"ndots:(\d+)", conf).group(1)
    k.expect_eq(a.get("first_search"), search[0], "first_search")
    k.expect_eq(a.get("nameserver"), ns, "nameserver")
    k.expect_eq(a.get("nameserver_service"), "kube-system/kube-dns", "nameserver_service")
    k.expect_eq(a.get("ndots"), ndots, "ndots")
    k.expect_eq(a.get("web_fqdn", "").rstrip("."), f"web.{k.ns}.svc.cluster.local", "web_fqdn")
    k.expect_eq(a.get("srv_port"), "80", "srv_port")
