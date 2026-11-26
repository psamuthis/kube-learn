# Exercise 7.7 — A Service with no selector

The setup started a pod `legacy-db` with **no labels**. Pretend it's a database on a VM outside
the cluster: you know its IP address, nothing else. Give it a proper in-cluster name, `legacy`:

1. `service.yaml`: a Service `legacy` with **no selector**, port 80 (name it `http`).
2. `endpointslice.yaml`: an `EndpointSlice` (`discovery.k8s.io/v1`) that the Service will use:
   * the label `kubernetes.io/service-name: legacy` is what links it to the Service;
   * `addressType: IPv4`;
   * one port named `http` with port **8080** (the name must match the Service's port name);
   * one endpoint whose `addresses` is the pod's IP:
     `kubectl -n ex-7-7 get pod legacy-db -o jsonpath='{.status.podIP}'`.

The checker fetches `http://legacy/`. (If you recreate the pod, its IP changes, and your
EndpointSlice is wrong. That's the price of managing endpoints by hand.)
