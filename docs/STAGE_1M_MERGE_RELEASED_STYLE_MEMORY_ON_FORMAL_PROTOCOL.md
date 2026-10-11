# Stage 1M — Merge Released-Style Memory-ON Minimal Preparation

## 1. Scope and readiness

Stage 1M prepares, but does not execute, the formal Merge Memory-ON batch. It reuses the generic Stage 1H Released-style Memory path, Stage 1K Merge support, and Stage 1L orchestration/accounting. No simulator episode, Ollama request, embedding request, Chroma initialization, real database creation, or formal output was performed locally.

**Readiness verdict: `STAGE_1M_READY_FOR_RDP_MEMORY_ON_PREFLIGHT_REVIEW`.** This authorizes only human review and a nonexecuting RDP preflight. It does not authorize the formal batch.

## 2. Evidence classification and fidelity boundary

This is a **Released implementation pipeline reproduction with local LLM substitutions**.

- **PAPER:** Merge is evaluated, repeated random-seed experiments are reported, and success conceptually requires safe completion. Exact paper Merge seeds, Memory lifecycle across episodes, and failure-denominator treatment are unavailable.
- **RELEASED-CODE-DERIVED:** existing retrieval query, top-k behavior, prompt insertion, immediate pre-step `memory_update`, and possible same-cycle visibility are retained.
- **OUR EXPERIMENT DESIGN:** seeds 0–19 and ordering, cumulative cross-seed persistent DB, fresh-DB gate, guard 250, executable success rule, batch isolation/accounting, Qwen and nomic substitutions.

This stage does not correct known paper-versus-Released Memory gaps and must not be described as a strict isolated causal ON/OFF comparison.

## 3. Stage 1H reuse; zero core changes

The existing `scripts/minimal_ollama_full_episode.py` already accepts:

```text
--scenario merge-multi-agent-v0
--memory-mode on
--memory-db-path <Merge-specific path>
```

It lazily imports `DrivingMemory` only for ON execution and passes the existing chat and embedding configuration. The existing controller performs, for each CAV in controlled order, the unchanged query/retrieval/prompt/decision followed immediately by the unchanged Released-style update. After all CAVs, the runner performs exactly one joint `env.step(tuple(actions), env)`.

Therefore Stage 1M adds only a manifest and a thin batch orchestrator. It does not modify `Run_multi_CAV_LLM.py`, `llm_controller`, `highway_env`, prompts, parser, negotiation, safety, action mapping, Memory semantics, or requirements.

## 4. Frozen Merge environment and OFF/ON alignment

| Field | Formal value |
|---|---|
| Scenario | `merge-multi-agent-v0` |
| Simulation / policy frequency | 20 / 5 |
| Duration / Released boundary | 40 / 200 policy steps |
| Controlled CAVs / joint-action arity | 3 / 3 |
| Seeds | integers 0–19, ascending, exactly once |
| Classification | `OUR EXPERIMENT DESIGN`; `paper_seed_claim=false` |
| Chat | Ollama `qwen2.5:7b`, `http://127.0.0.1:11435`, timeout 120 s |
| Embedding | Ollama `nomic-embed-text:latest`, same endpoint, timeout 120 s |
| Guard | 250; protective only |
| Retry / replacement | none / none |

These conditions align with formal Stage 1L OFF except for the explicitly enabled Released-style Memory path and embedding substitution.

## 5. Cumulative Memory lifecycle

The formal batch uses exactly one fresh empty Merge-specific persistent DB. Seed 0 starts empty; its writes remain for seed 1, and accumulation continues through seed 19. The same absolute path is passed to every fresh seed subprocess. The DB is never cleared, replaced, rolled back, or automatically deleted.

Updates remain **pre-step**. Earlier CAV writes may be visible to later CAVs in the same policy cycle. If a trial fails after one or more pre-step writes, those partial writes remain in the cumulative DB; the orchestrator does not roll them back. This behavior is deliberate Released-code-derived behavior plus our cumulative lifecycle design, not a paper-explicit claim.

## 6. Fresh DB and namespace safety

The formal output root is:

```text
runs/stage1m_merge_memory_on_20seeds
```

