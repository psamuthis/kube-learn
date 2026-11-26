# Chapter 18 — Capstone: a production-grade guestbook

> **Time:** a weekend · **Exercise:** `exercises/ch18-capstone/` (1, graded in sections)

Time to put everything together. You'll deploy a small but **complete** platform: a web tier,
a stateful backend, configuration and secrets, HTTPS ingress, autoscaling, disruption budgets,
pod security and network isolation, packaged with Kustomize. There's almost no starter code:
the README is a specification, the same way a ticket at work would be.

## 18.1 The system

```text
           https://guestbook.ex18.kube-learn.test
                         │  (ingress-nginx, TLS)
                         ▼
               Service web ─────▶ Deployment web (kubeapp:2.0, 2–5 replicas, HPA)
                                        │  REDIS_HOST=redis, REDIS_PASSWORD from a Secret
                                        ▼
               Service redis ───▶ StatefulSet redis (redis:7.4-alpine, AOF persistence,
                                        PVC on local-path)
```

kubeapp's `/guestbook` endpoint stores entries in Redis (`POST` adds one, `GET` lists them),
and `/hits` counts visits.

## 18.2 The specification

**Packaging**

* `base/`: everything environment-neutral; `overlays/prod/`: what's specific to production (the
  Ingress, the TLS host, prod sizing). The checker runs `kubectl apply -k overlays/prod`.
* Generated config: the Redis password comes from a `secretGenerator` (hash suffix, so a password
  change rolls the pods).

**Redis**

* StatefulSet `redis`, 1 replica, `redis:7.4-alpine`, started with `--requirepass` (from the
  Secret, never written in plain text in a manifest other than the generator) and
  `--appendonly yes`;
* a volumeClaimTemplate `data` (200Mi, `local-path`) mounted at `/data`;
* a readiness probe that actually authenticates (`redis-cli -a "$REDIS_PASSWORD" ping`);
* a Service `redis` on 6379.

**Web**

* Deployment `web`, `kubeapp:2.0`, **without** a `replicas` field (an HPA owns it);
* env `REDIS_HOST=redis`, and `REDIS_PASSWORD` from the Secret (`secretKeyRef`). Watch out for the
  `REDIS_PORT=tcp://…` service-link variable (chapter 7.5): kubeapp copes with it, many apps don't,
  and `enableServiceLinks: false` turns those variables off;
* readiness and liveness probes, CPU/memory requests, a memory limit;
* graceful shutdown (preStop + grace period);
* replicas spread across nodes (topology spread, `ScheduleAnyway` is fine);
* Service `web` (80 → http);
* HPA `web`: 2–5 replicas at 70% CPU;
* PodDisruptionBudget `web`: at least 1 available.

**Security**

* The namespace enforces the **restricted** Pod Security level (the setup sets the label), so
  every pod needs a compliant securityContext. For Redis, run as UID/GID 999 (the image's `redis`
  user) with `fsGroup: 999`.
* `readOnlyRootFilesystem` for `web` (with an `emptyDir` on `/tmp`).
* NetworkPolicies: **default-deny ingress** for the namespace; Redis accepts only `web` pods on
  6379; `web` accepts only the ingress controller (namespace `ingress-nginx`) on 8080.
* No ServiceAccount token mounted in either workload.

**Ingress**

* host `guestbook.ex18.kube-learn.test`, TLS with a Secret `guestbook-tls` that you create
  yourself (self-signed, chapter 8.3). Not in git!

## 18.3 How it's graded

`./course check 18.1` grades in sections, so you can build incrementally:

1. **objects**: everything exists and rolls out;
2. **app**: through HTTPS, a guestbook entry can be posted and read back;
3. **persistence**: the entry survives deleting `redis-0`;
4. **security**: pods admitted under `restricted`, non-root, no tokens; a pod that isn't `web`
   can't reach Redis, nor can anything reach `web` except the ingress controller;
5. **resilience**: HPA, PDB, spread, graceful shutdown;
6. **config**: the password only lives in the Secret.

## 18.4 Where to go from here

* **Real clusters**: create a managed cluster (GKE Autopilot, EKS with Karpenter, AKS) and redeploy
  the capstone there. Swap `local-path` for the cloud's storage class, ingress-nginx for the
  cloud's load balancer or a Gateway API implementation, and self-signed TLS for cert-manager.
* **GitOps**: put the capstone in a git repo and let Argo CD or Flux sync it.
* **Observability**: install kube-prometheus-stack, add a ServiceMonitor, build a dashboard for
  the guestbook.
* **The operator**: extend kv-operator from chapter 17 into a real Redis operator (a replica set
  with failover via Sentinel), rewrite it with kube-rs, add leader election and conditions.
* **Certifications**: CKAD (developer), CKA (administrator), CKS (security). This course covers
  the first two curricula; chapter 12 is a start on the third.
* **Read the source**: `pkg/controller/deployment/` in kubernetes/kubernetes is the Deployment
  controller you've been using all along. It's a few thousand lines of very readable Go.
