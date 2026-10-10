# Stage 1G — Memory Contract and Multi-Scenario Reproduction Audit

## 1. Scope

This audit defines the evidence boundary and candidate design for future controlled Memory-ON experiments in Intersection, Merge, and Highway. It does not implement Memory ON, execute a simulator or Ollama, alter a seed manifest, or change the frozen Stage 1F results.

Evidence labels used throughout:

- **PAPER**: supported by the published CoDrivingLLM paper.
- **RELEASED_CODE**: directly observable in the author's released source lineage.
- **OUR_RECONSTRUCTION**: a previous implementation choice in `CoDrivingLLM-PaperReconstruction`; it is not author evidence.
- **OUR_EXPERIMENT_DESIGN**: a proposed controlled protocol.
- **UNRESOLVED**: the available evidence does not determine the answer.

## 2. Evidence hierarchy

Evidence is applied in this order: (1) paper, (2) Released Code and preserved fidelity evidence, (3) existing audit documents in this repository, and (4) `CoDrivingLLM-PaperReconstruction` only as a record of our earlier choices. A runnable reconstruction is not promoted to a paper or author fact.

Primary source inspected: *Towards Interactive and Learnable Cooperative Driving Automation: A Large Language Model-Driven Decision-Making Framework*, especially Section III-A, Section III-D, Algorithm 1, and Figures 7–8. Source-code locations below are repository-relative and line numbers refer to the audited revisions.

## 3. Paper Memory contract

### Supported statements

- **PAPER — stored information.** Section III-A states that the final scenario description, conflict description, and decisions are stored in a memory database in vector form. Section III-D describes a mapping among scenarios, actions, and results, with feedback used as experience for later decisions.
- **PAPER — retrieval timing and use.** Before each LLM reasoning invocation, relevant memories are retrieved and added to the prompt as few-shot experience. Current scenario and conflict descriptions form the vector-search input; cosine similarity ranks memories and the most similar items are selected.
- **PAPER — update intent.** Memory Augment evaluates the effect of CAV actions from the previous scenario. When an action increases danger, negative feedback such as avoiding similar actions is associated with the experience. Algorithm 1 places retrieval before reasoning and memory evaluation/addition after action-related processing, but the paper does not publish an executable evaluator contract.
- **PAPER — empirical claims.** Figure 7 reports performance after interaction counts 0, 5, 10, and 20+; improvement is faster in Highway/Merge and slower in Intersection/Roundabout. Figure 8 illustrates an Intersection case in which retrieval of a similar failed experience changes the later decision and resolves the conflict.

### What the paper does not establish

The following remain **UNRESOLVED**: whether storage occurs after every interaction or only selected outcomes; the exact success/failure evaluator and threshold; whether successful and failed experiences use different schemas; whether memory is per-CAV or shared; precise top-k; embedding model; persistence across steps, episodes, processes, or random seeds; database reset/prepopulation order; and whether one “interaction” means an episode, policy cycle, per-CAV decision, or another unit. Figures 7–8 do not identify seeds, database checkpoints, insertion order, or rule out other state carried across trials.

Accordingly, Figure 7 supports learning with increasing prior interaction exposure, not a unique database lifecycle. Figure 8 supports the usefulness of an available similar failed experience, not that every evaluated episode must begin empty or that the database is necessarily shared.

## 4. Released Code Memory behavior

### Construction and persistence

- `Run_multi_CAV_LLM.py:58-68` resets once per episode but constructs `DrivingMemory(env)` inside every policy-cycle loop.
- `llm_controller/memory.py:12-21` constructs `OpenAIEmbeddings` and a persistent Chroma collection at `./db/<env.spec.id>`. Object recreation therefore targets the same scenario-named on-disk store; absent deletion or a different working directory, data can survive policy cycles, episodes, and processes.
- The path is scenario-specific but neither seed-specific nor CAV-specific. The code has no explicit lifecycle/reset/checkpoint contract.

### Retrieval and write interfaces

