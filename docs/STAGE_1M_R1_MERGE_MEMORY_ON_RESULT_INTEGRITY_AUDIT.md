# Stage 1M-R1 — Merge Released-Style Memory-ON Formal Result Integrity Audit

## 1. Scope and verdict

This audit independently checks the copied formal Merge Memory-ON batch and its persistent Chroma database. It is read-only: no episode was rerun, no chat/embedding endpoint was contacted, no `DrivingMemory` or Chroma runtime was instantiated, and no raw artifact was modified.

**Verdict: `STAGE_1M_R1_PASS_WITH_NOTES`.** The batch is complete and internally consistent, and the write-count/storage completeness invariant is satisfied. Notes preserve the nonfatal initial top-k warning and known fidelity/evidence limits.

## 2. Provenance and exact batch

- Local evidence root: `runs/stage1m_merge_memory_on_20seeds/released-style-merge-memory-on-formal-v1`
- Stored RDP batch root: `E:\YiZhen\Thesis\CoDrivingLLM-ReleasedReproduction\runs\stage1m_merge_memory_on_20seeds\released-style-merge-memory-on-formal-v1`
- Execution commit: `e525998af4dc1ecd3af2f12d379d7884f387b471`
- Branch: `codex/released-reproduction`
- Stored `git_dirty`: `true`

The stored absolute RDP paths are retained as provenance and were not normalized or rewritten. `git_dirty=true` proves only that Git reported a dirty RDP worktree; it does not prove that tracked source changed. Untracked experiment outputs are a sufficient possible explanation, and the raw batch does not reconstruct the complete RDP Git diff.

## 3. Formal protocol identity

| Field | Raw value | Audit |
|---|---|---|
| Protocol / version | `released-style-merge-memory-on` / `1` | PASS |
| Classification | `OUR EXPERIMENT DESIGN` | PASS |
| Memory definition | `Released-code-derived Memory ON` | PASS |
| Scenario / mode | `merge-multi-agent-v0` / `on` | PASS |
| Cumulative / fresh / clear-between | `true` / `true` / `false` | PASS |
| Update / same-cycle visibility | pre-step / `true` | PASS |
| Seeds | integers 0–19 ascending | PASS |
| Chat model / digest | `qwen2.5:7b` / `845dbda0ea48` | PASS |
| Embedding model / digest | `nomic-embed-text:latest` / `0a109f422b47` | PASS |
| Chat / embedding endpoint | `http://127.0.0.1:11435` | PASS |
| Chat / embedding timeout | 120 / 120 seconds | PASS |
| Config | simulation 20, policy 5, duration 40 | PASS |
| Released boundary / guard | 200 / 250 | PASS |
| Controlled CAVs / action arity | 3 / 3 | PASS |
| Retry / replacement | none / none | PASS |
| Fresh process per seed | `true` | PASS |
| Manifest ID | `merge-memory-on-released-style-cumulative-v1` | PASS |
| Execution status | `complete_batch_attempt` | PASS |

## 4. Raw inventory identity

The deterministic inventory includes top-level metadata, every trial artifact, and the entire copied persistent database.

| Type | Files | Bytes |
|---|---:|---:|
| `.bin` | 4 | 12,897,984 |
| `.json` | 42 | 72,032 |
| `.jsonl` | 21 | 780,512 |
| `.pickle` | 1 | 230,019 |
| `.sqlite3` | 1 | 23,146,496 |
| `.txt` | 40 | 1,711,086 |
| **Total** | **109** | **38,838,129** |

Aggregate SHA-256 of the exact sorted LF-terminated inventory representation is **`3ffc68143a90a45e0e270e62256aab7c2c85eb7da77adf2d5d934cb6c9b0c850`**. The complete tracked text inventory is `experiments/archive/stage1m_merge_memory_on_raw_inventory.sha256`.

## 5. Batch accounting

