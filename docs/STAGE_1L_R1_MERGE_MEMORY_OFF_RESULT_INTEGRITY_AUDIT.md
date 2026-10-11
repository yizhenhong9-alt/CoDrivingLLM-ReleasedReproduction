# Stage 1L-R1 — Merge Memory-OFF Formal Result Integrity Audit

## 1. Scope and verdict

This is a read-only integrity audit of the copied Stage 1L formal raw batch. No episode was rerun, no Ollama/Chroma/DrivingMemory service was contacted, and no file under `runs/` was changed. The result is a **Released implementation pipeline reproduction with local LLM substitution**, not a numerical reproduction of the paper.

**Verdict: `STAGE_1L_R1_PASS_WITH_NOTES`.** The batch is internally complete and consistent. The notes concern evidence limits: the raw logs cannot prove the absence of every hidden Memory side effect, cannot independently prove stable semantic vehicle identity from action arrays alone, and cannot resolve the paper's unpublished seed manifest or failure denominator.

## 2. Provenance and selected batch

- Repository commit recorded by the batch: `0dced03f3d2a9cbb7b2db79caa925a6257cdc629`
- Branch recorded by the batch: `codex/released-reproduction`
- Selected directory: `runs/stage1l_merge_memory_off_20seeds/controlled-merge-memory-off_20261011T020133286647Z_49485cbf`
- Selection method: unique directory whose `batch_metadata.json` identifies the frozen protocol below; the timestamp was not used as the selection criterion.
- Execution status: `complete_batch_attempt`
- The stored absolute RDP manifest path was inspected as evidence and was not rewritten or normalized.
- `git_dirty=true` proves only that Git reported a dirty worktree on the RDP. It does **not** prove that tracked source files were modified; untracked `runs/` is a sufficient possible cause. The copied artifacts do not contain enough evidence to reconstruct the complete RDP worktree diff.

## 3. Formal protocol identity

| Field | Raw value | Audit |
|---|---:|---|
| Protocol / version | `controlled-merge-memory-off` / `1` | PASS |
| Classification | `OUR EXPERIMENT DESIGN` | PASS |
| Scenario | `merge-multi-agent-v0` | PASS |
| Memory | `off` | PASS |
| Backend / model | `ollama` / `qwen2.5:7b` | PASS |
| Model substitution | `true` | PASS |
| Endpoint / timeout | `http://127.0.0.1:11435` / `120` s | PASS |
| Ollama / model digest | `0.32.9` / `845dbda0ea48` | PASS |
| Simulation / policy frequency | `20` / `5` | PASS |
| Duration / Released boundary | `40` / `200` policy steps | PASS |
| Protective guard | `250` | PASS |
| Expected CAVs / action arity | `3` / `3` | PASS |
| Manifest ID | `merge-memory-off-controlled-v1` | PASS |
| Manifest seeds | integers `0..19`, ascending, unique | PASS |
| Planned trials | `20` | PASS |
| Retry / replacement seeds | none / none | PASS |
| Fresh process per seed | `true` | PASS |

The environment and toolchain metadata also records Python 3.8.20, gym 0.15.3, NumPy 1.24.4, and pandas 1.3.5.

## 4. Batch accounting

Independent parsing found 20 valid `trials.jsonl` records. Trial indices are exactly `0..19`; seeds are exactly `0..19` in frozen manifest order, with no duplicate, missing, unexpected, or replacement seed. There are exactly 20 top-level trial directories, every recorded `trial_result_directory` exists, and no unexplained formal trial directory exists. Recomputed counts are 20 planned, 20 attempted, 20 completed, 20 environment-completed, and 0 failed.

## 5. Seed-by-seed results

`C` means collision and `A` means arrival; flags retain the stored controlled-vehicle order. Success was independently recomputed from the frozen rule and not trusted from stored `derived_success`.

