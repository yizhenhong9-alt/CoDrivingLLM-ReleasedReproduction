# Minimal Patch Register

## Status definitions

- `NOT_IMPLEMENTED`: documented candidate only; no source or runtime behavior has changed.
- `UNDER_REVIEW`: evidence and exact patch are being reviewed.
- `IMPLEMENTED`: patch and validation evidence have been recorded.
- `REJECTED`: patch will not be applied, with rationale recorded.

All Stage 1A entries are `NOT_IMPLEMENTED`.

| Patch ID | Candidate | Classification | Stage 1A status | Intended evidence and validation gate |
|---|---|---|---|---|
| P01 | Pandas compatibility | `REQUIRED_RUNTIME_COMPATIBILITY` candidate | `NOT_IMPLEMENTED` | Confirm the actual RDP pandas failure/version; prove observation row order, values, shape, and dtype remain equivalent. |
| P02 | Acceleration tool `env` argument | `REQUIRED_RUNTIME_COMPATIBILITY` candidate | `NOT_IMPLEMENTED` | Trace caller/callee signature and reproduce the affected leading-vehicle path with a bounded fixture. |
| P03 | Ollama backend | `REQUIRED_OLLAMA_SUBSTITUTION` candidate | `NOT_IMPLEMENTED` | Preserve exact prompt payload and downstream parser contract; validate transport first with a fake endpoint, then one authorized RDP call. |
| P04 | Mandatory proxy removal | `REQUIRED_OLLAMA_SUBSTITUTION` candidate | `NOT_IMPLEMENTED` | Make proxy use explicit/optional without changing prompt, model response handling, or system proxy settings. |
| P05 | API credential handling | `REQUIRED_RUNTIME_COMPATIBILITY` candidate | `NOT_IMPLEMENTED` | Remove source-secret assumptions, require safe runtime configuration, and pass repository secret scanning. |
| P06 | Memory OFF import side effects | `REQUIRED_RUNTIME_COMPATIBILITY` candidate | `NOT_IMPLEMENTED` | Ensure Memory OFF performs no embedding initialization, credential mutation, database creation, retrieval, or update. |

## Patch record requirements

Before any status becomes `IMPLEMENTED`, record:

- source file, function, and verified line location;
- original behavior and reproducible evidence;
- exact proposed change;
- necessity and classification;
- whether decision semantics can change;
- reference implementation, if any;
- validation command and artifact;
- reviewed diff and final commit.

No P01-P06 source changes were made during Stage 1A.
