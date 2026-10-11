# Stage 1N-R1 — Highway Non-LLM Runtime Result-Integrity Audit

## 1. Scope and evidence boundary

This is a narrow Local, documentation-only reconciliation of six bounded Highway probes previously executed manually on the Lab RDP. It does not rerun a probe, inspect an RDP machine, execute Highway locally, contact Ollama/embeddings, initialize Chroma, or define a formal Highway experiment.

> **OPERATOR-PROVIDED RDP EVIDENCE — RAW TERMINAL OUTPUT NOT ARCHIVED IN REPOSITORY**

The six observations in this document were supplied by the operator. No raw result JSON, terminal capture, hash, timestamp, or artifact path is available in the Local repository. Accordingly:

- **Repository-verifiable facts** are limited to source, documentation, tests, Git identity, and the behavior expressible by the checked-in probe.
- **Operator-provided runtime evidence** consists only of the values stated by the operator.
- **Audit inference** is the reconciliation of those statements with repository evidence; it is not independent verification of raw RDP output.

Absence of local raw artifacts is not evidence that the probes were not run, and no rerun is requested merely to create artifacts.

## 2. Local repository preflight

| Item | Observed Local state |
|---|---|
| Repository root | `C:/Thesis/CoDrivingLLM-ReleasedReproduction` |
| Branch | `codex/released-reproduction` |
| HEAD | `4eb48ccaf26497b6b3fc7ac175a841140d4b1ed1` |
| Remote tracking | Local branch aligned with `origin/codex/released-reproduction` before this documentation edit |
| Worktree | No tracked modification before this audit; pre-existing untracked historical docs and `runs/` remain present |
| Stage 1N audit | `docs/STAGE_1N_HIGHWAY_RELEASED_CODE_EXPERIMENT_CONTRACT_AUDIT.md` |
| Stage 1N-R1 protocol | `docs/STAGE_1N_R1_HIGHWAY_BOUNDED_RUNTIME_CONFIRMATION_PROTOCOL.md` |
| Probe/test preparation commit | `4eb48cc` contains only the protocol, probe, and fake/static tests |

Stage 1N-R1 does not stage or alter the unrelated untracked files or `runs/`.

## 3. Six-probe reconciliation matrix

All runtime observations in this table are **OPERATOR-PROVIDED RDP EVIDENCE — RAW TERMINAL OUTPUT NOT ARCHIVED IN REPOSITORY**.

| Probe | Static expectation | Operator-provided runtime observation | Verdict | Notes / limitation |
|---|---|---|---|---|
| Reset/topology | `highway-v0`; `HighwayEnv`; `Discrete(5)`; 4 controlled + 20 background = 24; 15/5 Hz; duration 40; controlled speed fixed 25; routes absent; destination falls back to current position. | All listed values observed; all controlled vehicles were `MDPVehicle`; all speeds 25; routes null; each destination equaled current position. | **CONFIRMED** | Confirms executable topology/configuration and unusable paper-style destination field. Raw output unavailable locally. |
| Seed | Same explicit seed should reproduce simulator-relevant creation; different seed should alter seeded positions/lanes/background speeds; controlled speed remains fixed. | Repeated 987654 physical/dynamic fields matched; only `display_id` differed. Seed 987655 changed controlled/background positions, lanes and background speeds; controlled speeds stayed 25. | **CONFIRMED WITH INSTRUMENTATION NOTE** | Raw aggregate `same_seed_identical=false` was polluted by non-semantic display IDs, not physical state. |
| Action | Tuple is accepted; `DiscreteMetaAction.act()` consumes `action[0]`; tail entries do not independently actuate vehicles; list is not a supported key. | A `(3,1,1,1)` and B `(3,4,4,4)` had equal reward and simulator-relevant controlled transitions. C `(4,1,1,1)` changed vehicle 0 outcome/reward. List raised `TypeError: unhashable type: 'list'` in the expected action lookup path. | **CONFIRMED WITH INSTRUMENTATION NOTE** | Raw `same_first_transition_identical=false` likewise resulted from recreated display IDs. No simulator “fix” is warranted. |
| Arrival/destination | No Highway `has_arrived`; routes absent; destination returns current position; no paper-compatible success field. | `has_arrived_present=false`, no calls, all routes null, all destinations equal current position, success unavailable. | **CONFIRMED** | Position-equals-destination is not arrival. |
| Termination | `HighwayEnv._is_terminal()` directly compares `steps >= duration`; expected actual boundary is 40 policy calls, not `40 × 5`. | With seed 987654 and IDLE tuple, no collision/off-road condition through step 40; false at 39 and true at 40. | **CONFIRMED** | Duration termination is not successful task completion. Alternative seed 987655 is unnecessary. |
| Negotiation pre-LLM | Non-intersection candidate list is all road vehicles; route-less default Highway is expected to yield no detected conflicts at reset. | 24 candidates, 4 controlled; controlled vehicles at road indices 0/6/12/18; every index 0–23 had zero conflicts; no LLM call and no step. | **CONFIRMED FOR THIS RESET STATE** | Does not prove that Highway can never detect a conflict. Evidence is limited to seed 987654 immediately after reset. |