- `DrivingMemory.retrieveMemory()` (`memory.py:24-30`) calls Chroma `similarity_search_with_score` and returns document metadata; its interface defaults to top-5.
- `LlmAgent_action_module.relative_memory()` (`llm_agent_action.py:117-125`) actually requests top-2. Its query is the last two lines of `prompt_info`; returned metadata are rendered as prior negotiation result, final action, and comments.
- `DrivingMemory.addMemory()` (`memory.py:62-70`) stores `sce_descrip` as page content and metadata keys `human_question`, `negotiation_result`, `final_action`, and `comments`. Write exceptions are printed and swallowed.
- `memory_update()` (`llm_agent_action.py:127-139`) would store only the last prompt line as scenario text. It writes string `None` for human question and negotiation, the parsed action, and a heuristic comment derived from conflict relation/action (or “recommended to FASTER” without conflict). It does not inspect a post-transition outcome.

### Actual call graph and runtime state

- `Run_multi_CAV_LLM.py:70-85` executes negotiation, per-CAV action decisions, action flattening, then one joint `env.step(tuple(action), env)`.
- In `llm_agent_action.py:35-51`, the action loop calls the LLM for each controlled vehicle. The `memory_update` call is commented out at line 48.
- In `send_to_chatgpt()` the retrieval call is commented out at line 153 and `past_memory` is forced to an empty string at line 154. The prompt retains a location for `past_memory`, but no retrieved experience is inserted.

Thus the actual **RELEASED_CODE** runtime constructs Memory infrastructure every policy cycle, but both retrieval and update are inactive. Merely uncommenting both calls would write each CAV's heuristic record immediately after that CAV decision and before the joint environment transition. It would not evaluate the previous action's observed outcome; earlier CAV writes could also become visible to later CAVs in the same policy cycle, making behavior dependent on CAV iteration order.

## 5. Paper vs Released Memory mapping

| Memory aspect | PAPER | RELEASED_CODE | Assessment |
|---|---|---|---|
| Initialization | Not specified | Reconstructed each policy cycle, same persistent path | Unresolved |
| Ownership/scope | Not specified | One collection per `env.spec.id`, shared by callers | Unresolved |
| Retrieval timing | Before each LLM reasoning invocation | Interface exists; call disabled | Gap |
| Retrieval query | Current scenario + conflict description | Last two lines of action prompt | Partial; exact equivalence unverified |
| Retrieved content | Similar prior experience | Metadata: negotiation, action, comments | Partial |
| Prompt insertion | Retrieved examples augment prompt | Slot exists; empty at runtime | Gap |
| Write/update timing | Evaluate prior scenario/action impact | Disabled; if enabled, pre-`env.step()` after each CAV decision | Gap |
| Write condition | Danger-increasing action receives negative feedback; exhaustive rule absent | If enabled, every per-CAV decision | Gap / Unresolved |
| Stored content | Scenario, conflict, action/result feedback | Last prompt line plus mostly synthetic metadata | Partial |
| Outcome grounding | Previous action impact is assessed | No post-step outcome used | Gap |
| Persistence | Not specified | Chroma persistent directory | Unresolved |
| Episode/seed boundary | Not specified | Same scenario path can cross both | Unresolved |
| Database lifecycle | Not specified | Implicit working-directory state | Gap |
| Embedding dependency | Vector form; model unspecified | OpenAI embeddings and credential side effect | Partial / Unresolved |

The most consequential mismatch is update timing/outcome grounding. Enabling the dormant calls verbatim is not a defensible implementation of the paper description.

## 6. Existing PaperReconstruction Memory-related differences

`CoDrivingLLM-PaperReconstruction` was inspected read-only at commit `2045ecda1c94f0d945ca200ac7f195c107b36089`.

