# Type-checking scope

The enforced type-check command is:

```bash
python -m mypy
```

It covers the repository-governance module and its public CLI adapters. New
governance modules must enter the `tool.mypy.files` list in the same change.
Imports from the legacy scientific runtime are followed as interfaces, not
recursively checked, so hygiene work cannot silently mutate physical-control
or algorithm code.

## Existing scientific-runtime exception

- **Owner:** research-programme maintainer
- **Rationale:** repository-wide mypy currently reports 72 pre-existing errors
  in 21 scientific-runtime files. Repairing them is outside the repository
  hygiene spec and would touch protected environment, evaluation, and agent
  implementations.
- **Tracking:** GitHub issue `#9`
- **Expiry:** 2026-09-30, or before any affected module is made part of an
  enforced type-check target, whichever comes first.

This exception does not permit new errors in the enforced governance scope.
