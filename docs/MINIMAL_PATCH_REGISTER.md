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
| P03 | Ollama backend | `REQUIRED_OLLAMA_SUBSTITUTION` | `IMPLEMENTED_LOCAL_VERIFIED` | Added a native `/api/chat` transport with explicit backend, model, endpoint, and timeout. Action and negotiation pass their original single-system-message payload to it. Fake HTTP, prompt-AST equality, parser identity, and action-mapping identity tests passed. Real RDP Ollama remains untested. |
| P04 | Mandatory proxy removal | `REQUIRED_OLLAMA_SUBSTITUTION` | `IMPLEMENTED_LOCAL_VERIFIED` | Removed the per-call OpenAI/httpx proxy construction from both controller modules. The minimal backend contains no proxy or OpenAI branch. Static exclusion tests passed. |
| P05 | API credential handling | `REQUIRED_RUNTIME_COMPATIBILITY` | `IMPLEMENTED_LOCAL_VERIFIED` | Removed the unused source API-key placeholders and OpenAI imports from the two chat controller modules. Ollama requires no API credential. Static exclusion and secret-pattern checks passed. |
| P06 | Memory OFF import side effects | `REQUIRED_RUNTIME_COMPATIBILITY` | `IMPLEMENTED_LOCAL_VERIFIED` | Added a one-policy-step Memory-OFF runner that does not import or instantiate `DrivingMemory` and passes `memory=None` through the released disabled-memory decision path. A fake ordering test proved negotiation -> decisions -> one joint `env.step`, no `db/`, and no `llm_controller.memory` import. Real simulator validation remains an RDP gate. |

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

### P03 - Native Ollama chat backend

- New file: `llm_controller/llm_backend.py`, `ChatBackend`.
- Modified callers: `LlmAgent_action_module` and `LlmAgent_negotiation_module` accept either one shared backend object or the same explicit Ollama configuration.
- Transport contract: native `POST <endpoint>/api/chat` with `model`, the caller-supplied `messages`, and `stream=false`; returns `message.content` unchanged.
- Defaults: backend `ollama`, model `qwen2.5:7b`, endpoint `http://127.0.0.1:11435`, timeout `120` seconds. The endpoint is an RDP default and was not contacted locally.
- Decision-semantic impact: the base model/backend changes from OpenAI GPT-4o-mini to Ollama Qwen and therefore cannot be treated as numerical paper reproduction. Program-level prompt, parser, action mapping, negotiation format, and safety semantics remain released-code compatible.
- Local result: fake HTTP payload/response tests passed; action and negotiation prompt ASTs are identical to Released commit; parser and action-mapping function ASTs are identical.

### P04 - Remove mandatory OpenAI proxy

- Original locations: both controller `send_to_chatgpt()` methods constructed `httpx.Client` with `127.0.0.1:7890`.
- Change: transport moved to the Ollama-only backend; no proxy or system proxy mutation is present.
- Decision-semantic impact: none; request transport only.
- Local result: static exclusion test passed.

### P05 - Remove OpenAI API credential dependency

- Original locations: module-level `api_key = "your key here"` in both chat controller modules.
- Change: removed OpenAI imports, placeholders, and API-key parameters from the chat path.
- Decision-semantic impact: none; Ollama authentication is not introduced.
- Local result: static exclusion and committed-diff secret scans passed.

### P06 - Memory OFF infrastructure isolation

- New file: `scripts/minimal_ollama_single_step.py`.
- Change: the bounded runner performs exactly one policy cycle and never imports or instantiates `DrivingMemory`; it passes `memory=None` to the released decision method, whose retrieval and update calls remain disabled.
- Ordering: centralized negotiation, all per-CAV decisions, joint action flattening, exactly one `env.step(tuple(action), env)`.
- Decision-semantic impact: no Memory retrieval/update behavior was modified or enabled. The original `Run_multi_CAV_LLM.py` remains unchanged; the new runner removes unused embedding/Chroma side effects only for the explicit Memory-OFF smoke path.
- Local result: fake ordering and no-database test passed; `llm_controller.memory` was absent from `sys.modules`. No simulator or real LLM was executed.
- RDP gate: `docs/RDP_SMOKE_TEST.md` defines environment, Ollama inventory, and one-step commands. A full episode remains unauthorized.

### P07 - Smoke runner JSON serialization and module launch

