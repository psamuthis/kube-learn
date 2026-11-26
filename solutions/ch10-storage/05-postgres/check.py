# HINT: `envFrom: [{secretRef: {name: pg}}]` turns every key of the Secret into an env var.
# HINT: `readinessProbe: {exec: {command: ["pg_isready", "-U", "postgres"]}}`
# HINT: `volumeClaimTemplates` is a field of the StatefulSet spec (not of the pod template); its claims are named data-pg-0, …


def psql(k, sql):
    return k.exec("pg-0", "psql", "-U", "postgres", "-tAc", sql, timeout=30)


def check(k):
    sts = k.get("statefulset", "pg")
    k.require(sts is not None, "a StatefulSet `pg` exists")
    k.expect([t["metadata"]["name"] for t in sts["spec"].get("volumeClaimTemplates", [])] == ["data"],
             "it has a volumeClaimTemplate `data`")
    k.require(k.rollout("pg", kind="statefulset", timeout=240), "pg-0 becomes Ready (pulling postgres can take a minute)")
    k.expect_eq(k.jp("pvc", "data-pg-0", "{.status.phase}"), "Bound", "the claim data-pg-0")
    code, out = psql(k, "CREATE TABLE IF NOT EXISTS notes (txt text); TRUNCATE notes; INSERT INTO notes VALUES ('persisted!');")
    k.require(code == 0, "psql can write", out)
    uid = k.jp("pod", "pg-0", "{.metadata.uid}")
    k.kubectl("delete", "pod", "pg-0")
    k.require(k.wait_for(lambda: k.jp("pod", "pg-0", "{.metadata.uid}") not in ("", uid), timeout=60), "pg-0 is recreated")
    k.require(k.rollout("pg", kind="statefulset", timeout=180), "the new pg-0 is Ready")
    code, out = psql(k, "SELECT txt FROM notes;")
    k.expect(code == 0 and out.strip() == "persisted!", "the row survived the pod's deletion", out)
