# Stage 1L — Formal Merge Memory-OFF Protocol Preparation

## 1. Scope

Stage 1L freezes the formal Merge Memory-OFF manifest and prepares orchestration for later RDP execution. This stage does not run the batch, invoke Ollama/GPU/Chroma/simulator episodes, create a formal Memory-ON DB, or modify controller/simulator semantics.

Starting commit: `764f6aeb92926f76a06f9eeb11137009c5e4eb83`.

## 2. Formal contract

| Field | Frozen value | Classification |
|---|---|---|
| Scenario | `merge-multi-agent-v0` | RELEASED-CODE |
| Model | `qwen2.5:7b` | MODEL/BACKEND SUBSTITUTION |
| Backend/endpoint | native Ollama, `http://127.0.0.1:11435` | MODEL/BACKEND SUBSTITUTION |
| Timeout | 120 seconds | OUR EXPERIMENT DESIGN |
| Memory | OFF | Controlled experiment condition |
| Simulation frequency | 20 Hz | RELEASED-CODE intended-runner config |
| Policy frequency | 5 Hz | RELEASED-CODE intended-runner config |
| Duration | 40 s | RELEASED-CODE intended-runner config |
| Environment boundary | 200 policy steps | RELEASED-CODE consequence |
| Protective max-step guard | 250 | OUR EXPERIMENT DESIGN; not termination |
| Controlled topology | 3 CAVs, tuple arity 3 | RELEASED-CODE effective behavior |
| Repetitions | 20 | PAPER-SPECIFIED |
| Exact seeds/order | integers 0–19 ascending | OUR EXPERIMENT DESIGN; not paper seeds |
| Retry/replacement | none / none | OUR EXPERIMENT DESIGN |

## 3. Manifest

Path: `experiments/merge_memory_off_seeds.json`

Manifest ID: `merge-memory-off-controlled-v1`

The manifest uses the existing `codrivingllm.seed-manifest` version-1 schema and adds Merge-specific scenario, config, topology, action arity, duration boundary, success rule, and failure policy fields. It declares `paper_seed_claim=false`, exactly 20 unique seeds, and exact ascending order 0–19.

The paper supplies the repetition count and different-random-seed concept, not these seed values.

## 4. Frozen derived-success rule

Derived success is true iff:

```text
completion_status == "environment_terminated"
AND all controlled_vehicle_arrival values are true
AND all controlled_vehicle_collision values are false
```

The independent Released success field stays unavailable. Reward, max-step stop, absence of traceback, and mere duration termination are not success. This rule is the **PAPER-SPECIFIED success concept + OUR EXPERIMENT DESIGN executable derivation using Released fields**.

## 5. Batch orchestration

`scripts/run_merge_memory_off_batch.py` reuses the established generic utilities in `run_intersection_memory_off_batch.py` and delegates each seed to:

```text
python -m scripts.minimal_ollama_full_episode
  --scenario merge-multi-agent-v0
  --memory-mode off
  ...
```

Each seed is executed exactly once in a fresh subprocess and unique `trial-XX-seed-N` directory. The orchestration adds no controller decision logic and provides no retry/replacement path.

For every attempt it preserves runner stdout/stderr, the unique per-episode result directory, summary/error artifacts, a `trials.jsonl` record, and the original exception traceback when execution or artifact parsing fails. Malformed/missing artifacts become failed records with unavailable fields; values are not fabricated. Processing continues to later manifest seeds without replacing the failed seed.

The unique formal root defaults to:

`runs/stage1l_merge_memory_off_20seeds`

Every invocation creates a timestamp/UUID batch directory below it. `runs/` remains untracked and must not be committed.

## 6. Safety gates

Before execution the runner validates:

- schema/version/classification and `paper_seed_claim=false`;
- scenario is Merge and Memory is OFF;
- exact seeds 0–19, count 20, unique and ascending;
- config 20/5/40;
- expected controlled count/action arity 3;
- duration boundary 200;
- exact derived-success declaration;
- no retry/replacement;
- `max_steps >= 200`.

The single-episode runner independently fails before an LLM call if actual post-reset Merge ID, 3-CAV topology, tuple arity, or 20/5/40 config differs.

## 7. Local fake/static validation

Focused tests cover manifest validation and rejection, command construction, Memory-OFF/no-embedding command, 200-step guard, preflight nonexecution, Merge metadata/topology, exactly-once ordered attempts, arrival success, collision, duration without all arrival, failed process, malformed/missing artifacts, raw stdout/stderr preservation, and unique nonoverwriting directories.

The full regression suite must pass before handoff. No Local test invokes a simulator episode, Ollama, GPU, Chroma, or a formal result directory.

## 8. Exact RDP preflight and formal command

From the RDP repository root, first update to the Stage 1L commit and confirm tracked cleanliness. Then run the nonexecuting protocol preflight:

```powershell
cd E:\YiZhen\Thesis\CoDrivingLLM-ReleasedReproduction
$env:PYTHONPATH = (Get-Location).Path
& E:\YiZhen\conda_envs\codriving_repro\python.exe -m scripts.run_merge_memory_off_batch --manifest experiments/merge_memory_off_seeds.json --max-steps 250 --output-dir runs/stage1l_merge_memory_off_20seeds --ollama-version 0.32.9 --model-digest 845dbda0ea48 --preflight
```

After reviewing the printed metadata and reconfirming the Ollama version/model digest, the exact formal command prepared—but **not executed or authorized by Stage 1L**—is:

```powershell
& E:\YiZhen\conda_envs\codriving_repro\python.exe -m scripts.run_merge_memory_off_batch --manifest experiments/merge_memory_off_seeds.json --backend ollama --model qwen2.5:7b --endpoint http://127.0.0.1:11435 --timeout 120 --max-steps 250 --output-dir runs/stage1l_merge_memory_off_20seeds --ollama-version 0.32.9 --model-digest 845dbda0ea48
```

If the immediately observed version/digest differs, stop and update the recorded invocation deliberately; do not silently proceed. Do not run Memory ON and do not reuse the temporary preflight DB.

## 9. Result-integrity requirements after future execution

A separate audit must recompute trial count/order, per-trial artifacts, step continuity, reward sums, termination, collision/arrival arrays, derived success, failures, guard stops, stdout/stderr warnings, and aggregate denominators from the archived text artifacts. A completed batch attempt does not itself prove 20 successful executions or paper equivalence.

## 10. Fidelity boundary and readiness verdict

The new manifest and orchestrator are experiment infrastructure. They do not modify prompts, parser, negotiation, safety, action mapping, simulator dynamics, Memory behavior, or the policy-cycle order. Intersection infrastructure and sealed Stage 1F/1I results remain untouched.

**STAGE_1L_READY_FOR_RDP_FORMAL_MEMORY_OFF_EXECUTION_REVIEW**

This means the code is ready for human review and nonexecuting RDP preflight. It does not authorize the formal command, does not claim a formal result, and does not prepare a formal Memory-ON batch.
