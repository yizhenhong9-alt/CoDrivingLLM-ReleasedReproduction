# Stage 1C Local Regression Results

## Scope

Local tests use fake environments, fake Negotiation/Action agents, and NumPy values. They do not import the simulator stack, contact Ollama, or execute an actual episode.

## Required checks

| Check | Evidence |
|---|---|
| Negotiation → Action Decision → `env.step()` | Event-order assertion in `test_order_one_step_per_cycle_joint_action_and_memory_off`. |
| One transition per policy cycle | Fake environment step-call count equals completed policy-cycle count. |
| Joint action identity | NumPy `int32` values reach fake `env.step()` unchanged and in order; JSON copy preserves values/order. |
| Memory OFF | `memory=None`, no `llm_controller.memory` import, and no `db/` creation. |
| Environment termination | Fake episode stops immediately on returned terminal state. |
| Max-step guard | Distinct `max_steps_reached` and `max_steps_guard` results. |
| Error visibility | Backend/parser-like exception is re-raised; invalid action ID fails before transition. |
| Partial-progress error summary | Runtime error summary retains completed-step count, accumulated reward, error text, and traceback. |
| JSON safety | NumPy scalar and array values serialize with the standard JSON encoder after conversion. |
| No overwrite | Exclusive run-directory creation rejects an existing run ID and preserves its files. |
| Released semantics protection | Git regression guard compares protected source trees with Stage 1B-R1 baseline; existing tests compare Released prompt/parser/action-mapping ASTs. |

## Final Local result

Command:

```text
python -m unittest discover -s tests -p 'test_*.py' -v
```

Result after the final implementation: 15 tests passed. RDP simulator/Ollama validation remains separate.

## Stage 1C-R1 additions

The reliability suite adds normal and failed Git metadata queries, typed unknown-value serialization, cleanup traceback capture, cleanup-only failure, and simultaneous runtime/cleanup failure with completed JSONL records preserved.

Final Stage 1C-R1 result using the same discovery command: **19 tests passed**.
