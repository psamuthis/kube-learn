# Exercise 11.4 — Topology spread

Complete `deployment.yaml`: 6 replicas that the scheduler **must** spread across the nodes with a
maximum skew of 1 (`topologySpreadConstraints` on `kubernetes.io/hostname`, `DoNotSchedule`).
On 3 nodes that means exactly 2 per node.
