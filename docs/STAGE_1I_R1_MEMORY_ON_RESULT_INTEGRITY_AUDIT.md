# Stage 1I-R1 — Memory-ON Formal Result Integrity Audit

## 1. Scope and provenance

This is a read-only integrity audit of the archived Stage 1I text artifacts at:

`artifacts/stage1i_intersection_memory_on/released-style-intersection-memory-on_20261010T085023016082Z_eed64981/`

No experiment, Ollama request, Chroma query, or simulator execution was performed. No archived artifact, `runs/`, source, seed manifest, or PaperReconstruction file was modified. The experiment is **Released-code-derived Memory ON**, not a paper-faithful Memory implementation.

Two evidence classes are kept separate:

- **A — independently recomputed locally:** all results derived from the 103 archived JSON/JSONL/TXT files.
- **B — separately observed on RDP:** the post-batch Chroma query `[('langchain', 4040)]`. The persistent database was intentionally excluded, so Local cannot independently query or authenticate this count.

The archive commit is `acc84a6815d67cc41c729241ce7748c758837874`. The formal run itself records source commit `c05cbffd07c26800654ad57b1d6d40155652fdb0` on `codex/released-reproduction`.

## 2. Audit method

The audit parsed every batch JSON/JSONL file, all 20 episode summaries and run metadata files, all 20 step logs, and all 40 stdout/stderr files. It independently checked:

- file counts/extensions and forbidden database artifacts;
- ordered trial indices and seeds;
- summary/trial/step consistency, continuous `step_index` and environment steps;
- reward sums, final termination flags, four-action joint-action length, arrivals and collisions;
- the frozen derived-success rule;
- metadata identity and database lifecycle;
- warning/error/retry text signals;
- agreement with standalone and embedded batch summaries.

Before documentation editing, the deterministic aggregate SHA-256 inventory of the 103 archived files was `efb5944bb9793c1202cdc3d5753f37d8e02a124057c42c4e6d2b0bcdde2dfd4a`.

## 3. Artifact completeness

| Check | Independently observed | Result |
|---|---:|---|
| Total files | 103 | PASS |
| `.json` | 42 | PASS |
| `.jsonl` | 21 | PASS |
| `.txt` | 40 | PASS |
| Batch root files | metadata, summary, trials | PASS |
| Per-trial required files | 5 × 20 | PASS |
| `memory-db/` or DB/vector binaries | 0 | PASS |
| Trial indices | exact ordered 0–19 | PASS |
| Seeds | exact ordered 0–19, 20 unique | PASS |

The archive intentionally contains no Chroma database, SQLite, `.bin`, or `.pickle` content.

## 4. Batch result recomputation

Success was not inferred from the summary's independent `success` object; that object is explicitly unavailable. For every episode, success was recomputed as:

`completion_status == environment_terminated` AND all controlled vehicles arrived AND no controlled vehicle collided.

| Quantity | Recomputed from archive | Standalone summary | Embedded metadata summary | Result |
|---|---:|---:|---:|---|
| Planned | 20 | 20 | 20 | PASS |
| Attempted | 20 | 20 | 20 | PASS |
| Completed | 20 | 20 | 20 | PASS |
| Environment-completed | 20 | 20 | 20 | PASS |
| Failed | 0 | 0 | 0 | PASS |
| Successful | 6 | 6 | 6 | PASS |
| Unsuccessful completed | 14 | 14 | 14 | PASS |
| Success / planned | 0.30 | 0.30 | 0.30 | PASS |
| Success / environment-completed | 0.30 | 0.30 | 0.30 | PASS |

Termination distribution:

- `all_controlled_vehicles_arrived`: 6 seeds — 0, 10, 12, 13, 14, 18.
- `controlled_vehicle_collision`: 14 seeds — 1, 2, 3, 4, 5, 6, 7, 8, 9, 11, 15, 16, 17, 19.
- max-step guard, runtime/backend/parser/cleanup termination: 0 observed.

## 5. Per-seed result table

`C` is the stored four-CAV collision vector; `A` is the arrival vector.