- **OUR_RECONSTRUCTION — backend/configuration.** `llm_controller/memory.py:7-35` adds selectable OpenAI/Ollama embeddings and an explicit persistence directory. Instrumentation records queries, scores, and writes. Ollama substitution and observability are implementation choices because the paper does not name that embedding model or logging contract.
- **OUR_RECONSTRUCTION — enabled calls.** `llm_controller/llm_agent_action.py:111-116,281-310` enables retrieval and update under `memory_mode="on"` while retaining the broad released query/schema.
- **Potentially inconsistent with PAPER.** Phase 3B and Phase 4 update after each per-CAV decision but before `env.step()` (`scripts/phase3b_full_episode_memory_on.py:375-419`; `scripts/phase4_reproduction_experiment.py:769-837`). Therefore writes remain pre-outcome and do not implement the paper's previous-action impact evaluation.
- **OUR_RECONSTRUCTION — lifecycle.** Phase 3A validates a fresh store and reopening persistence. Phase 3B uses a fresh empty run database. Phase 4 puts a fresh Chroma store inside each independent episode run and requires an initial count of zero (`phase4_reproduction_experiment.py:128-157,534-545,946-964`). This prevents cross-episode learning and is not established by the paper.
- **Unrelated mechanisms that can confound Memory.** The reconstruction includes state/scene sharing, intent buffers, TTCP/risk buffers, coordinator logic, identity handling, and safety/candidate layers. They alter the context/query or decision pipeline and must not be imported as part of a minimal Memory port without separate evidence and approval.
- **Unfinished.** A paper-faithful, outcome-grounded write evaluator and a frozen multi-episode Memory lifecycle remain undefined.

An empty independent database is useful isolation, but it cannot explain Figure 8 if the relevant failed experience must already exist at first retrieval, and it measures mostly within-episode acquisition rather than the cumulative exposure suggested by Figure 7.

## 7. Intersection / Merge / Highway applicability

| Scenario | Released execution facts | Memory applicability | Required adaptation / risk |
|---|---|---|---|
| Intersection | `intersection-multi-agent-v0`; four controlled vehicles; `MultiAgentAction`; centralized negotiation and per-CAV decisions | Same `DrivingMemory` interface and scenario-specific DB path are usable | Define shared/per-CAV ownership, outcome evaluator, same-cycle visibility, and matched seed manifest |
| Merge | Commented alternative in `Run_multi_CAV_LLM.py:46-54`; multi-agent environment exposes four controlled vehicles | Same class/interface is mechanically usable; longitudinal action prompt path is shared with Intersection | Add and validate a scenario-specific runner/config/metrics and seed manifest; do not assume Intersection termination or success definitions |
| Highway | Commented `highway-v0`; configuration creates multiple controlled vehicles but action type is `DiscreteMetaAction` | `DrivingMemory` can instantiate at `db/highway-v0`; Highway prompt/action vocabulary includes lane changes | `DiscreteMetaAction.act()` applies tuple/list input only through `action[0]` to one `controlled_vehicle` (`highway_env/envs/common/action.py:135-221`). Existing multi-CAV joint-action and cooperative-memory assumptions therefore do not carry over |

Merge and Intersection use the multi-agent negotiation/decision context, whereas Highway's effective environment action and terminal/reward ownership are single-agent-oriented. Prompts also differ: Highway includes lateral actions, while Merge/Intersection use the longitudinal subset (`llm_agent_action.py:53-76`). These differences change query representation and the meaning of an “experience.” The scenario-derived database path prevents cross-scenario retrieval by default, which should be preserved.

Conclusion: one common storage API and logging schema may serve all three, but one common behavioral contract is not yet defensible. Highway requires its execution/agent-ownership contract to be resolved first; each scenario needs its own database namespace, seed manifest, metric definitions, and validation gate.

## 8. Candidate controlled Memory-ON contract

The following is the minimum defensible target, not authorization to implement it:

1. **PAPER:** Retrieve before each relevant action-reasoning invocation, using current scenario and conflict information, and insert selected similar experiences into the existing Memory prompt section.
2. **RELEASED_CODE:** Preserve the released textual query construction and top-2 formatting initially, but label these as released implementation details rather than paper facts. Freeze and hash the actual query/prompt in tests.
3. **OUR_EXPERIMENT_DESIGN:** Use scenario-separated, explicitly named databases; record embedding backend/model/digest, database identity/checkpoint hash, initial/final counts, retrieval/write events, top-k, scenario, seed, agent identity, policy cycle, and timestamps. No silent write failure.
4. **UNRESOLVED:** Do not enable writes until an outcome-grounded rule specifies (a) which transition is evaluated, (b) which reliable simulator fields determine increased danger/success/failure, (c) which experiences qualify, and (d) the feedback schema. The released pre-step heuristic is insufficient.
5. **UNRESOLVED:** Decide shared versus per-agent ownership. If shared, prohibit visibility of writes from earlier CAVs during the same policy cycle (retrieve from one frozen pre-cycle snapshot, transition once, then evaluate/write) unless evidence supports within-cycle learning.
6. **OUR_EXPERIMENT_DESIGN:** OFF and ON evaluations must use the same ordered scenario-specific seed manifest, simulator configuration, model and model digest, prompts/parsers, timeout/error policy, action ordering, and metrics. LLM nondeterminism remains a limitation and must be recorded.
7. **OUR_EXPERIMENT_DESIGN:** Each matched evaluation seed should start from an identical clone of a frozen scenario-specific Memory checkpoint. For the primary causal comparison, disable learning writes during evaluation (retrieval-only ON), or conduct write-enabled adaptation as a separately labelled experiment.
8. **UNRESOLVED:** An Ollama embedding substitution is required for the local/RDP deployment but neither its model nor equivalence is specified by the paper. It must be frozen and validated before a checkpoint is built.

This separates “does access to the same prior experience change outcomes?” from “does an online learner improve as experience accumulates?” Mixing them would make seed order and database history confound the ON/OFF effect.

## 9. Memory database lifecycle alternatives

### A. Independent per-seed, fresh/empty Memory

Provides strong isolation and reproducibility. However, ON begins equivalent to OFF until an experience is written, and subsequent effects measure within-episode online acquisition. It is not a strong match for Figure 8's already retrievable similar failure, and it does not naturally represent Figure 7's increasing prior interaction counts. Paper support: **UNRESOLVED**. Phase 4 precedent: **OUR_RECONSTRUCTION**.

### B. Cumulative Memory across seeds 0–19

Most closely resembles an informal reading of Figure 7 as accumulated interactions and the implicit Released Code persistent path. It is highly order-dependent: seed 0 and seed 19 receive different treatments, ON is not matched per seed, retries can contaminate the store, and a failure can alter all later trials. Paper details and the definition of interaction remain **UNRESOLVED**. The Released Code would permit this accidentally, but does not define or audit it.

### C. Pre-populated Memory with N prior interactions

Most closely matches Figure 8 when the checkpoint contains the illustrated kind of failed experience. It also enables a clean causal OFF-vs-ON comparison: every evaluation seed receives the same immutable checkpoint, while OFF receives no retrieval. To study Figure 7, separately build ordered training streams and freeze checkpoints at 0/5/10/20+ interactions, then evaluate each checkpoint on a distinct, fixed matched evaluation set. This is **OUR_EXPERIMENT_DESIGN**, not a recovered author protocol.

### Direct answer for seeds 0–19

For the primary matched experiment, do not carry mutations from one evaluated seed into the next. Start every ON seed from the same cloned, frozen, scenario-specific pre-populated checkpoint, and keep it retrieval-only during evaluation. Run cumulative online learning only as a separate order-controlled experiment. A fresh empty store per seed is acceptable as an explicit within-episode-learning ablation, not as the sole Memory-ON reproduction.

## 10. Recommended matched OFF/ON experiment design

Use two separately reported protocols:

1. **Frozen-memory causal evaluation (recommended primary):** build the Memory checkpoint using a disjoint, predetermined training seed/order; freeze its manifest and hash; clone it for every evaluation seed; compare OFF against retrieval-only ON on identical evaluation seeds and configurations. This answers the effect of available prior memory with minimal history confounding.
2. **Cumulative-learning curve (secondary):** use a fixed training stream and explicitly defined interaction unit; freeze checkpoints at 0/5/10/20+; evaluate checkpoints on a separate fixed set without further writes. This is the closest defensible reconstruction of Figure 7 while acknowledging missing author details.

