# Exercise 3.3 — Label selectors

The setup created six pods, `a` to `f`, with these labels:

| pod | app | env | tier | release | team |
|---|---|---|---|---|---|
| a | shop | prod | web | stable | red |
| b | shop | prod | db | stable | |
| c | shop | staging | web | | blue |
| d | blog | prod | web | | red |
| e | blog | dev | db | canary | |
| f | shop | dev | web | | |

(See for yourself: `kubectl -n ex-3-3 get pods --show-labels`.)

In `selectors.txt`, write one **label selector** per question. The checker runs
`kubectl get pods -l '<your selector>'` and compares the pods it returns with the expected set.
Test as you go: `kubectl -n ex-3-3 get pods -l 'app=shop'`.
