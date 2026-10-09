# CoDrivingLLM Paper vs Released Code Fidelity Audit

## 1. Scope and evidence policy

This document audits the paper against author Released commit `f9e71fed08c1772cf4009ed61dfe91177019cf7d`. Stage 1A creates the document structure and evidence index only. It does not assert unverified paper quotations, page references, Algorithm line numbers, or reconstructed behavior.

Evidence labels to use:

- `PAPER_CONFIRMED`
- `RELEASED_CODE_CONFIRMED`
- `RUNTIME_CONFIRMED`
- `INFERENCE`
- `RECONSTRUCTION_CONVENTION`
- `SOURCE_REQUIRED`
- `UNRESOLVED`

PaperReconstruction conventions must never be described as author Released-Code implementation.

## 2. Source provenance

To record: paper version and bibliographic identity; author repository; Released commit and tree; audit commit; runtime artifact provenance.

## 3. Evidence record schema

Each finding must record:

| Field | Required content |
|---|---|
| Paper evidence | Section, page, Figure, Equation, or Algorithm line; exact location must be verified before entry. |
| Released evidence | Repository-relative file, function/class, verified line, commit. |
| Control flow | Caller, callee, inputs, outputs, side effects, and ordering. |
| Classification | Fully implemented, partially implemented, hard-coded, disabled, missing, reconstructed, or unresolved. |
| Gap | Precise difference without assuming it is a defect. |
| Experimental impact | Possible effect on decisions, transitions, Memory, metrics, or interpretation. |
| Minimal patch decision | Keep, patch, defer, reject, or source required. |
| Evidence source | Primary source or clearly labeled secondary audit/runtime artifact. |
| Unresolved evidence | Missing source, version, configuration, artifact, or author clarification. |

## 4. Planned audit chapters

1. Repository topology and executable entry points
2. Environment module and simulator dynamics
3. Observation and state sharing
4. Intent sharing
5. Semantic action space and low-level mapping
6. Conflict detection and centralized negotiation
7. TTCP and conflict-severity logic
8. Distributed per-CAV decision process
9. Prompt composition
10. Response parsing and failure semantics
11. Three-level safety assessment
12. Memory representation and persistence
13. Memory retrieval and prompt injection
14. Memory update and feedback timing
15. Algorithm 1 and actual caller/callee order
16. Joint `env.step` execution
17. Scenario coverage: Intersection, Merge, Highway, and Roundabout
18. Seed, episode, termination, and success protocol
19. Logging, artifacts, metrics, and evaluation infrastructure
20. Dependencies and runtime compatibility
21. Minimal Patch Decision Register
22. Unresolved questions and `SOURCE_REQUIRED` items
23. Experimental interpretation limits

## 5. Existing evidence index

The following are secondary research references. Their findings must be rechecked against the paper and Released commit before being promoted to this audit.

| Evidence set | Location | Intended use | Authority boundary |
|---|---|---|---|
| Original local Released checkout | `C:\Thesis\CoDrivingLLM` | Primary local Git/source comparison | Primary only when commit/tree identity is verified. |
| Prior paper/code mapping | `C:\Thesis\CoDrivingLLM-PaperReconstruction\notes\reference\paper_code_mapping.md` | Candidate finding index | Secondary audit; verify every claim. |
| Memory/reflection fidelity audit | `C:\Thesis\CoDrivingLLM-Thesis\notes\codriving_memory_reflection_fidelity_audit.md` | Memory timing and Algorithm 1 candidate findings | Secondary audit; paper locations require re-verification. |
| Released TTCP mapping | `C:\Thesis\CoDrivingLLM-PaperReconstruction\notes\stage1C3B_released_ttcp_mapping_audit.md` | TTCP caller/callee candidates | Released mapping reference, not a substitute for current line verification. |
| Released coordinator mapping | `C:\Thesis\CoDrivingLLM-PaperReconstruction\notes\stage1C4B_released_coordinator_mapping_audit.md` | Negotiation evidence candidates | Secondary audit. |
| Released safety mapping | `C:\Thesis\CoDrivingLLM-PaperReconstruction\notes\stage1C5B_released_safety_mapping_audit.md` | Safety and action-enforcement candidates | Secondary audit. |
| Baseline reconciliation | `C:\Thesis\CoDrivingLLM-PaperReconstruction\notes\stage2C3_released_vs_paper_reconstruction_reconciliation.md` | Prevent Released/Reconstruction conflation | Reconstruction conventions remain non-author behavior. |
| Thesis reproduction summary/protocol | `C:\Thesis\CoDrivingLLM-Thesis\notes\reproduction_summary.md` and `reproduction_protocol.md` | Historical runtime evidence and blockers | Runtime evidence is backend/config specific, not paper numerical reproduction. |

## 6. Finding register

No substantive findings are entered in Stage 1A. Findings will be added only after primary-source verification.

| Finding ID | Topic | Paper evidence | Released evidence | Classification | Gap | Experimental impact | Minimal patch decision | Status |
|---|---|---|---|---|---|---|---|---|
| TBD | TBD | `SOURCE_REQUIRED` | `SOURCE_REQUIRED` | `UNRESOLVED` | TBD | TBD | TBD | Not audited |

## 7. Algorithm and timing comparison template

To be completed with verified evidence:

| Ordered stage | Paper Algorithm 1 | Released caller/callee | Before/after `env.step` | Memory OFF | M0 | M1 | Evidence status |
|---|---|---|---|---|---|---|---|
| TBD | `SOURCE_REQUIRED` | `SOURCE_REQUIRED` | `UNRESOLVED` | TBD | Deferred | Deferred | Not audited |

## 8. Unresolved questions

Record questions without inventing answers, including unpublished experiment configuration, exact paper seeds, Memory evaluator conditions, scenario assets absent from Released Code, and author-only execution details.