| Seed | Termination | Steps | Reward | C | A | Derived success |
|---:|---|---:|---:|---|---|:---:|
| 0 | arrived | 76 | 13.25 | F,F,F,F | T,T,T,T | T |
| 1 | collision | 42 | -2.50 | T,T,F,F | F,F,F,F | F |
| 2 | collision | 44 | -2.50 | T,T,F,F | F,F,F,F | F |
| 3 | collision | 44 | -2.50 | T,T,F,F | F,F,F,F | F |
| 4 | collision | 41 | -2.50 | T,F,F,T | F,F,F,F | F |
| 5 | collision | 38 | -2.50 | T,F,F,T | F,F,F,F | F |
| 6 | collision | 49 | -2.50 | T,F,T,F | F,F,F,F | F |
| 7 | collision | 40 | -2.50 | T,T,F,F | F,F,F,F | F |
| 8 | collision | 45 | -2.50 | T,T,F,F | F,F,F,F | F |
| 9 | collision | 42 | -2.50 | F,T,F,T | F,F,F,F | F |
| 10 | arrived | 69 | 7.00 | F,F,F,F | T,T,T,T | T |
| 11 | collision | 44 | -2.50 | F,T,F,T | F,F,F,F | F |
| 12 | arrived | 72 | 11.75 | F,F,F,F | T,T,T,T | T |
| 13 | arrived | 65 | 7.50 | F,F,F,F | T,T,T,T | T |
| 14 | arrived | 72 | 12.00 | F,F,F,F | T,T,T,T | T |
| 15 | collision | 33 | -2.50 | T,T,F,F | F,F,F,F | F |
| 16 | collision | 34 | -1.25 | F,F,F,T | F,F,F,F | F |
| 17 | collision | 44 | -2.50 | T,F,F,T | F,F,F,F | F |
| 18 | arrived | 71 | 10.50 | F,F,F,F | T,T,T,T | T |
| 19 | collision | 45 | -2.50 | F,F,T,T | F,F,F,F | F |

## 6. Policy-step consistency

Per-seed policy steps are:

`0:76, 1:42, 2:44, 3:44, 4:41, 5:38, 6:49, 7:40, 8:45, 9:42, 10:69, 11:44, 12:72, 13:65, 14:72, 15:33, 16:34, 17:44, 18:71, 19:45`.

The independently summed total is **1010 policy steps**. For all 20 trials:

- `steps.jsonl` line count equals both episode and trial `total_steps`;
- indices are continuous `0..N-1`, environment steps are `1..N`;
- summed step reward equals episode/trial reward within `1e-9`;
- the final record has `terminated=true`;
- completion, termination, collision, arrival and derived success agree;
- each joint action contains exactly four ordered vehicle actions;
- run metadata seed and experiment identity agree with batch metadata.

No consistency discrepancy was found.

## 7. Memory-write count consistency

**A — locally recomputed:** 1010 policy steps and four controlled-vehicle actions per step imply `1010 × 4 = 4040` expected calls to the Released-style per-CAV pre-`env.step()` update location, under the Stage 1H runner contract. Every archived joint action has length four.

**B — RDP-only evidence:** the separately reported read-only Chroma query returned `[('langchain', 4040)]`. Because the DB is absent locally, this actual record count is not independently reproducible from the archive.

The equality `expected 4040 == RDP-observed 4040` supports **write-count completeness only**. It does not validate semantic content, retrieval relevance, embedding correctness, feedback correctness, uniqueness, or paper fidelity.

## 8. Warning and error audit

All 40 TXT files were searched. Exactly four stderr files are non-empty:

- Seed 0: `Number of requested results 2 is greater than number of elements in index 1, updating n_results = 1`. This is consistent with a fresh DB early retrieval. The episode completed normally in 76 steps and is nonfatal.
- Seeds 13, 14 and 18: `RuntimeWarning: divide by zero encountered in scalar divide` at `llm_controller/prompt_llm.py:381`, `ttc = distance / relativeSpeed`. All three completed normally by arrival and are nonfatal.

The same divide-by-zero warning class was recorded in sealed Stage 1F Memory OFF, so these artifacts do not support classifying it as Memory-ON-specific.

No stdout signal matching traceback, exception, error, failed, timeout, or retry was found. Trial records report 20 completed and zero failed, all run metadata report environment cleanup `closed`, and no max-step termination occurs. The runner states that LLM-call and parser-failure counters are unavailable; therefore the archive cannot produce numerical parser/backend failure counts. It does show no recorded runtime termination or textual failure signal.

Exact trial indices/seeds 0–19 occur once, with 20 unique trial/result paths and no replacement seed. No retry/replacement evidence is present. This establishes what is observable in the archived contract, not an external process-level proof beyond those files.

