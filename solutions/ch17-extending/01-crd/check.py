APPLY = ["crd.yaml"]

# HINT: The CRD's name must be `<plural>.<group>`: notes.kube-learn.dev.
# HINT: Defaults only work in a structural schema: every level needs a `type`.
# HINT: Printer columns: `additionalPrinterColumns: [{name: Text, type: string, jsonPath: .spec.text}, …]`.

BAD = {
    "priority 9": "apiVersion: kube-learn.dev/v1\nkind: Note\nmetadata: {name: bad1}\nspec: {text: hi, priority: 9}\n",
    "no text": "apiVersion: kube-learn.dev/v1\nkind: Note\nmetadata: {name: bad2}\nspec: {priority: 2}\n",
    "281 characters": "apiVersion: kube-learn.dev/v1\nkind: Note\nmetadata: {name: bad3}\nspec: {text: " + "x" * 281 + "}\n",
}


def cleanup(k):
    k.try_kubectl("delete", "crd", "notes.kube-learn.dev", "--ignore-not-found", ns=False)


def check(k):
    k.require(k.wait("crd/notes.kube-learn.dev", "condition=Established", timeout=30), "the CRD notes.kube-learn.dev is Established")
    code, _, err = k.try_kubectl("apply", "-f", str(k.dir / "note.yaml"))
    k.require(code == 0, "note.yaml applies", err)
    note = k.get("note", "first")
    k.require(note is not None, "the Note `first` exists")
    k.expect_eq(note["spec"].get("priority"), 3, "the defaulted priority")
    for what, doc in BAD.items():
        code, _, err = k.try_kubectl("apply", "--dry-run=server", "-f", "-", input=doc)
        k.expect(code != 0, f"a Note with {what} is rejected", "it was accepted")
    out = k.kubectl("get", "nt")
    header = out.splitlines()[0].split()
    k.expect(header[:4] == ["NAME", "TEXT", "PRIORITY", "AGE"], "`kubectl get nt` shows NAME TEXT PRIORITY AGE", out)
    crd = k.get("crd", "notes.kube-learn.dev", ns=False)
    k.expect("status" in crd["spec"]["versions"][0].get("subresources", {}), "the status subresource is enabled")
