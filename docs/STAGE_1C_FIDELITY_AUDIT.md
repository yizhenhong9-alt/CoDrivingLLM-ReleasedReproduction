# Stage 1C Fidelity Audit — Intersection Memory-OFF Full Episode

## Evidence scope

- Released baseline: `f9e71fed08c1772cf4009ed61dfe91177019cf7d`.
- Stage 1C engineering baseline: `be89080b5f8e26dcb7ad0b887a0e3113730061cd`.
- Primary evidence: `Run_multi_CAV_LLM.py`, `highway_env/envs/common/abstract.py`, and `highway_env/envs/intersection_env.py`.
- This audit records released implementation behavior. It does not infer paper specifications where no checked evidence exists.

## Flow comparison

| Concern | Released code evidence | Stage 1C runner | Classification / fidelity note |
|---|---|---|---|
| Scenario | `Run_multi_CAV_LLM.py:54` creates `intersection-multi-agent-v0`. | Same environment ID. | Match. |
| Episode count | `Run_multi_CAV_LLM.py:58` loops 100 episodes. | Exactly one episode per invocation. | Intentional execution-boundary change; no policy change. |
| Reset / seed | `Run_multi_CAV_LLM.py:64` calls `env.reset()` with defaults. `abstract.py:176-200` seeds from the environment's incrementing seed when `is_training=True`. | Calls `env.reset(is_training=False, testing_seeds=<CLI seed>)` once. | Explicit reproducibility adaptation. For the first default episode, seed 0 targets the same numeric seed; equivalence of all hidden RNG state is not asserted. |
| Per-step object lifecycle | `Run_multi_CAV_LLM.py:68,71,75` creates Memory, Negotiation, and Action objects inside every loop iteration. | Recreates Negotiation and Action modules every policy cycle, sharing only the configured transport object. Does not create Memory. | Decision-module lifecycle matched; Memory intentionally isolated OFF. |
| Decision order | `Run_multi_CAV_LLM.py:70-80`: negotiation, per-CAV decisions in `env.controlled_vehicles` order, flatten results. | Same module calls and flatten expression. | Match. |
| Memory behavior | Released runner constructs `DrivingMemory` each cycle, while retrieval/update lines in the Action module are disabled. Construction can initialize embedding/DB infrastructure. | Passes `memory=None`; never imports or instantiates `DrivingMemory`. | Minimal side-effect isolation; retrieval/update remain OFF. |
| Transition | `Run_multi_CAV_LLM.py:85` calls `env.step(tuple(action), env)` once per loop. | Identical transition call once per completed policy cycle. | Match. |
| Simulator substeps | `abstract.py:520-540` performs simulator substeps inside the single environment step. | Uses the same environment step without extra simulator calls. | Match. |
| Termination | Released loop is `while not terminated` (`Run_multi_CAV_LLM.py:65`). Intersection termination is controlled collision, all controlled vehicles arrived, released duration limit, or configured off-road (`intersection_env.py:98-103`). | Stops on the returned `terminated`. Separately reports `max_steps_reached` for the external guard. | Environment termination matched; guard is explicitly not normal termination. |
| Collision | `intersection_env.py:98-103`; `abstract.py:492-500` also exposes `info["cav_crashed"]`. | Reports per-controlled-vehicle `crashed` flags without redefining collision. | Available from explicit simulator state. |
| Arrival | `intersection_env.py:279-282` defines `has_arrived`; all controlled arrivals terminate the episode. | Reports per-controlled-vehicle results from that method. | Available from explicit simulator method. |
| Success | No independent success definition in the Released runner. | Records `success` as unavailable with reason. | Unresolved; not inferred from arrival or reward. |
| Metrics | Released runner prints actions/reward, writes vehicle state to XLSX, and captures MP4 frames (`Run_multi_CAV_LLM.py:59-61,82-95`). | Records metadata, JSONL transitions, and a summary. | Recording infrastructure differs; no policy input is changed. |
| Rendering | Released runner renders twice and records one RGB frame per policy cycle (`Run_multi_CAV_LLM.py:86,90-91,101`). | No render or video. | Side-effect removal; possible timing/UI differences only. No simulator transition is added. |
| Error behavior | Released code has no retry/fallback wrapper. | Saves completed records and the original traceback, then re-raises. | Failure remains visible; no retry or substitute action. |
| LLM / parser counts | Released backend exposes the latest call only; parsers expose no counters. | Marks both counts unavailable. | Unresolved rather than estimated. |

## Original reset and state behavior

`AbstractEnv.reset()` resets `time`, `steps`, `done`, vehicle speed/position histories, recreates the road and vehicles, assigns IDs, and regenerates the observation. Within an episode, the Released runner does not call reset again. Stage 1C follows the same one-reset-per-episode boundary.

The original workbook, writer, and agent objects have different lifetimes: workbook/writer are per episode, while Memory and both decision modules are per policy cycle. Stage 1C preserves the decision-module cycle boundary, but replaces workbook/video output with one unique run directory.

## Unresolved evidence

- No checked Released source defines an independent binary `success` metric.
- No reliable released counter exists for LLM calls or parser failures; inferring counts from vehicle count would become unreliable during partial failures.
- The paper-level meaning of the 100-episode outer loop was not established in this audit.
- `max_steps=100` is a runner protection default, not the Released duration. The Released default duration bound is `50 × 5 - 1 = 249` policy steps for Intersection.
- Explicit `testing_seeds` is an engineering reproducibility interface. This audit does not claim it reproduces every RNG side effect of the default multi-episode seed progression.

## Stage 1C-R1 reliability classification

Stage 1C-R1 changes only runner observability and failure preservation:

- Git commit and branch remain ordinary strings when queries succeed. A failed query is recorded as `unavailable` with its exception type, reason, and traceback; no identity is invented.
- NumPy scalars and arrays remain converted to JSON-native values. An unsupported value is no longer silently coerced with `str()`; it is represented by an explicit `unsupported_type` record containing its qualified Python type, `repr`, and any `repr` failure.
- Environment cleanup has no transition or decision effect. A cleanup exception is written separately to `cleanup_error.json`. When a primary runtime error already exists, that primary error remains the propagated exception; when cleanup is the only failure, it becomes a recorded and propagated runtime error.

These are execution-record and error-handling adaptations. They do not modify Released Prompt, Parser, Negotiation, Safety, Action Mapping, simulator, Memory algorithm, or LLM backend behavior.