| Seed | Steps | Total reward | Termination | Collision flags | Arrival flags | Success |
|---:|---:|---:|---|---|---|---|
| 0 | 25 | -9.959961438233844 | collision | F,T,F | F,F,F | no |
| 1 | 179 | -18.6340034568263 | collision | F,T,F | F,T,T | no |
| 2 | 200 | 78.80278790686175 | duration | F,F,F | F,T,T | no |
| 3 | 200 | 45.20112016504241 | duration | F,F,F | T,T,T | **yes** |
| 4 | 36 | 0.8366416347096823 | collision | T,F,F | F,F,F | no |
| 5 | 114 | -129.94322635830247 | collision | F,F,T | T,T,T | no |
| 6 | 35 | -1.673275827530757 | collision | T,F,F | F,F,F | no |
| 7 | 200 | 96.8342143244577 | duration | F,F,F | T,T,T | **yes** |
| 8 | 72 | 11.486057159328372 | collision | F,F,T | F,T,F | no |
| 9 | 20 | -12.083796796906135 | collision | T,T,F | F,F,F | no |
| 10 | 70 | 7.680046947351078 | collision | F,T,F | T,F,F | no |
| 11 | 88 | -9.648017070681167 | collision | T,F,F | T,F,F | no |
| 12 | 89 | -2.296416217240397 | collision | T,F,F | T,T,T | no |
| 13 | 165 | 32.326820938406144 | collision | T,F,F | T,T,T | no |
| 14 | 20 | -11.47702841900144 | collision | T,T,F | F,F,F | no |
| 15 | 38 | -6.308362880346417 | collision | T,F,T | F,F,F | no |
| 16 | 133 | 12.383882206797171 | collision | F,T,F | T,T,T | no |
| 17 | 51 | -2.7200320040779857 | collision | T,T,F | F,F,T | no |
| 18 | 21 | -11.22752475492775 | collision | T,T,F | F,F,F | no |
| 19 | 106 | -2.9801690817367064 | collision | F,T,F | F,T,T | no |

## 6. Artifact completeness and metadata consistency

For every seed, `runner_stdout.txt`, `runner_stderr.txt`, nested `run_metadata.json`, `episode_summary.json`, and `steps.jsonl` exist and parse where applicable. No `error.json`, `cleanup_error.json`, traceback artifact, or other explicit failure artifact was found. All 20 per-trial metadata files agree on seed, scenario, Memory OFF, backend, model, endpoint, timeout, guard, commit, branch, and recorded scenario configuration. Their post-reset topology records 3 controlled vehicles and action arity 3.

## 7. Step-log integrity

All 1,862 step rows parse as JSON. For every trial:

- row count equals both `episode_summary.total_steps` and `trials.jsonl.total_steps`;
- `step_index` is continuous `0..N-1` and `environment_steps` is continuous `1..N`;
- recomputed reward agrees with stored total reward within absolute tolerance `1e-9`;
- final termination state agrees with the episode summary;
- no trial exceeds the Released boundary of 200 policy steps and none reaches guard 250.

The step record does not carry a separate textual termination reason, so exact reason agreement is derived jointly from its final termination state, total step count, and stored controlled collision flags rather than from an independent reason field.

## 8. Merge termination and success audit

The Released Merge contract terminates on any controlled-vehicle collision or when steps reach `duration × policy_frequency = 40 × 5 = 200`; arrival alone is not a termination condition.

Independent results are 17 collision terminations and 3 duration-limit terminations. Every collision trial ends before 200 and has at least one controlled collision flag. Seeds 2, 3, and 7 end at exactly 200 with all collision flags false. Seed 2 lacks all-CAV arrival and is therefore unsuccessful. Seeds 3 and 7 satisfy the frozen derived-success rule and are the only successes.

Recomputed success is `2/20 = 0.10` per planned trial and `2/20 = 0.10` per environment-completed trial. Seeds 5, 12, 13, and 16 have all arrival flags true but also a collision flag; all are correctly excluded. Recomputed values match `trials.jsonl`, standalone `batch_summary.json`, and the summary embedded in `batch_metadata.json`.

## 9. Action and topology evidence

Every one of the 1,862 raw step records contains a joint action with exactly three entries, directly supporting action arity 3. Continuous environment-step numbering and one step record per completed policy cycle support one environment transition per recorded cycle. Per-trial post-reset metadata records the three-CAV topology and controlled-vehicle order. However, step rows store the action array rather than vehicle IDs, so stable semantic identity-to-position mapping across every cycle is **UNAVAILABLE** from step logs alone.

## 10. Memory-OFF evidence