Independent parsing found exactly 20 valid `trials.jsonl` records. Trial indices are exactly 0–19, seeds are exactly 0–19 in manifest order, and no duplicate, missing, unexpected, replacement, or retry seed exists. Exactly one `trial-XX-seed-N` directory exists for every record; every recorded result directory exists; no unexplained formal trial directory exists. Recomputed counts are 20 planned, 20 attempted, 20 completed, 20 environment-completed, and 0 failed.

## 6. Seed-by-seed ON results

Flags retain the stored controlled-vehicle order.

| Seed | Steps | Reward | Termination | Collision | Arrival | Success |
|---:|---:|---:|---|---|---|---|
| 0 | 22 | -11.046576097518589 | collision | F,T,F | F,F,F | no |
| 1 | 80 | 1.845048619012547 | collision | F,T,F | F,T,T | no |
| 2 | 200 | 80.65427805365731 | duration | F,F,F | F,T,T | no |
| 3 | 200 | 99.42698903770699 | duration | F,F,F | T,T,T | **yes** |
| 4 | 34 | 1.280736151542856 | collision | T,F,F | F,F,F | no |
| 5 | 110 | -37.4770140726175 | collision | F,F,T | T,T,T | no |
| 6 | 33 | 1.250842403247532 | collision | T,F,F | F,F,F | no |
| 7 | 200 | 98.9182472508739 | duration | F,F,F | T,T,T | **yes** |
| 8 | 66 | 15.712054538252193 | collision | F,F,T | F,T,F | no |
| 9 | 59 | -54.12544724551476 | collision | F,F,T | T,T,F | no |
| 10 | 46 | -2.910245166301233 | collision | F,T,F | F,F,F | no |
| 11 | 39 | -16.34389582605127 | collision | F,T,F | T,F,F | no |
| 12 | 80 | 7.390163561392149 | collision | F,T,F | T,T,T | no |
| 13 | 97 | 1.110612219606475 | collision | T,F,F | T,T,T | no |
| 14 | 40 | -18.034734649625392 | collision | F,F,T | T,T,F | no |
| 15 | 65 | -7.329046519573027 | collision | F,F,T | T,F,T | no |
| 16 | 64 | -4.785982383542363 | collision | F,T,F | F,T,T | no |
| 17 | 51 | -4.484063010319717 | collision | T,T,F | F,F,T | no |
| 18 | 20 | -10.479122912042996 | collision | T,T,F | F,F,F | no |
| 19 | 101 | -9.892828232806417 | collision | F,T,F | F,T,T | no |

## 7. Artifact completeness and metadata consistency

For every seed, `runner_stdout.txt`, `runner_stderr.txt`, nested `episode_summary.json`, `run_metadata.json`, and `steps.jsonl` exist and parse. Each trial has exactly one nested episode result directory. No `error.json`, `cleanup_error.json`, traceback file, or explicit failure artifact was found.

All 20 run metadata files agree on seed, scenario, Memory ON, chat backend/model/endpoint, embedding backend/model/endpoint, both timeouts, guard, Git commit, branch, Merge config, three-CAV topology, and action arity 3. All record the same exact RDP DB path. None references Intersection, the temporary `merge-preflight-memory-on` namespace, another batch, or a per-seed DB.

## 8. Step-log integrity

All 1,607 step lines parse as JSON. For each trial, line count equals both summary and trial-record total steps; `step_index` is continuous 0..N−1; `environment_steps` is continuous 1..N; independently summed reward agrees with both stored totals within `1e-9`; and the final `terminated=true` agrees with environment completion. Termination reason is derivable from step count plus stored collision flags and agrees with both records. No trial exceeds 200 policy steps or reaches guard 250.

The independently summed ON reward is `130.6800157193787`. It is retained only as an integrity quantity, not promoted to a paper metric.

## 9. Action and topology integrity

Every one of the 1,607 action-bearing step records contains exactly three joint-action entries. Continuous environment-step indices and one step record per cycle support one stored environment transition per completed policy cycle. Post-reset metadata records three controlled vehicles and their order.

**3-entry joint-action structural integrity is verified, but semantic vehicle identity stability cannot be independently proven from step logs alone.** Vehicle IDs are not stored alongside every action slot.

