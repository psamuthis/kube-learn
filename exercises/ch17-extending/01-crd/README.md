# Exercise 17.1 — Your own resource type

Write `crd.yaml`: a CRD for a namespaced kind **`Note`** in the group **`kube-learn.dev`**
(plural `notes`, short name `nt`), version `v1` (served, storage), with this schema:

* `spec.text`: string, **required**, at most 280 characters;
* `spec.priority`: integer from 1 to 5, **default 3**;
* `spec.tags`: list of strings;
* a `status` subresource (with a free-form `status` object: `type: object` and
  `x-kubernetes-preserve-unknown-fields: true`);
* printer columns `Text` (`.spec.text`), `Priority` (`.spec.priority`) and `Age`.

And `note.yaml`: a `Note` named `first` with some text and no priority (the default should fill it in).

Since the CRD must exist before a Note can be created, the checker applies `crd.yaml`, waits for
it to be *Established*, then applies `note.yaml`. Then: `kubectl -n ex-17-1 get nt`,
`kubectl explain note.spec`. CRDs are cluster-scoped: `./course clean 17.1` deletes it.