The prepared batch ID is `released-style-merge-memory-on-formal-v1`, producing this conceptual layout:

```text
runs/stage1m_merge_memory_on_20seeds/
  released-style-merge-memory-on-formal-v1/
    memory-db/
      merge-multi-agent-v0/
```

The runner requires the output root's final component to be exactly `stage1m_merge_memory_on_20seeds`; requires a single safe batch-ID component; rejects names containing Intersection or `merge-preflight-memory-on`; and aborts before seed 0 if the planned batch directory or DB already exists. It never clears an existing path. Preflight validates the exact planned paths but creates neither the root, batch directory, nor DB.

## 7. Manifest

Path: `experiments/merge_memory_on_seeds.json`

ID: `merge-memory-on-released-style-cumulative-v1`

It freezes Merge, Memory ON, seeds 0–19, config 20/5/40, CAV/action arity 3, boundary 200, cumulative Memory, fresh-empty start, no between-seed clearing, no retry, no replacement, and the same success rule as OFF.

## 8. Batch orchestration and artifacts

`scripts/run_merge_memory_on_batch.py` delegates each seed once, in manifest order, to a fresh Python process running the existing full-episode module. Each invocation receives the same DB path and explicit chat/embedding identities. The orchestrator preserves stdout, stderr, result/error artifacts, traceback-bearing failed records, actual summaries, seed order, Git state, formal path, and lifecycle metadata. It fabricates no missing value and continues without retry or replacement.

The formal batch directory is explicitly named and must not exist. This makes preflight and execution refer to the same reviewed absolute path while retaining a hard no-overwrite gate.

## 9. Success rule

Success is independently derived using the frozen OFF rule:

```text
completion_status == "environment_terminated"
AND all(controlled_vehicle_arrival)
AND NOT any(controlled_vehicle_collision)
```

Duration termination alone is not success. All-arrived plus any controlled collision is not success. The Released independent success metric remains unavailable.

## 10. Storage/write-count invariant

For three controlled CAVs, a fully processed policy cycle is expected to produce three writes:

```text
expected completed-cycle writes = 3 × sum(completed Memory-ON policy cycles)
```

This is only a storage completeness check. It does not prove retrieval correctness, embedding correctness, semantic correctness, Memory usefulness, or paper fidelity. A failed/incomplete cycle may add one to three partial pre-step writes, so post-run auditing must account for such failures separately and must not roll them back.

## 11. Nonexecuting preflight behavior

Preflight validates the manifest, exact frozen config, guard, formal output/DB namespace, DB absence, model identities, lifecycle, seed order, and success rule, then prints metadata. It does not create any directory or artifact; import/instantiate `DrivingMemory`; initialize Chroma; contact chat/embedding endpoints; reset/step a simulator; or execute an episode.

## 12. Local fake validation

Focused tests cover manifest and lifecycle rejection, exact Merge-only ON commands, explicit embedding config, guard 250, safe formal namespaces, rejection of Intersection/smoke/existing paths, nonexecuting preflight, one shared DB across 20 ordered fresh subprocess commands, no clearing/rollback metadata, OFF-identical success classification, preservation of failures/stdout/stderr, and unique hard-gated output identity.

A fake three-CAV cycle demonstrates top-k=2 retrieval, immediate writes, same-cycle visibility counts 0→1→2, exactly three writes, and exactly one joint environment step with all writes preceding it. No real simulator, backend, embedding service, Chroma, or database is used.

## 13. Known limitations

- Memory update is pre-step and not outcome-grounded.
- Same-cycle visibility and cross-seed cumulative history introduce ordering dependence.
- A failed seed can influence later seeds through partial retained writes.
- Exact paper seeds, cross-episode lifecycle, and failure denominator are unresolved.
- Local Qwen/nomic models are declared substitutions, not GPT-4o-mini numerical reproduction.
- Passing tests establishes orchestration invariants, not Memory usefulness or paper equivalence.

## 14. Local validation result

- Stage 1M focused suite: **13 passed, 6 subtests passed**.
- Stage 1H Released-style Memory suite: **6 passed** in a fresh process with NumPy loaded normally.
- Stage 1K Merge preflight suite: **9 passed**.
- Stage 1L Merge Memory-OFF suite: **8 passed, 4 subtests passed**.
- Intersection regression selection: **27 passed, 3 subtests passed**.
- Full repository suite after all Stage 1M changes: **66 passed, 13 subtests passed**.

