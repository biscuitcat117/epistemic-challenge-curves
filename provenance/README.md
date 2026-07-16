# Research provenance

The main repository presents a clean reproduction workflow. This folder keeps
the records needed to understand how the original experiment was designed and
run.

`original-v0.1/` preserves the original plans, freeze manifests, amendments,
Python scripts, tests, frozen prompt inventories, and accepted pilot logs. For
privacy, the public copies of the two pilot `.eval` archives replace one
absolute local filesystem path with the equivalent repository-relative path;
their model outputs and other run records are unchanged. `REPLICATION_FREEZE.json`
records the hashes of these sanitized public archives. The snapshot is not the
recommended code path for new readers.

The freeze manifests inside the snapshot can be checked with:

```bash
python provenance/verify_snapshot.py
```

This preservation has a narrow purpose: the clean code can change without
creating the false impression that it was the exact code used during the
original experiment.
