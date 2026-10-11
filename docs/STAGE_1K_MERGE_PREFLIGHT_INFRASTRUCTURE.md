# Stage 1K — Merge Preflight Infrastructure and Local Fake Validation

## 1. Scope

Stage 1K prepares a bounded Merge preflight without running a simulator episode, Ollama, GPU, Chroma, or a formal experiment. It parameterizes the existing single-episode runner, adds fail-fast topology/namespace checks, supplies a reset-only RDP helper, and adds Local fake tests. It does not modify `Run_multi_CAV_LLM.py`, `highway_env`, Released prompts/parser/negotiation/safety/action mapping, Memory algorithms, formal artifacts, or existing runs.

Starting repository state: branch `codex/released-reproduction`, commit `c560ad7297a405f0ad2a541e63a8f22562c40e4b`.

## 2. Governing contract and classification

The governing evidence is `docs/STAGE_1J_MERGE_RELEASED_CODE_EXPERIMENT_CONTRACT_AUDIT.md`.

- `merge-multi-agent-v0` / `MergeEnvMARL`: **RELEASED-CODE**.
- simulation frequency 20, policy frequency 5, duration 40: **RELEASED-CODE intended-runner configuration**, taken from the author's commented Merge selection in `Run_multi_CAV_LLM.py:46-53`. The standalone environment default is 15 Hz; it is intentionally not used for this formal reproduction path.
- Local Ollama chat/embedding backends: **MODEL/BACKEND SUBSTITUTION**.
- allow-list, metadata, validation, guards, fake tests, output layout, DB lifecycle, and derived-success executable function: **OUR EXPERIMENT DESIGN / compatibility and orchestration**.
- Released-style Memory ON remains **not paper-faithful Memory**.

## 3. Exact code changes

### `scripts/minimal_ollama_full_episode.py`

The runner now accepts an allow-listed `--scenario` with only:

- `intersection-multi-agent-v0` (unchanged default), and
- `merge-multi-agent-v0`.

For Merge only, normal environment construction receives:

```text
simulation_frequency = 20
policy_frequency = 5
duration = 40
```

Intersection still calls `gym.make('intersection-multi-agent-v0')` without a new config and retains `runs/intersection-memory-off` as its effective default output directory. Merge defaults to `runs/merge-memory-off`; ON mode uses the corresponding scenario-correct `memory-on` name.

After reset, the runner records the actual class, environment ID, controlled/road vehicle counts, tuple arity, frequencies, duration, seed, and controlled list order/state. Merge fails before backend creation or any LLM policy cycle unless:

- environment ID is `merge-multi-agent-v0`;
- controlled count is 3;
- action tuple arity is 3; and
- config is exactly 20/5/40.

The policy-cycle body in `run_episode()` is unchanged: negotiation → action module over the controlled list → flatten → exactly one `env.step(tuple(action), env)`.

The Released independent `success` field remains unavailable. `classify_derived_success()` is a separate aggregation helper and does not change episode behavior or the summary's claim.

### `scripts/merge_preflight.py`

This helper imports no controller or Memory module, makes no backend call, and performs no `env.step()`. It creates Merge with the frozen config, repeats `reset(is_training=False, testing_seeds=...)`, applies the topology checks, prints state snapshots, and reports whether repeated same-seed controlled state is identical.

### `tests/test_merge_preflight.py`

Nine focused fake tests freeze scenario defaults/configuration, topology, termination, derived success, OFF/ON ordering, DB isolation/freshness, and reset-only behavior. Existing fake/static suites remain unchanged except that the full-episode fake environment now exposes the normal `spec`, road, and tuple-space metadata required by post-reset instrumentation.

## 4. Frozen topology and joint action

The reproduction freezes the observed Released behavior at `traffic_density=3`:

- 3 controlled CAVs;
- 3 initially requested HDVs, subject to Released early-collision/background cleanup;
- a three-element `MultiAgentAction` tuple;
- controlled order exactly as exposed by `env.controlled_vehicles`.

Road vehicle count is recorded after reset but is not asserted throughout an episode. The runner does not sort, replace, or mutate the controlled list.

## 5. Termination and derived success

The Merge duration boundary is exactly `40 × 5 = 200` policy steps. Tests freeze:

- collision precedence;
- step 199 without collision is non-terminal under the contract;
- step 200 is duration terminal;
- all-arrived alone is not Merge environment termination.

The future batch derived-success rule is frozen as:

```text
completion_status == "environment_terminated"
AND all controlled_vehicle_arrival values are true
AND all controlled_vehicle_collision values are false
```

This combines the **PAPER-SPECIFIED success concept** with an **OUR EXPERIMENT DESIGN executable derivation using Released fields**. Duration termination alone is not success; collision plus arrival is not success; reward is not used.

