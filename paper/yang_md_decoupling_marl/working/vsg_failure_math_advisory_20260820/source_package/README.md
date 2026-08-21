# Bundled frozen evidence package

`gpt_pro_math_pack_20260820.zip` is the exact user-supplied evidence package used by this advisory. Its SHA-256 digest is recorded in `SHA256.txt` and in `manifest/artifact_manifest.json`.

To reproduce the evidence checks without an external source directory, run:

```bash
./verification/run_with_bundled_source.sh
```

The helper extracts the nested source ZIP into a temporary directory, runs `verification/run_all_checks.sh`, and removes the temporary directory on exit.
