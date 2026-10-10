# Stage 1H — Released-Style Memory-ON Minimal Port

## Purpose

This stage activates the author's dormant Memory retrieval/update interfaces with the minimum local Ollama embedding adaptation. **Released-style Memory ON is not claimed to be a paper-faithful Memory implementation.** Starting point: `a40a9c2567277ed4d912545c4921e3baa5feb862` on `codex/released-reproduction`.

## Changed files

- `llm_controller/llm_agent_action.py`: explicit `memory_mode=off|on` and conditional activation of existing calls.
- `llm_controller/memory.py`: explicit persistence path and embedding configuration; lazy OpenAI import.
- `llm_controller/embedding_backend.py`: minimal Ollama `/api/embed` adapter.
- `scripts/minimal_ollama_full_episode.py`: mode/config metadata and injected per-cycle Memory factory.
- `scripts/run_intersection_memory_on_batch.py`: ordered ON batch with one fresh persistent DB.
- `tests/test_released_style_memory_on.py`: fake-only regression coverage.

## OFF and ON behavior

**RUNTIME_ADAPTATION:** OFF remains the validated behavior: the runner does not import or instantiate `DrivingMemory`, passes `None`, performs negotiation and decisions with empty `past_memory`, then one joint `env.step()`.

**RELEASED_CODE:** ON preserves the existing `relative_memory()` and `memory_update()` function bodies. Per policy cycle it reopens `DrivingMemory` at the explicit path, negotiates, then for each CAV in released iteration order: constructs the existing query from the final two `prompt_info` lines; retrieves top-2 metadata; formats and inserts it at the existing prompt location; performs the unchanged chat/parser/action mapping; and immediately runs the released heuristic `memory_update()`. Only after all CAVs does it call joint `env.step()` once.

**KNOWN_PAPER_GAP:** writes remain before `env.step()` and are not grounded in transition outcomes. The shared store means a later CAV can retrieve an earlier CAV's same-cycle write. Both are intentional Released-style consequences, not Paper claims.

## Embedding adaptation

**MODEL_SUBSTITUTION:** chat remains independently configured as `qwen2.5:7b`. Memory defaults to Ollama `nomic-embed-text:latest` at `http://127.0.0.1:11435`. Backend, model, endpoint, timeout, and later RDP digest are separately recorded. The adapter implements LangChain's synchronous interface using `/api/embed`; the Ollama path imports no `OpenAIEmbeddings` and needs no OpenAI credential. The HTTP technique was compared with PaperReconstruction, but none of its altered timing, TTCP, coordinator, intent, safety, or other decision mechanisms was imported.

## Database lifecycle

**OUR_EXPERIMENT_DESIGN:** each formal ON batch gets a unique output directory and requires `memory-db/intersection-multi-agent-v0` to be absent. The same absolute path persists across policy cycles and ordered episode subprocesses for seeds 0–19; it is never cleared between seeds. The existing manifest is reused unchanged. No retry or replacement seed is introduced. Partial writes from a failed trial remain in the ordered history and the failure remains recorded. The single-episode runner requires `--memory-db-path` in ON mode, preventing accidental reuse of legacy `./db` state.

## Tests and limitations

Local fake tests cover OFF inactivity, ON per-CAV retrieval/decision/update ordering, pre-step writes, one `env.step()`, top-k 2, AST identity of released retrieval/update functions, fake Ollama embedding transport, separate chat/embedding models, explicit fresh DB rejection, and stable DB identity across subprocess commands. Existing minimal-port, full-episode, and controlled-batch suites must also pass without network, GPU, Ollama, or simulator experiments.

Result: `python -m unittest discover -s tests -p "test_*.py" -v` passed 33/33 tests. The Memory-ON batch `--preflight` also completed without creating a DB or calling Ollama.

Known limitations: this is not outcome-grounded Paper Memory; cumulative order confounds per-seed independence; `addMemory()` retains Released exception-printing semantics; Ollama results are not GPT-4o-mini numerical reproduction.

## Next RDP validation

Record installed Ollama version and digests for `qwen2.5:7b` and `nomic-embed-text:latest`; confirm repository-local imports and packages; run the new batch `--preflight`; then perform only a one-seed/small-step isolated-DB smoke test. Inspect retrieval, exact prompt insertion, writes, persistence, and metadata before authorizing the 20-seed batch.
