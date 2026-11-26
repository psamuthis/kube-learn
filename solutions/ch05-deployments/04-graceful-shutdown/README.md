# Exercise 5.4 — Graceful shutdown

During a rollout, a pod that's being deleted is removed from load balancing *at the same time*
as it gets SIGTERM, so for a moment it still receives new requests. Make `web` shut down
gracefully:

* a `preStop` hook that **sleeps 5 seconds** before SIGTERM is sent (use the built-in
  `sleep` action: `lifecycle: {preStop: {sleep: {seconds: 5}}}`);
* kubeapp itself keeps serving **3 more seconds** after SIGTERM: env `SHUTDOWN_DELAY` = `3`;
* a termination grace period of **20 seconds** (enough for both, with margin).

The checker deletes one pod and measures how long it takes to go away. It must take at least
8 seconds (5 + 3) and less than 20 (so the process really exits on its own and isn't SIGKILLed).
