# Exercise 14.2 — A LimitRange

Write `limitrange.yaml`: a LimitRange `defaults` for containers in this namespace, with

* default **requests**: 50m CPU, 64Mi memory;
* default **limits**: 200m CPU, 128Mi memory;
* a **maximum** memory limit of 256Mi.

The checker then creates a pod with no resources (it must get the defaults) and tries one
asking for a 512Mi limit (it must be rejected).
