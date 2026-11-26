# Exercise 3.2 — Precise queries

The setup created a few pods in `ex-3-2` with various labels, images and nodes. Answer
`answers.txt` using `-o jsonpath`, `-o custom-columns`, `--sort-by`, `-l` and
`--field-selector`, not by eyeballing `-o yaml`.

You can answer with a command: a value like `$ kubectl -n $NS get …` is run by the checker
(`$NS` is the exercise namespace), so you can test your jsonpath directly.
