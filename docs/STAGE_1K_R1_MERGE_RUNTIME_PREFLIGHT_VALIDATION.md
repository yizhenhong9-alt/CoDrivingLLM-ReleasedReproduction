# Stage 1K-R1 — Merge Runtime Preflight Validation

## 1. Scope and evidence boundary

This document records runtime evidence supplied from the laboratory RDP after Stage 1K. Codex did **not** independently reproduce these observations locally. No formal seed, formal Merge episode, or formal database was used. Stage 1J established the static contract; Stage 1K implemented the bounded preflight infrastructure; Stage 1K-R1 records the reported RDP observations against those contracts.

## 2. RDP environment

- Repository: `E:\YiZhen\Thesis\CoDrivingLLM-ReleasedReproduction`
- Python: `E:\YiZhen\conda_envs\codriving_repro\python.exe`
- Scenario: `merge-multi-agent-v0`
- Class: `highway_env.envs.merge_env_v1.MergeEnvMARL`
- Frozen author-runner config: simulation frequency 20, policy frequency 5, duration 40
- Temporary seeds: 987654 and 987655; neither is a formal experiment seed

## 3. Topology and configuration validation

The supplied preflight output reported:

- controlled vehicles: 3;
- road vehicles after reset: 6;
- action tuple arity: 3;
- environment class and all 20/5/40 config values matched Stage 1J/1K.

This supports the effective three-CAV contract and 200-policy-step duration boundary. Road vehicle count is a reset observation, not a promise that six vehicles persist throughout an episode, because Released Merge can remove crashed background vehicles.

## 4. Reset reproducibility and cross-seed variation

Two resets with temporary seed 987654 produced the same controlled state:

| CAV index | Lane | Position | Speed |
|---:|---|---|---:|
| 0 | `["a","b",0]` | `[10.453109916033014, 0.0]` | 15.699486280521658 |
| 1 | `["j","k",0]` | `[45.4856031849419, 10.5]` | 15.426814358658687 |
| 2 | `["j","k",0]` | `[163.7944782333397, 10.5]` | 15.382485957205098 |

Reported result: `same_seed_state_reproducible = true`.

Temporary seed 987655 produced different position/speed state:

| CAV index | Position | Speed |
|---:|---|---:|
| 0 | `[89.20552317131131, 0.0]` | 15.257224495319242 |
| 1 | `[6.131655397426219, 10.5]` | 16.704333989786534 |
| 2 | `[125.4453017826465, 10.5]` | 16.23906163043668 |

The supplied evidence therefore supports same-seed repeatability and cross-seed position/speed variation in the tested RDP stack. Destination `d` was **not** exposed by this JSON output; fixed destination remains Stage 1J source-audit evidence and the paper/code randomization gap remains documented.

## 5. Memory-OFF live smoke

A bounded three-policy-step live smoke used `qwen2.5:7b`, seed 987654, and Memory OFF. Reported joint actions were:

1. `[3,3,3]` — FASTER / FASTER / FASTER
2. `[1,1,1]` — IDLE / IDLE / IDLE
3. `[1,4,1]` — IDLE / SLOWER / IDLE

The supplied observation was three ordered CAV decisions and one joint transition per policy cycle, with no Memory/Chroma use and no traceback. The runner stopped at the `max_steps=3` guard. This is not a completed episode and is not a successful Merge case.

## 6. Released-style Memory-ON live smoke

A separate temporary three-policy-step smoke used:

`runs/merge-preflight-memory-on/memory-db/merge-multi-agent-v0`

This is explicitly not the future formal DB. Reported counts were 0 initially, then 3, 6, and 9 after cycles 1–3. A final read-only query reported `[('langchain', 9)]`. The equality `3 cycles × 3 CAVs = 9 attempted/observed records` supports count consistency only.

The smoke retained retrieval before decision, one write after each CAV decision, all writes before joint `env.step`, and same-cycle visibility. It validates the expected Released-style runtime order, not semantic correctness, retrieval quality, embedding quality, usefulness, or paper-faithful Memory.

## 7. GPU/model placement observation

The supplied `ollama ps` output after the ON smoke reported:

- `qwen2.5:7b`, ID `845dbda0ea48`, 100% GPU;
- `nomic-embed-text:latest`, ID `0a109f422b47`, 100% GPU.

The user observed Ollama llama-server processes on GPU1. GPU0 remained occupied by a pre-existing high-load workload. This records placement at the observation time; it does not establish absolute causal non-interference with GPU0.

## 8. Warnings and limitations

- A fresh-store top-k warning adjusted requested results from 2 to the one available record. It was nonfatal and is consistent with a small initial collection.
- No traceback was reported, but absence of a traceback is not a success metric.
- Seeds 987654/987655 are temporary and are not part of the formal manifest.
- No formal episode reached Released termination.
- No formal seed was consumed and no formal Merge DB was created.
- RDP observations are supplied evidence, not Local independent reproduction.
- Memory count integrity is not paper-faithful Memory validation.

## 9. Fidelity classification and verdict

| Finding | Classification |
|---|---|
| `merge-multi-agent-v0`, class, 3 CAVs, tuple arity 3 | RELEASED-CODE runtime observation consistent with source audit |
| 20/5/40 config | RELEASED-CODE intended-runner configuration |
| temporary seeds and bounded 3-step guards | PREFLIGHT DESIGN, not paper seeds/results |
| qwen/Ollama chat and Ollama embedding | MODEL/BACKEND SUBSTITUTION |
| pre-step per-CAV writes and same-cycle visibility | Released-style implementation, not paper-faithful Memory |

**STAGE_1K_R1_PASS_WITH_NOTES**

The RDP evidence is consistent with the Stage 1J/1K contract and supports preparation of a formal Merge Memory-OFF protocol. It does not authorize or constitute the formal 20-seed execution.