Do not claim numerical reproduction of GPT-4o-mini when chat or embedding inference uses Ollama. Record failed trials rather than rebuilding a favorable checkpoint.

## 11. Multi-scenario implementation roadmap

1. **Contract gate:** resolve the five blockers in Section 13 and approve an outcome/evaluation specification before code changes.
2. **Intersection first:** reuse the frozen Stage 1F Memory-OFF batch infrastructure, seed manifest, metrics, failure policy, and joint-action ordering. Add Memory event logging and checkpoint cloning only after the contract is frozen. Validate with local fake tests, then an RDP preflight and a small smoke run before any batch.
3. **Merge second:** create a separate seed manifest and scenario-specific configuration/termination/metric audit. Reuse generic batch/result-integrity infrastructure, not Intersection-specific success assumptions. Establish a new OFF baseline before matched ON.
4. **Highway third:** first decide whether the experiment is the released effective single-agent environment or a new multi-agent adaptation. The latter is a semantic change and cannot be called unmodified Released Code. Only then define agent ownership, negotiation relevance, action application, metrics, and a Highway seed manifest; establish OFF before ON.
5. **Controlled expansion:** for every scenario, freeze environment/config hash, seed order, model identifiers, prompt/parser hashes, database checkpoint identity, metrics, and error policy. Promote from fake tests to one seed, a small batch, and only then the planned evaluation.

Currently reproducible metrics must be limited to fields with verified scenario definitions (e.g., recorded reward, steps, termination and reliably exposed collision/arrival fields). Paper success rate, travel velocity, PET, and cross-scenario aggregation remain scenario-specific audit items; absent released aggregation infrastructure must be labelled reconstructed evaluation infrastructure.

## 12. Future Paper vs Released vs PaperReconstruction comparison roadmap

Preserve an evidence matrix with rows for: scene/state sharing, intent sharing, conflict detection and TTCP, coordinator, safety, action decision and mapping, Memory query/retrieval/insertion/update/outcome grounding/lifecycle, scenario configuration, agent/action ownership, seed and model protocol, termination, and metrics/aggregation. Columns must separately state:

- what the **PAPER** explicitly specifies;
- what **RELEASED_CODE** actually executes (including disabled code);
- what **OUR_RECONSTRUCTION** added or changed and why;
- what remains **OUR_EXPERIMENT_DESIGN** or **UNRESOLVED**;
- expected experimental impact and validation evidence.

Every future artifact should retain commit, config, seed-manifest, model, prompt/parser, and Memory-checkpoint identities so the final comparison is auditable rather than retrospective.

## 13. Unresolved questions and implementation blockers

Before Memory-ON implementation, exactly these decisions require explicit resolution:

1. **Outcome-grounded write contract:** the evaluated transition, authoritative simulator evidence, write qualification rule, and feedback schema.
2. **Database lifecycle and interaction unit:** primary protocol (frozen pre-populated versus cumulative/empty), definition of an interaction, checkpoint construction order, and whether evaluation-time writes are enabled.
3. **Memory ownership and same-cycle isolation:** shared versus per-CAV storage and whether writes may become visible within the same joint policy cycle.
4. **Highway execution semantics:** released effective single-agent evaluation versus an explicitly non-fidelity multi-agent adaptation, including action/termination/metric ownership.
5. **Embedding contract:** backend/model/version (or digest), similarity compatibility, and frozen checkpoint identity for Ollama-based Memory ON.

## 14. Final recommendation

Adopt a two-protocol design: frozen, pre-populated, scenario-specific retrieval-only checkpoints for the primary matched OFF/ON causal comparison; and a separately labelled, ordered cumulative-learning/checkpoint experiment for the Figure 7 question. Do not implement by merely uncommenting Released calls. Begin with Intersection only after the five decisions above are approved, then audit Merge, and treat Highway as a separate execution-contract gate.

**NOT_READY_FOR_MEMORY_ON_IMPLEMENTATION**
