# Exercise 11.5 — Draining a node safely

`deployment.yaml` runs 3 `web` replicas.

1. Write `pdb.yaml`: a PodDisruptionBudget `web` that keeps **at least 2** `app=web` pods available.
2. Practise maintenance on the node running one of the pods:

   ```console
   $ kubectl -n ex-11-5 get pods -o wide
   $ kubectl cordon kube-learn-m02
   $ kubectl get node kube-learn-m02 -o jsonpath='{.spec.taints}'
   $ kubectl drain kube-learn-m02 --ignore-daemonsets --delete-emptydir-data
   $ kubectl -n ex-11-5 get pods -o wide        # where did they go?
   $ kubectl uncordon kube-learn-m02            # don't forget!
   ```

   Also try `kubectl drain` without `--ignore-daemonsets` first and read the error.
3. Fill in `answers.txt`.

The checker then evicts two pods back to back through the Eviction API (what `drain` does), and
expects the PDB to let the first through and refuse the second. It also checks that every node is
schedulable again.
