# Exercise 4.2 — Two containers, one pod

Complete `pod.yaml`. The Pod `web` has two containers:

* `nginx` (`nginx:1.29-alpine`) serves files from `/usr/share/nginx/html`;
* `writer` (`busybox:1.37`) writes the current date into `index.html` every 2 seconds.

They must share an `emptyDir` volume named `html`, mounted at `/usr/share/nginx/html` in nginx
and at `/html` in the writer. The writer's command is already there.

The checker fetches the page through the pod IP, and also checks that the *writer* container
can reach nginx at `http://localhost/` (same network namespace!).
