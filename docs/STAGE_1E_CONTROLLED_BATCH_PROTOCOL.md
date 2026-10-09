# Stage 1E — Controlled Intersection Memory-OFF Batch Protocol

## Classification and evidence basis

This protocol is **OUR EXPERIMENT DESIGN**. It is not the original Released
100-loop runner, the authors' unpublished seed manifest, or a numerical
reproduction of the paper.

Stage 1D established that the paper repeats each scenario 20 times with
different random seeds but does not publish their values. The Released entry
script instead contains a 100-iteration loop with an implementation-derived
implicit seed progression. A repository-wide audit found no existing formal,
version-controlled seed manifest to reuse.

## Frozen seed policy

`experiments/intersection_memory_off_seeds.json` freezes the 20 unique integer
seeds 0 through 19 in ascending order. Consecutive integers were selected
because the policy is transparent, deterministic, human-readable, and cannot
be mistaken for a discovered author seed list. The manifest records its schema,
version, selection policy, and an explicit false `paper_seed_claim`.

Changing the manifest requires a new manifest ID/version and a new protocol;
completed results must never be relabelled under a modified manifest.

## Architecture and episode boundary

`scripts/run_intersection_memory_off_batch.py` is orchestration only. For each
seed it launches `scripts.minimal_ollama_full_episode.py` as a fresh Python
process. Consequently each trial creates a fresh simulator environment and
reuses the already validated Negotiation → Action Decision → one joint
`env.step()` per cycle implementation. The batch code does not import or
reimplement Prompt, Parser, Negotiation, Safety, Action Mapping, Memory, or
simulator transition logic.

Memory remains OFF through the delegated runner's existing `memory=None` path;
neither the batch module nor Local tests import `llm_controller.memory`.

## Success classification

The batch derives success only when all three conditions hold:

1. `completion_status == environment_terminated`;
2. every controlled-vehicle arrival flag is true;
3. every controlled-vehicle collision flag is false.

This is an implementation of the paper's textual definition using reliable
Released simulator primitives. The original single-episode
`success=unavailable` evidence remains unchanged. `max_steps_reached`, runtime,
backend, parser, and orchestration errors are never success.

## Failure accounting

Every manifest seed is attempted exactly once in order. A failure preserves the
delegated runner artifacts, captured stdout/stderr, error summary and batch
record, then the batch advances to the next fixed seed. There is no retry,
fallback, replacement seed, or silent deletion.

The summary reports both:

- successful trials / all 20 planned manifest trials;
- successful trials / environment-completed trials.

Neither denominator is claimed to reproduce the paper's unpublished handling
of LLM/API/parser failures.

## Outputs

Every invocation creates a unique exclusive batch directory containing:

- `batch_metadata.json`: protocol/version, Git commit/branch/dirty state,
  scenario, Memory mode, backend/model/endpoint, optional Ollama version/model
  digest, timeout, guard, manifest identity, package versions and timestamps;
- `trials.jsonl`: exactly one record per seed after a complete batch attempt,
  including status, termination, reward/steps, arrival/collision evidence,
  derived success, duration, relative result directory and error details;
- `batch_summary.json`: planned/attempted/completed/failed/success counts, both
  denominators, termination counts and wall-clock time;
- one isolated `trial-NN-seed-S` tree per seed, containing the delegated
  single-episode result and captured process output.

PET and travel-velocity paper metrics remain `UNRESOLVED` and are not added.

## Model identity and substitution

The default model is Ollama `qwen2.5:7b`, therefore this remains a
`MODEL_SUBSTITUTION`. Metadata accepts Ollama version and model digest supplied
from the RDP preflight; no digest is invented and Local preflight never contacts
Ollama. Results may be described only as a Released implementation pipeline
reproduction with local LLM substitution.

## Interruption, resume, and rerun

The runner never overwrites a batch directory or a trial directory. Completed
artifacts survive interruption. Stage 1E intentionally does **not** implement
resume: restarting creates a new batch directory and never auto-runs or mutates
the interrupted directory. Explicit, audited resume semantics are deferred to
a later stage.

## max-step guard

The batch default is 300 policy cycles. This is **OUR EXPERIMENT DESIGN** safety
protection and is deliberately above the Released Intersection duration boundary
around step 249, allowing the simulator's own duration termination to occur.
The CLI rejects values below 250. The guard does not redefine simulator
termination, and reaching it is not success.

## Read-only preflight

From the repository root, run:

```powershell
python -m scripts.run_intersection_memory_off_batch `
  --preflight `
  --manifest experiments/intersection_memory_off_seeds.json `
  --backend ollama `
  --model qwen2.5:7b `
  --endpoint http://127.0.0.1:11435 `
  --timeout 120 `
  --max-steps 300 `
  --ollama-version '<verified-on-RDP>' `
  --model-digest '<verified-on-RDP>'
```

This validates configuration and prints metadata only. It creates no batch
directory, contacts no Ollama service, and executes no simulator or trial.

## Limitations

- Seeds 0–19 are not author-provided Paper seeds.
- Qwen2.5:7b is not GPT-4o mini.
- LLM generation is not made deterministic merely by fixing environment seeds.
- Paper failure-denominator handling is unknown.
- PET, travel-velocity aggregation, Memory ON and resume are outside Stage 1E.
- A real 20-trial command remains withheld until RDP preflight is reviewed.