## 10. Merge termination audit

The Released contract is controlled collision or `duration × policy_frequency = 40 × 5 = 200`; arrival alone is not termination. Independent recomputation finds:

- Collision: 17 seeds — 0, 1, 4, 5, 6, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19.
- Released duration limit: 3 seeds — 2, 3, 7.

Every collision trial ends before 200 and has at least one controlled collision flag. Every duration trial ends exactly at 200 with all collision flags false.

## 11. Independently recomputed success

The frozen rule is `environment_terminated AND all(arrival) AND NOT any(collision)`. Recomputed successful seeds are **3 and 7**, matching per-trial stored values, standalone summary, and embedded summary. ON success is **2/20 = 0.10** using either planned or environment-completed denominator.

- Duration without all-arrived: seed **2**.
- All-arrived but collision, therefore unsuccessful: seeds **5, 12, 13**.

## 12. Warning and error audit

Seed 0 is the only non-empty stderr:

```text
Number of requested results 2 is greater than number of elements in index 1, updating n_results = 1
```

This is the expected nonfatal initial-store top-k limitation: the trial completed and subsequent accumulation continued. No traceback, timeout, Ollama/chat failure, embedding failure, parser failure, connection failure, retry, fallback, cleanup failure, max-step guard, divide-by-zero/TTC warning, unexpected DB path, or Memory-OFF evidence was found.

## 13. Cumulative DB integrity and write count

The copied DB exists at local evidence path `runs/stage1m_merge_memory_on_20seeds/released-style-merge-memory-on-formal-v1/memory-db/merge-multi-agent-v0`, corresponding exactly to the stored RDP path suffix. It is non-empty and Merge-specific.

The SQLite file was opened only through a `file:` URI with `mode=ro`; no Chroma API or `DrivingMemory` was instantiated. Read-only inspection found:

- one collection: `langchain`;
- embedding dimension: 768;
- two segments: persisted HNSW vector and SQLite metadata;
- final `embeddings` record count: **4,821**.

Independent ON steps are 1,607, so expected writes are `3 × 1,607 = 4,821`. Actual minus expected is **0**. Therefore: **write-count/storage completeness invariant satisfied.** This does not establish semantic, retrieval, embedding, effectiveness, or paper fidelity.

## 14. Cumulative-lifecycle evidence

Evidence levels are distinct:

1. **Metadata declaration:** cumulative true, fresh-empty start true, clear-between false, pre-step updates, same-cycle visibility, no rollback.
2. **Per-trial path:** all 20 trials record the identical absolute RDP Merge DB path.
3. **Runtime stdout:** seed 0 first reports 0 items; each trial begins at the prior trial's final post-write count. First loaded counts progress `0, 66, 306, 906, ... , 4518`; within each trial, loaded counts increase by three per completed cycle. Seed 19's final pre-cycle loaded count is 4,818.
4. **Final DB:** 4,821 records, exactly three per independently verified completed cycle.

Together these strongly support uninterrupted cumulative accumulation with no per-seed clear. Because no seed failed, raw evidence does not exercise partial-failure rollback behavior. Final count alone cannot prove exact historical retrieval behavior or which memories affected decisions.

## 15. Aggregate recomputation

| Quantity | Independent | Standalone | Embedded | Result |
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
| Total policy steps | 1,607 | unavailable | unavailable | independently recorded |
| Total reward | 130.6800157193787 | unavailable | unavailable | independently recorded |
| Expected / actual DB records | 4,821 / 4,821 | unavailable | unavailable | PASS |

Sum of per-trial wall times is `10128.6138084` s versus stored batch wall time `10128.6199403` s, a `0.0061319` s orchestration overhead difference.

## 16. OFF↔ON transitions and descriptive comparison

| Transition | Seeds | Count |
|---|---|---:|
| OFF success → ON success | 3, 7 | 2 |
| OFF success → ON unsuccessful | none | 0 |
| OFF unsuccessful → ON success | none | 0 |
| OFF unsuccessful → ON unsuccessful | 0,1,2,4,5,6,8,9,10,11,12,13,14,15,16,17,18,19 | 18 |