## 9. Metadata provenance

| Field | Archived value | Audit |
|---|---|---|
| Protocol | `released-style-intersection-memory-on`, v1 | consistent |
| Classification | `OUR EXPERIMENT DESIGN` | explicit |
| Memory definition | `Released-code-derived Memory ON` | not paper-faithful |
| Scenario | `intersection-multi-agent-v0` | consistent across 20 runs |
| Chat backend/model | Ollama / `qwen2.5:7b` | MODEL_SUBSTITUTION |
| Ollama/model ID | `0.32.9` / `845dbda0ea48` | stored provenance |
| Embedding | Ollama / `nomic-embed-text:latest` | MODEL_SUBSTITUTION |
| Embedding model ID | `0a109f422b47` | stored provenance |
| Endpoint | `http://127.0.0.1:11435` | chat and embedding |
| Timeouts | 120 s chat / 120 s embedding | consistent |
| Max-step guard | 300 | no guard termination |
| Manifest | `intersection-memory-off-controlled-v1`, v1 | reused; seeds 0–19 |
| Experiment Git | `c05cbffd...d1d6d40155652fdb0` | consistent across runs |
| Branch | `codex/released-reproduction` | consistent |
| Runtime | Python 3.8.20; gym 0.15.3; NumPy 1.24.4; pandas 1.3.5 | consistent |

The recorded lifecycle is: fresh empty database at batch start, persistent across policy cycles and ordered episode subprocesses, never cleared between seeds. All 20 run metadata files point to the same RDP database path.

Batch metadata records `git_dirty=true`. This is a provenance note, not proof that tracked source differed from `c05cbffd`. Pre-run untracked `runs/` artifacts are a plausible known cause, but the archive does not contain a contemporaneous porcelain listing; therefore tracked-source cleanliness at execution time is **not independently established** and no stronger claim is made.

## 10. OFF vs ON matched-seed comparison

Sealed Stage 1F-R1 evidence reports Memory OFF successes at seeds `0, 7, 10, 12, 13, 14, 17, 18` (8/20, 40%). Independently recomputed Stage 1I Memory ON successes are `0, 10, 12, 13, 14, 18` (6/20, 30%).

| Transition | Count | Seeds |
|---|---:|---|
| OFF success → ON success | 6 | 0, 10, 12, 13, 14, 18 |
| OFF success → ON collision | 2 | 7, 17 |
| OFF collision → ON success | 0 | — |
| OFF collision → ON collision | 12 | 1, 2, 3, 4, 5, 6, 8, 9, 11, 15, 16, 19 |

Allowed interpretation: **under the Released-code-derived cumulative Memory-ON protocol, the observed success rate was 30% (6/20), compared with 40% (8/20) for the controlled Memory-OFF baseline.** This is observational, not a causal estimate. ON carries cumulative ordered history across seeds, seed N is not an independent fresh-memory counterpart to OFF seed N, and local Qwen inference is not established as deterministic.

## 11. Fidelity and metric limitations

- Memory update remains per-CAV and pre-joint-`env.step()`; it is not outcome-grounded as described by the Paper.
- Same-cycle earlier-CAV writes may be visible to later CAVs.
- The cumulative lifecycle and explicit seed order are our experiment design, not paper-specified protocol.
- `qwen2.5:7b` and `nomic-embed-text:latest` are local substitutions; this is not GPT-4o-mini numerical reproduction.
- The controlled success rule is derived because the runner's independent success metric is unavailable.
- Fixed simulator seeds do not guarantee deterministic LLM outputs.
- PET, travel velocity, paper failure-denominator equivalence, collision causality and paper-level safety/efficiency metrics are not established by these artifacts.
- The text-only archive supports internal consistency, not independent cryptographic authentication of its RDP origin or local DB inspection.

## 12. Final verdict

**STAGE_1I_R1_PASS_WITH_NOTES**

The 103-file archive satisfies its contract. Independent recomputation confirms 20 ordered attempts/completions, zero execution failures, six successful arrivals, fourteen collision terminations, 30% controlled success, and 1010 policy steps with no summary/step discrepancy. Notes are the Released-style/paper gap, cumulative seed-order dependence, model substitutions, derived-success definition, four nonfatal stderr warnings, `git_dirty` provenance limitation, and the RDP-only status of the 4040 Chroma count. No causal OFF/ON claim is supported.