## 6. Memory OFF contract

The fake Merge policy cycle observes:

```text
negotiation
→ decision CAV 0
→ decision CAV 1
→ decision CAV 2
→ one joint env.step((a0, a1, a2), env)
```

`memory=None`, no `memory_factory`, and no `llm_controller.memory` import/DrivingMemory construction occur on the tested OFF path. No retry or fallback was added.

## 7. Released-style Memory ON contract

The three-CAV fake cycle confirms three repetitions of:

```text
retrieve(top_k=2) → decision → attempted write
```

before exactly one joint step. The later fake CAVs observe the records written earlier in the same cycle. Therefore expected attempted writes per completed Merge policy cycle are **3**. Retrieval location, pre-step update timing, same-cycle visibility, and existing write error behavior are not changed.

## 8. DB namespace and lifecycle

Merge uses the required namespace:

```text
memory-db/merge-multi-agent-v0
```

The runner resolves and records an absolute path, rejects an Intersection namespace in a Merge path, and requires the `merge-multi-agent-v0` component for Merge ON. `require_fresh_memory_database_path()` is provided for a future batch orchestrator: it rejects any existing path and never deletes/clears it. The single-episode runner permits reopening the same validated Merge path because persistence across policy cycles/ordered episode processes is part of the future design.

The future lifecycle is **OUR EXPERIMENT DESIGN / Released-code-derived design**:

fresh absent Merge DB → persistent across cycles → persistent across ordered seeds → never clear between seeds.

No Local test creates or opens a Chroma database.

## 9. Test results

Executed locally with fake/static paths only:

```powershell
python -m unittest discover -s tests -v
```

Result: **45/45 passed** (36 pre-existing tests plus 9 Merge-focused tests). The suite retained prompt/parser/action mapping AST checks, protected-source checks, Intersection batch behavior, OFF isolation, Released-style Memory ordering, artifact archival checks, and all previous reliability tests.

No simulator episode, Ollama, GPU, or Chroma was invoked.

## 10. Remaining RDP runtime gates

Before any formal seed manifest or batch:

1. confirm the actual RDP branch/commit, tracked cleanliness, Python 3.8.20, Gym 0.15.3, NumPy/Pandas, and repository-local import;
2. confirm actual class, 20/5/40 config, three controlled CAVs, initial road count, tuple arity, lane/order/state reporting;
3. repeat one nonformal temporary seed and verify identical initial controlled state;
4. compare a second nonformal temporary seed and verify intended position/speed variation while destination remains fixed `d`;
5. review any difference caused by RDP dependency behavior before an LLM call;
6. only after review, authorize a one-to-three-step Memory-OFF live smoke;
7. separately authorize a temporary fresh Merge DB Memory-ON smoke and verify three attempted writes per completed cycle with no Intersection path access.

No formal Merge seed manifest exists. Seeds `0..19` are not frozen or consumed here.

## 11. Exact proposed RDP preflight sequence

From the repository root in PowerShell:

```powershell
git branch --show-current
git rev-parse HEAD
git status --short
$env:PYTHONPATH = (Get-Location).Path
python --version
python -c "import gym,numpy,pandas; print('gym',gym.__version__); print('numpy',numpy.__version__); print('pandas',pandas.__version__)"
python -m scripts.merge_preflight --seed 987654 --repeat-resets 2
python -m scripts.merge_preflight --seed 987655 --repeat-resets 1
```

The two temporary seeds are preflight choices, not formal experiment seeds. Compare the printed controlled order/position/speed snapshots and confirm destinations remain fixed `d` from the Released construction.

Only after human review, the proposed bounded Memory-OFF live command is:

```powershell
python -m scripts.minimal_ollama_full_episode --scenario merge-multi-agent-v0 --backend ollama --model qwen2.5:7b --endpoint http://127.0.0.1:11435 --timeout 120 --seed 987654 --max-steps 3 --memory-mode off --output-dir runs/merge-preflight-memory-off
```

Do not run Memory ON or a formal batch automatically. A later approved ON smoke must use a fresh temporary path ending in `memory-db/merge-multi-agent-v0`, never the Intersection namespace.

## 12. Fidelity boundary and verdict

No CoDrivingLLM decision behavior was redesigned. Scenario selection, author-runner config injection, topology/namespace assertions, metadata, and fake tests are execution safeguards. Original prompts, parser, negotiation, safety, action mapping, simulator transitions, and Released-style Memory semantics remain untouched.

**STAGE_1K_READY_FOR_RDP_MERGE_PREFLIGHT**

This means ready only for the reset/topology commands above. It does not authorize the bounded live smoke, Memory ON smoke, seed-manifest creation, or a formal 20-seed Merge batch.