- RDP evidence: Python 3.8.20, pandas 1.3.5, gym 0.15.3, numpy 1.24.4, and Ollama `qwen2.5:7b` completed reset, negotiation, four decisions, joint action `[4, 1, 1, 1]`, and one `env.step`; only the subsequent summary `json.dumps()` failed because the action values were NumPy `int32` objects.
- Reference evidence: Thesis `scripts/phase2c_integrated_single_step.py:20-31,140,167-168` uses a general NumPy-to-JSON conversion and converts action IDs with `int(...)`; Thesis `notes/reproduction_log.md:155-171` records that repository-root `python -m scripts.phase2b_llm_smoke` resolves local imports without a `sys.path` source modification. Antigravity contains joint-action printing/execution but no equivalent NumPy JSON or module-launch fix.
- Modified location: `scripts/minimal_ollama_single_step.py`, `build_summary()` and `main()`.
- Change: convert only the post-step reporting copy with `[int(a) for a in result["joint_action"]]`; the tuple supplied to `env.step()` is unchanged. RDP instructions now launch the runner as a module from repository root.
- Reason: Python's standard JSON encoder does not serialize `numpy.int32`; direct script-file launch places `scripts/` instead of the repository root first on the import path.
- Decision-semantic impact: none. Conversion occurs after `env.step`; action values and ordering are preserved. No prompt, parser, action mapping, negotiation, safety, memory, simulator, or backend code changed.
- Local result: regression tests cover NumPy `int32` serialization and exact `[4, 1, 1, 1]` ordering; the existing fake test continues to prove one `env.step`, `memory=None`, no database creation, and Released prompt/parser/action-mapping identity.

### P08 - Intersection Memory-OFF full-episode runner

- New file: `scripts/minimal_ollama_full_episode.py`.
- Released evidence: `Run_multi_CAV_LLM.py:58-102` defines the outer episode loop and policy-cycle order; `highway_env/envs/intersection_env.py:98-103,279-282` defines environment termination and arrival; `highway_env/envs/common/abstract.py:451-518` defines the single transition contract.
- Change: add a one-episode runner that repeats the existing Negotiation → per-CAV Action Decision → `env.step(tuple(action), env)` sequence, keeps Memory OFF with `memory=None`, writes each completed transition immediately, and separates environment termination, max-step guard, and runtime error outcomes.
- Recording: every invocation uses a new exclusive output directory containing run metadata, JSONL step records, summary, and an error traceback when applicable. NumPy values are converted only in reporting copies.
- Removed side effects relative to the Released runner: no `DrivingMemory`, render window, MP4 writer, or XLSX workbook. No additional simulator transition or warm-up is introduced.
- Decision-semantic impact: none intended. Existing controller modules, prompt, parser, negotiation, safety, action mapping, backend, memory algorithm, and simulator are unchanged. Invalid action ID is surfaced as an error rather than sent to the simulator; no fallback is supplied.
- Guard semantics: default `max_steps=100` is an execution protection limit, not a Released or paper setting. The Released Intersection default duration boundary is 249 policy steps.
- Metrics: collision and arrival use explicit simulator attributes/methods; independent success, LLM call count, and parser failure count are marked unavailable because the Released interfaces do not expose reliable definitions/counters.
- Validation: Local fake regression covers call ordering, one transition per cycle, action identity, Memory OFF, termination, max-step stop, error propagation, NumPy JSON, exclusive result directories, and protected-source identity. Real Ollama/simulator execution is deferred to RDP.

### P09 - Full-episode record and cleanup reliability

- Modified file: `scripts/minimal_ollama_full_episode.py`; no controller or simulator source changed.
- Initialization: Git commit/branch queries now occur inside the protected execution path. Each failed query is explicitly recorded as unavailable with its reason and traceback; successful metadata remains unchanged.
- Serialization: Python primitives and NumPy scalar/array values retain JSON-native representations. Unknown values now produce a typed `unsupported_type` diagnostic record instead of an unlabelled string conversion. Joint action conversion remains reporting-only after `env.step()`.
- Cleanup: `env.close()` exceptions are captured in `cleanup_error.json`. A pre-existing runtime exception remains primary and is re-raised; a cleanup-only failure is recorded as `runtime_error` and re-raised. No simulator transition is added.
- Decision-semantic impact: none. This patch changes metadata, serialization diagnostics, and cleanup failure precedence only. It adds no retry, fallback, action replacement, prompt rewrite, or LLM behavior.
- Validation: fake tests cover normal/unavailable Git metadata, NumPy and unknown-value serialization, cleanup-only failure, simultaneous primary/cleanup failure, traceback preservation, completed-step durability, action identity/order, one step per cycle, Memory OFF, and protected-source identity.
