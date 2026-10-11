# Stage 1N-R1 — Highway Bounded Runtime Confirmation Protocol

## 1. Purpose

Stage 1N-R1 prepares the smallest diagnostic infrastructure needed to runtime-confirm the critical static findings from Stage 1N. It does not run Highway locally, define a success rate, reconstruct Highway, modify simulator/controller behavior, create a formal seed manifest, or prepare a formal batch.

The diagnostic script is `scripts/stage1n_r1_highway_runtime_probe.py`. Every mode produces one machine-readable `probe_result.json`; an exception produces `probe_error.json` with the original traceback and is re-raised.

## 2. Why the formal Highway experiment remains blocked

Stage 1N concluded:

`HIGHWAY_SUCCESS_METRIC_UNAVAILABLE_FROM_RELEASED_FIELDS`

The paper's success concept requires all CAVs to finish their tasks safely and reach their destinations. Released Highway assigns no routes/destinations, has no `has_arrived()` implementation, and does not terminate on arrival. Runtime confirmation cannot repair that evidence gap and must not reinterpret `destination == current position` as arrival.

The prepared probes can confirm the Released executable contract only. Even complete confirmation does not make Highway ready for a formal paper-success experiment.

## 3. Classification and fixed bounds

All generated evidence is classified **DIAGNOSTIC ONLY / NON-FORMAL**.

| Item | Fixed contract |
|---|---|
| Primary diagnostic seed | `987654` |
| One bounded alternative seed | `987655`, permitted only where documented |
| Formal seed exclusion | Seeds `0..19` are rejected |
| Action cases | One step per freshly recreated same-seed environment |
| Termination maximum | 45 policy steps |
| Negotiation | Pre-LLM only by default; optional one-cycle real path |
| Memory ON | Exactly two complete policy cycles |
| Retry/replacement | None |
| Success/PET/travel velocity | Not computed |

The CLI refuses to run without `--confirm-rdp`. This flag denotes deliberate execution on the Lab RDP; it does not certify results or convert them into formal evidence.

## 4. Reset/topology probe

Command mode: `--probe reset`

It creates `highway-v0`, performs one explicit diagnostic reset, and records:

- resolved environment ID and Python class;
- action-space class, representation, and `n`;
- controlled, background, and total road-vehicle counts;
- effective simulation frequency, policy frequency, duration, configured vehicle counts, and off-road option;
- controlled object list order;
- each controlled vehicle's class/display ID, lane index, position, speed, collision/on-road flags, route presence, route value, and safely read destination value/error.

It performs no step, LLM call, Memory import, embedding call, or DB creation.

Expected evidence, not a hard-coded result assertion: 4 controlled vehicles, 20 background vehicles, 24 total vehicles, and `Discrete(5)`.

## 5. Seed reproducibility probe

Command mode: `--probe seed`

It creates three separate environments and captures canonical states after resets with seeds `987654`, `987654`, and `987655`. Canonical state includes all controlled and background vehicle class/order, controlled membership, lane, position, speed, crash/on-road state, route, and destination behavior.

It reports:

- `same_seed_identical`;
- exact differing field paths between repeated same-seed states;
- `different_seed_state_differs`;
- exact differing field paths between seeds 987654 and 987655;
- all three raw canonical states.

It performs reset only—no `env.step`, LLM, Memory, or DB operation.

## 6. Action-consumption probe

Command mode: `--probe action`

Four fresh environments are recreated with seed `987654`:

| Case | Input |
|---|---|
| A, reference | `(3, 1, 1, 1)` |
| B, same first/different tail | `(3, 4, 4, 4)` |
| C, changed first | `(4, 1, 1, 1)` |
| List sub-probe | `[3, 1, 1, 1]` |

Each environment receives exactly one step. Before/after states for all four controlled vehicles, reward, terminated flag, environment step counter, observation shape, and info are preserved.

Evidence expectations:

- A and B have identical controlled transitions if tuple entries 1–3 are ignored.
- A and C differ if tuple entry 0 is effective.
- The list case records either its exact transition or its exact exception/traceback and stops that sub-probe; it is never fixed or retried.

The script does not infer consumption merely because a tuple did not raise.

## 7. Termination probe

Command mode: `--probe termination`

The probe resets once with seed `987654` and supplies Released-semantic joint tuple `(1, 1, 1, 1)` for at most 45 policy steps. For every step it records:

- requested policy step and environment step counter;
- terminated flag;
- all controlled collision flags;
- all controlled on-road flags, where available;
- reward and raw info.

`duration_40_confirmed` is true only if first termination is exactly policy step 40 and no earlier collision explains it.

If seed 987654 collides before step 40, one manual bounded alternative run with seed 987655 is permitted. No further seed search is allowed, and neither run is an experiment trial.