Under the frozen Released-code-derived cumulative Memory-ON protocol, the observed Merge success rate was **2/20**, compared with **2/20** under the controlled Memory-OFF protocol; both successful-seed sets are `{3,7}`. This is descriptive only, not causal evidence that Memory had no effect. ON uses ordered cumulative history, later seeds depend on earlier seeds, updates are pre-step and not outcome-grounded, same-cycle visibility exists, Qwen inference may be nondeterministic, and the paper does not specify this exact cross-episode lifecycle. Per-seed steps and several arrival/collision vectors differ even though the derived success classifications do not.

## 17. Paper / Released / our-design distinction

- **PAPER:** Merge is evaluated; repeated different-seed experiments and safe completion success are described. Exact seeds, cumulative cross-episode lifecycle, and failure denominator are unavailable.
- **RELEASED-CODE-DERIVED:** collision-or-duration termination, no independent success metric, pre-step Memory update, existing query/top-k/prompt insertion, and possible same-cycle visibility.
- **OUR EXPERIMENT DESIGN:** seeds/order, cumulative persistent DB across seeds, fresh-path gate, guard 250, derived-success executable rule, batch integrity protocol, and local Qwen/nomic substitutions.

The results are not a numerical reproduction of the paper and not a strict paired causal Memory test.

## 18. Metric limitations

Reliable PET and travel velocity are not directly recorded: **PET = unavailable; travel velocity = unavailable**. They were not reconstructed ad hoc. Paper failure-denominator equivalence remains unresolved. Total reward is used only for file/aggregate integrity.

## 19. Raw immutability verification

The complete 109-file, 38,838,129-byte inventory was computed before inspection and recomputed afterward. File paths, sizes, per-file hashes, and aggregate SHA-256 are identical. No raw ON or OFF artifact was changed. `runs/` remains untracked; the DB and raw logs are not staged or committed.

## 20. Regression tests and protected sources

Local tests were run without a real simulator episode, Ollama, embedding endpoint, `DrivingMemory`, Chroma runtime, or formal DB mutation:

- Full required `python -m unittest discover -s tests -p "test_*.py"`: **66 tests passed**.
- Stage 1H Memory regression: **6 passed** in a fresh process after a normal initial NumPy import.
- Stage 1K Merge regression: **9 passed**.
- Stage 1L Merge OFF regression: **8 passed**.
- Stage 1M batch regression: **13 passed**.
- Intersection regression selection: **27 passed**.

One direct isolated Stage 1H invocation under the Local Windows Python 3.13 host encountered NumPy's `ImportError: cannot load module more than once per process`; the unchanged suite passed 6/6 in a fresh process with NumPy imported normally, and it also passed within the required 66-test full discovery. No production or test source was changed to conceal this host/process loading condition.

Git inspection found no audit-created change to `Run_multi_CAV_LLM.py`, `highway_env/`, controller or Memory adapter semantics, embedding backend, prompts, parser, safety, negotiation, action mapping, requirements, Stage 1F/1I artifacts, Stage 1L OFF raw evidence, Stage 1M ON raw evidence, or PaperReconstruction.

## 21. Remaining limitations

- Step logs prove three-entry structure, not semantic vehicle identity per slot.
- Final counts and stdout strongly support accumulation but cannot reconstruct every historical retrieval result.
- The batch contains one nonfatal initial top-k warning.
- No failed seed exists to empirically test partial-write/no-rollback handling.
- ON is order-dependent and uses local model substitutions.
- Paper seeds, exact Memory lifecycle, PET, travel velocity, and failure denominator remain unresolved/unavailable.

## 22. Final verdict

`STAGE_1M_R1_PASS_WITH_NOTES`

The formal batch is complete, internally consistent, raw-immutable, and storage-count complete under the frozen Released-style cumulative Memory-ON protocol. The notes above must remain attached to any thesis interpretation.