## 4. Repository-source reconciliation

The operator observations are consistent with the checked-in implementation:

- `highway_env/envs/highway_env.py` registers/implements `HighwayEnv`, configures 4 controlled and 20 background vehicles, duration 40, and directly tests `self.steps >= self.config["duration"]`.
- `highway_env/envs/common/action.py` declares `DiscreteMetaAction`; tuple handling indexes `action[0]`, while a list reaches an unhashable action lookup.
- `highway_env/vehicle/kinematics.py` returns the current position as `destination` when no route exists.
- `llm_controller/llm_agent_negotiation_system.py` uses `env.road.vehicles` for Highway and returns no sampled route points when a route is absent.
- `scripts/stage1n_r1_highway_runtime_probe.py` intentionally includes `display_id` in canonical vehicle records. Its whole-record equality therefore explains both non-semantic false booleans without contradicting physical-state equality.

No supplied observation contradicts the Stage 1N static contract.

## 5. Instrumentation notes

### 5.1 Seed equality flag

`same_seed_identical=false` compares the entire canonical record, including `display_id` derived from object string representation. The operator states that only those IDs differed, while positions, lanes, speeds, crash/on-road state, routes, and destinations matched. Classification: **instrumentation-only false negative**.

### 5.2 Action-transition equality flag

`same_first_transition_identical=false` compares the full after-state records from recreated environments, again including display IDs. The stated physical values and reward for cases A/B matched. Classification: **instrumentation-only false negative**.

The comparator remains unchanged. Changing it would improve presentation but would not answer an unresolved simulator question, and rerunning completed probes solely to turn these booleans true is unwarranted.

## 6. Result-integrity verdict

**STAGE_1N_R1_NON_LLM_RUNTIME_CONTRACT_CONFIRMED_WITH_NOTES**

The operator-provided observations consistently confirm the six bounded non-LLM expectations. Notes are limited to lack of archived raw terminal output, two display-ID equality false negatives, and the state-specific scope of the empty negotiation conflict set.

This verdict is not a numerical paper reproduction and is not an independent raw-artifact audit.

## 7. Formal Highway decision gate

The formal 20-seed Highway experiment remains blocked:

**HIGHWAY_SUCCESS_METRIC_UNAVAILABLE_FROM_RELEASED_FIELDS**

Released episode termination and paper-style successful task completion remain distinct:

```text
Released duration/collision/off-road termination
!=
all CAVs safely completing tasks and reaching assigned destinations
```

No route, destination-completion, or arrival contract was revealed at runtime. Duration termination, no collision, and `destination == position` must not be promoted to success criteria. No Highway formal manifest, 20-seed batch, PET, travel-velocity result, or success rate is authorized.

## 8. Remaining bounded negotiation question

### Separate negotiation-with-LLM probe

- **Necessary?** No, not as a separate probe.
- **Question it would answer:** Whether the existing backend is actually invoked with an empty-conflict prompt, produces parser-compatible negotiation text, supplies that text to the four ActionAgent decisions, and completes one step.
- **Can static evidence answer it?** Source establishes the call chain and unchanged prompt/backend wiring, but not a successful live Ollama response.
- **Material evidence improvement?** Limited. The non-LLM conflict/candidate contract is already confirmed, and the proposed Memory-ON probe exercises the same live negotiation/action path twice.
- **Safe and bounded?** Yes: the current CLI's `negotiation --with-llm` mode is one negotiation, four action decisions, and one step, without retry/fallback.
- **Worth doing separately?** No. It would be redundant if the Memory-ON probe is run and would not affect the success-metric blocker.