## 8. Arrival/destination probe

Command mode: `--probe arrival`

This reset-only mode records every controlled vehicle's route and destination behavior, whether `has_arrived` is callable, and the exact value/error if such a callable exists. It applies no success interpretation and explicitly reports success as unavailable.

If a route is absent and the destination property resolves to current position, that is recorded as implementation behavior—not arrival.

## 9. Negotiation probe

Command mode: `--probe negotiation`

The default mode is pre-LLM only. It invokes `detect_conflicts()` directly and records:

- road/candidate count;
- controlled count;
- per-road-vehicle conflict count and conflict partners;
- whether all conflict sets are empty;
- confirmation that no LLM call or environment step occurred.

Only if the actual prompt path is still needed may `--with-llm` be added. That bounded mode uses the existing `ChatBackend`, calls the existing negotiation agent once, supplies its unchanged result to the existing ActionAgent for all controlled vehicles, records the four returned decisions, and performs exactly one joint `env.step`. There is no retry, fallback, prompt rewrite, parser substitution, or replacement action.

## 10. Bounded Memory-ON probe

Command mode: `--probe memory-on`

This reuses the Stage 1H Released-style code without modifying `llm_agent_action.py`, `memory.py`, or embedding behavior. It is fixed at two cycles. Each cycle:

1. constructs the existing `DrivingMemory` against the same isolated diagnostic path;
2. executes one negotiation call;
3. executes the existing ActionAgent loop over four controlled vehicles;
4. wraps, but does not change, `retrieveMemory()` and `addMemory()` to record counts;
5. requires exactly four retrieval events and four write events before the step;
6. passes the four parsed actions unchanged as a tuple to exactly one `env.step`.

Each retrieval records `top_k` and DB count visible before query. Each write records DB count before/after. This is sufficient to observe whether later CAVs can see earlier same-cycle records without modifying retrieval or update semantics.

Expected fresh-DB progression:

```text
cycle 1: 0 → 1 → 2 → 3 → 4 → env.step
cycle 2: 4 → 5 → 6 → 7 → 8 → env.step
```

Expected total: 8 retrieval calls, 8 writes, and 2 joint steps. A backend/parser/write failure is preserved; it is not retried and partial pre-step DB effects are not rolled back.

## 11. Temporary DB lifecycle and guard

Required non-formal namespace:

```text
runs/highway-stage1n-r1-preflight-memory-on/memory-db/highway-v0
```

The guard requires all namespace components, rejects paths containing `intersection`, `merge`, or `formal`, and rejects an already existing target. It never clears or reuses a DB. The operator must choose a different explicitly diagnostic path for a later repeat rather than deleting evidence or pointing at another scenario/formal database.

The directory is intentionally under untracked `runs/` and must not be staged.

## 12. GPU/Ollama safety

RDP executable and services:

- Python: `E:\YiZhen\conda_envs\codriving_repro\python.exe`
- Ollama: `http://127.0.0.1:11435`
- Chat model: `qwen2.5:7b`
- Embedding model: `nomic-embed-text:latest`
- Intended workload GPU: GPU1

Before any optional real LLM/embedding mode, inspect existing Ollama and GPU state. Do not restart Ollama, kill processes, change device assignment, or touch GPU0. A snapshot cannot prove zero GPU0 impact; the probe must not make that claim.

The reset, seed, action, termination, arrival, and default negotiation probes do not need Ollama or embeddings.

## 13. Expected evidence

Runtime evidence should confirm or falsify, without repairing:

- 4 controlled + 20 background = 24 road vehicles;
- deterministic controlled order and initial state behavior;
- `Discrete(5)` and tuple/list runtime behavior;
- identical A/B and different A/C action transitions;
- actual duration termination at policy step 40 if collision does not intervene;
- missing route/arrival completion contract;
- candidate/conflict behavior before negotiation LLM;
- one negotiation → four decisions/writes → one step ordering;
- four `top_k=2` retrievals and four pre-step writes per complete Memory cycle;
- same-cycle Memory visibility.

## 14. Prohibited interpretations

Probe output must not be used to claim:

- Highway paper-success reproduction;
- success rate, PET, or travel-velocity result;
- a formal seed/trial;
- valid four-agent simulator control merely because four LLM actions exist;
- destination completion from current-position fallback;
- Memory quality or learning performance;
- equivalence to GPT-4o-mini;
- permission to alter simulator/controller semantics.

## 15. Local fake/static tests

`tests/test_stage1n_r1_highway_runtime_probe.py` imports the diagnostic module without runtime dependencies and verifies:

- formal seeds 0–19 are rejected;
- 45-step and two-cycle bounds;
- formal/batch output namespaces are rejected;
- DB namespace isolation and existing-DB rejection;
- same-seed environments are recreated for action comparison;
- seed comparison reports exact changed fields;
- four retrievals/writes precede exactly one step per cycle;
- expected cumulative visibility/count progression;
- no retry, replacement seed, or success-rate computation contract;
- no repository DB/artifact is created by module import.

Observed Local result on 2026-10-11 after final verification: **76 tests ran and all passed (`OK`)**. The argparse usage/error text emitted by an existing negative-path test is expected and did not fail the suite. No Local test imports or runs the real Highway simulator, contacts Ollama/embeddings, or initializes Chroma.

## 16. Protected files

Stage 1N-R1 must not modify:

- `Run_multi_CAV_LLM.py`;
- `highway_env/`;
- action/negotiation agent semantics;
- `memory.py` or `embedding_backend.py`;
- prompts, parser, safety, action mapping, requirements;
- Intersection/Merge formal artifacts or Stage 1M DB;
- PaperReconstruction.

Only the diagnostic script, fake/static tests, and this protocol document belong in the commit. `runs/` remains untracked.

## 17. Exact future RDP commands

Run from a PowerShell prompt on the Lab RDP:

```powershell
Set-Location C:\Thesis\CoDrivingLLM-ReleasedReproduction
$ReproPython = 'E:\YiZhen\conda_envs\codriving_repro\python.exe'
```

Reset/topology and seed checks:

```powershell
& $ReproPython -m scripts.stage1n_r1_highway_runtime_probe --probe reset --confirm-rdp --seed 987654
& $ReproPython -m scripts.stage1n_r1_highway_runtime_probe --probe seed --confirm-rdp
```

Action and arrival checks:

```powershell
& $ReproPython -m scripts.stage1n_r1_highway_runtime_probe --probe action --confirm-rdp --seed 987654
& $ReproPython -m scripts.stage1n_r1_highway_runtime_probe --probe arrival --confirm-rdp --seed 987654
```

Termination check:

```powershell
& $ReproPython -m scripts.stage1n_r1_highway_runtime_probe --probe termination --confirm-rdp --seed 987654 --max-steps 45
```

Only if the first result says collision prevented duration confirmation:

```powershell
& $ReproPython -m scripts.stage1n_r1_highway_runtime_probe --probe termination --confirm-rdp --seed 987655 --max-steps 45
```

Pre-LLM negotiation check:

```powershell
& $ReproPython -m scripts.stage1n_r1_highway_runtime_probe --probe negotiation --confirm-rdp --seed 987654
```

Before optional LLM/Memory calls, inspect state without restarting or killing anything:

```powershell
nvidia-smi
Invoke-RestMethod -Method Get -Uri 'http://127.0.0.1:11435/api/tags'
```

Optional one-cycle negotiation/action/step path:

```powershell
& $ReproPython -m scripts.stage1n_r1_highway_runtime_probe --probe negotiation --confirm-rdp --with-llm --seed 987654 --backend ollama --model 'qwen2.5:7b' --endpoint 'http://127.0.0.1:11435' --timeout 120
```

Before Memory ON, the diagnostic DB must not exist:

```powershell
$DiagnosticDb = 'C:\Thesis\CoDrivingLLM-ReleasedReproduction\runs\highway-stage1n-r1-preflight-memory-on\memory-db\highway-v0'
Test-Path -LiteralPath $DiagnosticDb
```

Proceed only if `Test-Path` returns `False`:

```powershell
& $ReproPython -m scripts.stage1n_r1_highway_runtime_probe --probe memory-on --confirm-rdp --seed 987654 --memory-cycles 2 --backend ollama --model 'qwen2.5:7b' --endpoint 'http://127.0.0.1:11435' --timeout 120 --embedding-backend ollama --embedding-model 'nomic-embed-text:latest' --embedding-endpoint 'http://127.0.0.1:11435' --embedding-timeout 120 --memory-db-path $DiagnosticDb
```

Do not rerun the Memory command against the same DB. Do not delete the DB as part of this protocol.

## 18. Decision gate after runtime confirmation

Preparation verdict:

`STAGE_1N_R1_READY_FOR_RDP_BOUNDED_RUNTIME_CONFIRMATION`

After RDP execution, archive and audit the raw diagnostic JSON before drawing conclusions. The next decision is limited to whether Stage 1N's static Released-contract statements are confirmed, falsified, or still unresolved.

Even if every expected runtime fact is confirmed, the formal gate remains:

`HIGHWAY_SUCCESS_METRIC_UNAVAILABLE_FROM_RELEASED_FIELDS`

No formal Highway manifest, batch, success rate, Memory comparison, or Stage 1O work is authorized by this protocol.
