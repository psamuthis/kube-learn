#!/usr/bin/env bash
# Issues a client certificate for alice through the Kubernetes CSR API and writes alice.kubeconfig.
set -euo pipefail
cd "$(dirname "$0")"
#>>
#| # TODO: key + CSR (openssl), CertificateSigningRequest alice-ex162, approve, fetch, kubeconfig
openssl genrsa -out alice.key 2048 2>/dev/null
openssl req -new -key alice.key -out alice.csr -subj "/CN=alice/O=developers"

kubectl delete csr alice-ex162 --ignore-not-found
cat <<YAML | kubectl apply -f -
apiVersion: certificates.k8s.io/v1
kind: CertificateSigningRequest
metadata:
  name: alice-ex162
spec:
  request: $(base64 -w0 alice.csr)
  signerName: kubernetes.io/kube-apiserver-client
  expirationSeconds: 86400
  usages: [client auth]
YAML
kubectl certificate approve alice-ex162
for _ in $(seq 20); do
  cert=$(kubectl get csr alice-ex162 -o jsonpath='{.status.certificate}')
  [ -n "$cert" ] && break
  sleep 1
done
echo "$cert" | base64 -d > alice.crt

server=$(kubectl config view --minify -o jsonpath='{.clusters[0].cluster.server}')
rm -f alice.kubeconfig
kubectl config set-cluster kube-learn --server="$server" --certificate-authority="$HOME/.minikube/ca.crt" \
  --embed-certs --kubeconfig=alice.kubeconfig
kubectl config set-credentials alice --client-certificate=alice.crt --client-key=alice.key \
  --embed-certs --kubeconfig=alice.kubeconfig
kubectl config set-context alice --cluster=kube-learn --user=alice --namespace=ex-16-2 --kubeconfig=alice.kubeconfig
kubectl config use-context alice --kubeconfig=alice.kubeconfig
rm -f alice.csr
#<<
echo "wrote alice.kubeconfig"
