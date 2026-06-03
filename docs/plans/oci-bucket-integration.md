# Plan: OCI bucket persistence backend

> A **plan-mode working doc**, not runnable config. Point Claude at this file and
> enter plan mode (Shift+Tab) when ready to implement.

## Goal
Add `OCIStore` implementing the `AmbienceStore` Protocol so ambiences can persist to
an OCI Object Storage bucket, selectable via `STORAGE=oci`. Local JSON files remain
the default (`STORAGE=local`). Zero changes to `AmbienceService` or controllers.

## Definition of done
- `OCIStore.save(ambience)` / `.get(id)` round-trip an ambience to/from a bucket.
- `STORAGE=local` (default) and `STORAGE=oci` both pass the same store conformance
  tests; switching is pure config.
- Credentials via env/OCI config only; never in code/logs; tests do not hit real OCI.

## Pre-work / open questions
- [ ] Auth method: OCI config file + key, or instance principals? Region, namespace, bucket name.
- [ ] Object key scheme: `ambiences/{user_id}/{id}.json` — confirm and guard traversal.
- [ ] SDK choice (`oci` Python SDK) and how to fake it in tests.
- [ ] Failure handling → surface as `502/503`, not stack traces (api/security rules).

## Steps (fill in during planning)
1. Add `STORAGE` + OCI settings to config (`app/core`); update `.env.example`.
2. Implement `persistence/oci_store.py` against the `AmbienceStore` Protocol.
3. Register in the composition root, selected by `STORAGE`.
4. Conformance tests shared with `LocalStore`; OCI SDK stubbed.
5. Document setup + the config switch in README.

## Risks
- Network/credential failures must degrade gracefully.
- Cost/latency vs local files; consider write-behind or local fallback later.