The real nonexecuting Local preflight reported the intended absolute DB path and left the formal root absent before and after execution. One isolated Stage 1H pytest invocation under the Local Windows Python 3.13 process encountered NumPy's `cannot load module more than once per process` import condition; rerunning that unchanged suite in a fresh process with a normal initial NumPy import passed 6/6, and the full suite also passed. No production source was changed to mask this host/test-process condition.

## 15. Exact future RDP preflight — review step only

From the RDP repository root, after updating to the Stage 1M commit and confirming tracked cleanliness:

```powershell
cd E:\YiZhen\Thesis\CoDrivingLLM-ReleasedReproduction
$env:PYTHONPATH = (Get-Location).Path
& E:\YiZhen\conda_envs\codriving_repro\python.exe -m scripts.run_merge_memory_on_batch --manifest experiments/merge_memory_on_seeds.json --backend ollama --model qwen2.5:7b --endpoint http://127.0.0.1:11435 --timeout 120 --embedding-backend ollama --embedding-model nomic-embed-text:latest --embedding-endpoint http://127.0.0.1:11435 --embedding-timeout 120 --max-steps 250 --output-dir runs/stage1m_merge_memory_on_20seeds --batch-id released-style-merge-memory-on-formal-v1 --ollama-version 0.32.9 --model-digest 845dbda0ea48 --embedding-model-digest unavailable --preflight
```

Review the printed absolute batch/DB paths, digests, Git metadata, seed order, and lifecycle. If either planned path already exists, stop. Update `--embedding-model-digest` to the verified RDP digest before any authorized formal execution.

## 16. Optional bounded temporary RDP validation

The earlier isolated Merge Memory-ON smoke already established the basic path, so another validation is not required by Stage 1M. If human review explicitly requests one, it must use a newly generated nonformal DB and must never use the formal root:

```powershell
$smokeId = "stage1m-bounded-" + [DateTime]::UtcNow.ToString("yyyyMMddTHHmmssfffZ")
$smokeRoot = Join-Path (Get-Location) ("runs\stage1m-merge-memory-on-bounded-validation\" + $smokeId)
$smokeDb = Join-Path $smokeRoot "memory-db\merge-multi-agent-v0"
if (Test-Path -LiteralPath $smokeDb) { throw "Temporary DB already exists: $smokeDb" }
& E:\YiZhen\conda_envs\codriving_repro\python.exe -m scripts.minimal_ollama_full_episode --scenario merge-multi-agent-v0 --backend ollama --model qwen2.5:7b --endpoint http://127.0.0.1:11435 --timeout 120 --seed 0 --max-steps 3 --memory-mode on --memory-db-path $smokeDb --embedding-backend ollama --embedding-model nomic-embed-text:latest --embedding-endpoint http://127.0.0.1:11435 --embedding-timeout 120 --output-dir $smokeRoot
```

This optional run is not formal evidence, must not be copied into the formal DB, and requires separate authorization.

## 17. Exact future formal command — DO NOT RUN YET

After a successful reviewed preflight, verified model digests, explicit authorization, and a final check that both batch and DB paths remain absent, the prepared command is:

```powershell
# DO NOT RUN YET
& E:\YiZhen\conda_envs\codriving_repro\python.exe -m scripts.run_merge_memory_on_batch --manifest experiments/merge_memory_on_seeds.json --backend ollama --model qwen2.5:7b --endpoint http://127.0.0.1:11435 --timeout 120 --embedding-backend ollama --embedding-model nomic-embed-text:latest --embedding-endpoint http://127.0.0.1:11435 --embedding-timeout 120 --max-steps 250 --output-dir runs/stage1m_merge_memory_on_20seeds --batch-id released-style-merge-memory-on-formal-v1 --ollama-version 0.32.9 --model-digest 845dbda0ea48 --embedding-model-digest <VERIFIED_NOMIC_DIGEST>
```

Do not run it during Stage 1M preparation. Do not create the formal DB in advance.