Therefore no separate negotiation-with-LLM command is recommended.

## 9. Remaining bounded Memory-ON question

### Two-policy-cycle Memory-ON probe

- **Necessary?** Not necessary to confirm the six non-LLM facts or unblock a formal experiment; recommended once to close the Released executable Memory evidence chain.
- **Question it would answer:** Whether real Highway + Ollama + embeddings + Chroma produce exactly four `top_k=2` retrievals and four pre-step writes per completed cycle, cumulative counts `0→4→8`, later-CAV same-cycle visibility, and one joint step only after four decisions/writes.
- **Can static evidence answer it?** Static code establishes the intended call locations/order, but cannot independently establish live Chroma persistence/count progression or endpoint integration.
- **Material evidence improvement?** Yes, narrowly: it validates the Stage 1H Memory path in Highway and simultaneously exercises real negotiation/action wiring. It does not validate Memory quality or paper success.
- **Safe and bounded?** Yes. The actual CLI fixes `--memory-cycles` at 2, rejects formal seeds, requires `--confirm-rdp`, rejects existing/cross-scenario/formal DB paths, and performs no retry/replacement.
- **Worth doing before Stage 1N closure?** Yes, as the final optional bounded runtime confirmation. Archive its generated JSON/DB identity afterward; do not treat it as a formal trial.

## 10. Exact future RDP command

The following command is justified only for the two-cycle Memory-ON confirmation. It explicitly targets the RDP repository and Python—not the Local path.

### Read-only preflight

```powershell
$RdpRepo = 'E:\YiZhen\Thesis\CoDrivingLLM-ReleasedReproduction'
$RdpPython = 'E:\YiZhen\conda_envs\codriving_repro\python.exe'
Set-Location -LiteralPath $RdpRepo

git rev-parse --show-toplevel
git branch --show-current
git rev-parse HEAD
git status --short --branch

nvidia-smi
Invoke-RestMethod -Method Get -Uri 'http://127.0.0.1:11435/api/tags'
```

Expected code identity before execution: branch `codex/released-reproduction`, HEAD `4eb48ccaf26497b6b3fc7ac175a841140d4b1ed1`. Review any status difference before proceeding. Do not restart Ollama, kill a process, change GPU assignment, or touch GPU0.

### Fresh-path guard

```powershell
$DiagnosticDb = Join-Path $RdpRepo 'runs\highway-stage1n-r1-preflight-memory-on\memory-db\highway-v0'
$OutputRoot = Join-Path $RdpRepo 'runs\highway-stage1n-r1-memory-on-results'

Test-Path -LiteralPath $DiagnosticDb
```

Proceed only if the DB result is `False`. The probe itself also rejects an existing DB and does not clear/reuse it.

### Two-cycle probe

```powershell
& $RdpPython -m scripts.stage1n_r1_highway_runtime_probe `
  --probe memory-on `
  --confirm-rdp `
  --seed 987654 `
  --memory-cycles 2 `
  --backend ollama `
  --model 'qwen2.5:7b' `
  --endpoint 'http://127.0.0.1:11435' `
  --timeout 120 `
  --embedding-backend ollama `
  --embedding-model 'nomic-embed-text:latest' `
  --embedding-endpoint 'http://127.0.0.1:11435' `
  --embedding-timeout 120 `
  --memory-db-path $DiagnosticDb `
  --output-root $OutputRoot
```

Do not rerun against the same DB, do not delete the DB as part of this protocol, and do not convert the result into a success rate.

## 11. Tests and protected state

No code/test modification is required. Observed Local results on 2026-10-11:

- relevant Stage 1N-R1 fake/static tests: **10 tests, all passed (`OK`)**;
- full Local suite: **76 tests, all passed (`OK`)**.

The argparse usage/error text emitted during the full suite is an expected existing negative-path assertion and did not fail the suite. No test ran the real Highway simulator, contacted Ollama/embeddings, or initialized Chroma. Stage 1N-R1 remains documentation-only in this audit; all Released core files, diagnostic implementation, prior formal artifacts, PaperReconstruction, and untracked `runs/` remain untouched.

## 12. STOP point

Stop after this audit and, if the operator chooses, the single bounded two-cycle Memory-ON confirmation. Do not proceed to Stage 1O, formal Highway experimentation, MultiAgentAction conversion, route/destination invention, Roundabout implementation, or reconstruction/extension work.
