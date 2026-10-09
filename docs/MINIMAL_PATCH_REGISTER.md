# Minimal Patch Register

## Status definitions

- `NOT_IMPLEMENTED`: documented candidate only; no source or runtime behavior has changed.
- `UNDER_REVIEW`: evidence and exact patch are being reviewed.
- `IMPLEMENTED`: patch and validation evidence have been recorded.
- `REJECTED`: patch will not be applied, with rationale recorded.

Stage 1A created this register without source changes. Stage 1B updates each entry only after the corresponding focused patch and Local verification.

| Patch ID | Candidate | Classification | Stage 1A status | Intended evidence and validation gate |
|---|---|---|---|---|
| P01 | Pandas compatibility | `REQUIRED_RUNTIME_COMPATIBILITY` | `IMPLEMENTED_LOCAL_VERIFIED` | Released `highway_env/envs/common/observation.py:208` used `DataFrame._append`; changed only that call to `DataFrame.append` for the pinned `pandas==1.3.5` contract. Arguments, row selection, ordering, features, normalization, and shape logic are unchanged. Syntax and source-contract checks passed locally; actual pandas 1.3.5 execution remains an RDP gate. |
| P02 | Acceleration tool `env` argument | `REQUIRED_RUNTIME_COMPATIBILITY` | `IMPLEMENTED_LOCAL_VERIFIED` | Released `llm_agent_action.py:251` and `prompt_llm.py:568,594` omitted the already available `env` required by `isAccelerationConflictWithCar.inference(..., env)`. The same object is now threaded through both calls. No formula, threshold, safety text, or action-selection logic changed. Syntax and call-contract checks passed locally. |
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

## Stage 1B implementation records

### P01 - Pandas compatibility

- Original location: `highway_env/envs/common/observation.py`, `KinematicObservation.observe()`.
- Change: `df._append(...)` to `df.append(...)` only.
- Reason: align the inconsistent first append call with the repository-pinned `pandas==1.3.5` API already used by the same function for zero-row padding.
- Decision-semantic impact: none expected; observation contents and ordering are unchanged.
- Local result: syntax compilation and exact source-contract checks passed. Local pandas is not the target 1.3.5 environment, so target-version execution is deferred to RDP.

### P02 - Acceleration safety `env` argument

- Original locations: `llm_controller/llm_agent_action.py`, `LlmAgent_action_module.prompt_engineer()`; `llm_controller/prompt_llm.py`, `check_safety_in_current_lane()`.
- Change: pass the existing `env` object through to the existing `isAccelerationConflictWithCar.inference(..., env)` parameter.
- Reason: the released caller omitted a required positional argument and could fail before the first transition when the leading-vehicle acceleration branch was reached.
- Decision-semantic impact: no new safety rule; the released calculation is made callable with its declared input.
- Local result: syntax compilation and exact call-contract checks passed. Simulator execution was not performed locally.
