# Exercise 2.4 — Reconciliation in action

`deployment.yaml` runs 3 replicas of kubeapp. Once the checker has applied it:

1. In a second terminal, watch: `kubectl -n ex-2-4 get events -w` (or `get pods -w`).
2. **Delete one of the pods** (`kubectl -n ex-2-4 delete pod <name>`). What happens?
3. Follow the owner chain: `kubectl -n ex-2-4 get pod <name> -o jsonpath='{.metadata.ownerReferences}'`,
   then the same on the owner.
4. Try to "win" against the controller: `kubectl -n ex-2-4 scale deployment web --replicas=5`,
   then re-run the check (which re-applies the file). What happens to the replica count?

Fill in `answers.txt`. The checker also verifies (from the ReplicaSet's events) that you really
deleted at least one pod.