Batch and all per-trial metadata explicitly record `memory_mode=off`; lifecycle metadata reports no DrivingMemory instantiation. Searches across all stdout/stderr found no DrivingMemory initialization, Chroma use/creation, embedding call, retrieval, or memory-write evidence. This is strong positive protocol evidence plus absence of unexpected log evidence, but raw logs cannot prove that an entirely silent hidden side effect was impossible. No Memory code was imported or database created during this audit.

## 11. Stdout, stderr, warnings, and failures

All 20 stderr files are empty. No stdout/stderr evidence of Python traceback, Ollama/backend error, timeout, connection failure, parser failure, max-step guard, cleanup failure, divide-by-zero/TTC warning, Chroma/embedding activity, retry, or fallback was found. Accordingly there is no seed-specific warning row to report. This classification concerns recorded output only and does not claim that unlogged events are impossible.

## 12. Aggregate recomputation

| Quantity | Independent | Standalone summary | Embedded summary | Result |
|---|---:|---:|---:|---|
| Planned | 20 | 20 | 20 | PASS |
| Attempted | 20 | 20 | 20 | PASS |
| Completed | 20 | 20 | 20 | PASS |
| Environment-completed | 20 | 20 | 20 | PASS |
| Failed | 0 | 0 | 0 | PASS |
| Successful | 2 | 2 | 2 | PASS |
| Unsuccessful completed | 18 | 18 | 18 | PASS |
| Success / planned | 0.10 | 0.10 | 0.10 | PASS |
| Success / environment-completed | 0.10 | 0.10 | 0.10 | PASS |
| Collision terminations | 17 | 17 | 17 | PASS |
| Duration terminations | 3 | 3 | 3 | PASS |
| Total policy steps | 1,862 | 1,862 | 1,862 | PASS |

Stored batch wall time is 8,101.9973453 s. Independently summing per-trial wall times gives 8,101.9911808 s; the 0.0061645 s difference is batch-level overhead and is internally reasonable. It is not used as an outcome metric.

## 13. Raw artifact immutability identity

The version-controlled inventory is `experiments/archive/stage1l_merge_memory_off_raw_inventory.sha256`. It contains one sorted line per raw file in the form `sha256␠␠byte_size␠␠relative_posix_path`.

- Files: **103**
- Total bytes: **2,328,575**
- SHA-256 of the exact LF-terminated sorted inventory representation: **`61426000148b11f097f77e901d2b19b511bc48cc64802a5f0b31f41ea5b6a0ae`**

The audit documentation and inventory itself are outside the raw batch and are not included in that identity. The raw `runs/` directory remains untracked and was not force-added.

## 14. Paper / Released / our-design distinction

**PAPER:** Merge is evaluated; repeated experiments use different random seeds; success conceptually requires safe completion/reaching destination. The exact published Merge seed manifest is unavailable, and `paper_failure_denominator_equivalence` remains unresolved.

**RELEASED:** Merge termination is controlled collision or duration boundary; the frozen configuration yields 200 policy steps. Arrival is not itself a termination condition, and the Released runner has no independent success metric.

**OUR EXPERIMENT DESIGN:** seeds 0..19 and their order, manifest identity, guard 250, the executable derived-success rule, Qwen2.5:7b substitution, and batch/artifact-integrity orchestration. The observed 10% must not be represented as the paper's numerical result.

## 15. Limitations

- Exact paper seeds and paper failure-denominator handling remain unresolved.
- Raw logs support, but cannot mathematically prove, the absence of silent hidden Memory behavior.
- Action arity and recorded order are supported; semantic identity-to-position stability is not independently encoded in each step.
- `git_dirty=true` cannot distinguish untracked outputs from tracked modifications without the original RDP Git status/diff.
- The local LLM is a declared model substitution.

## 16. Regression and protected-source status

Local fake/unit tests were run without Ollama or simulator episodes: **53 passed, 7 subtests passed**. Git diff/status inspection found no audit-created change to `Run_multi_CAV_LLM.py`, `highway_env/`, controller semantics, prompts, parser, safety, negotiation, requirements, Stage 1F artifacts, Stage 1I archive, existing raw runs, or PaperReconstruction.

## 17. Final verdict

`STAGE_1L_R1_PASS_WITH_NOTES`

The copied formal batch is complete, internally consistent, deterministically inventoried, and supports the reported 2/20 derived-success result under the frozen **our-design** rule. Evidence limitations above are nonfatal but must remain explicit.
