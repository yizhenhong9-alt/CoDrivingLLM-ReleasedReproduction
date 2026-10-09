# CoDrivingLLM Released Reproduction Provenance

## Source of truth

- Author repository: `https://github.com/FanGShiYuu/CoDrivingLLM`
- Author remote name in this repository: `upstream`
- Released commit: `f9e71fed08c1772cf4009ed61dfe91177019cf7d`
- Released Git tree: `f47860567cf65b93e8c23700ddc015eb6d7d591d`
- Local verified source repository: `C:\Thesis\CoDrivingLLM`

## Local initialization method

This repository was initialized on 2026-10-09 by cloning the verified local Git repository with full history, checking out the specified Released commit, and creating the branch `codex/released-reproduction`.

The clone was created from Git objects, not by copying a working directory. Untracked files from the source repository, including local PDFs, notes, temporary files, logs, databases, and other artifacts, were not imported.

The annotated tag `released-f9e71fed` identifies the immutable author Released commit. The tag is local unless explicitly pushed in a later authorized stage.

## Tree identity invariant

Before adding reproduction-management files, the new checkout had:

- `HEAD = f9e71fed08c1772cf4009ed61dfe91177019cf7d`
- `HEAD^{tree} = f47860567cf65b93e8c23700ddc015eb6d7d591d`
- no tracked or untracked working-tree changes

Future reproduction commits must retain this commit in their ancestry. Changes to author source files must be individually registered and justified; they must never be silently folded into the baseline.

## Project objective

The project will reproduce the released CoDrivingLLM code with the smallest necessary, evidence-backed compatibility changes. It will preserve released decision semantics unless a separately reviewed research variant explicitly states otherwise.

The planned local backend is Ollama with `qwen2.5:7b`. This substitution is **not implemented in Stage 1A**.

The initial experimental baseline is planned as Memory OFF. Memory variants are deferred:

- M0: Released-Code Memory Timing, retaining the released helper placement and behavior.
- M1: Paper-Inspired Post-Transition Memory Timing, treated as a separate research variant requiring additional evidence and design review.

Neither M0 nor M1 is implemented in Stage 1A.

## Execution boundary

### Local Windows Codex

- Git and source audit
- static comparison and documentation
- future source development and non-runtime checks
- no assumption that a local Ollama endpoint is available

### Lab Windows RDP

- simulator execution
- Ollama and model execution
- GPU-dependent work when actually required
- controlled runtime validation and experiments

Project transfer from Local to RDP remains a manual user operation.

## Algorithm protection

The following must not be silently changed: prompts, parsers, action mapping, centralized negotiation, TTCP logic, safety logic, Memory semantics, simulator behavior, and joint `env.step` ordering.

PaperReconstruction conventions such as C0-C3 safety, Protected IDLE, reconstructed identity handling, or redesigned intent sharing are not author Released-Code behavior and are not part of this baseline.
