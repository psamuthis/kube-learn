# Exercise 2.5 — A pod with no API call

Static pods are run by a kubelet straight from files on its node. The API server isn't involved,
except that the kubelet then *reports* a read-only "mirror pod" so you can see it.

1. Write `static-web.yaml`: a Pod named `static-web` **in namespace `ex-2-5`** (set
   `metadata.namespace`) running `nginx:1.29-alpine`.
2. Put it in the static pod directory of the node **kube-learn-m02** (you found the path in 2.1):

   ```console
   $ minikube -p kube-learn cp static-web.yaml kube-learn-m02:/tmp/static-web.yaml
   $ minikube -p kube-learn ssh -n kube-learn-m02 -- sudo cp /tmp/static-web.yaml <staticPodPath>/
   ```
3. `kubectl -n ex-2-5 get pods`. Note the name of the pod the API shows.
4. Try `kubectl -n ex-2-5 delete pod <it>`. What happens? Fill in `answers.txt`.

The checker doesn't apply anything; it looks for the mirror pod. `./course clean 2.5` removes the
file from the node again.
(On a single-node cluster, use the node `kube-learn` instead.)
