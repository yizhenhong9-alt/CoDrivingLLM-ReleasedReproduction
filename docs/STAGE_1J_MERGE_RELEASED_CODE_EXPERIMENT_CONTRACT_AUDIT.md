# Stage 1J — Merge Released-Code Experiment Contract Audit

## 1. Scope

This is a static, read-only contract audit for a future Merge experiment. It does not run Merge or Intersection, invoke Ollama/GPU/Chroma, create a seed manifest, change a runner, or modify formal results. The audited formal repository state is branch `codex/released-reproduction`, HEAD `d8a885466351b26bcbdb55ae5f12450197b16b54`.

The intended claim remains **Released implementation pipeline reproduction with local LLM substitution**, not a numerical reproduction of the paper.

## 2. Evidence hierarchy

1. **PAPER-SPECIFIED** — the published paper/PDF and its extracted text.
2. **RELEASED-CODE** — author commit `f9e71fed08c1772cf4009ed61dfe91177019cf7d`, with current compatibility changes separately identified.
3. **OUR EXPERIMENT DESIGN** — runners, seed ordering, guards, storage layout, archival, and derived metrics introduced by this reproduction.
4. **UNRESOLVED** — unsupported or conflicting details.

`CoDrivingLLM-PaperReconstruction` is not used as evidence of author code and no reconstruction feature is imported.

## 3. Paper Merge contract

The available paper evidence is the PDF and the existing extraction at `C:\Thesis\CoDrivingLLM\tmp\pdfs\paper.txt`.

| Finding | Classification | Evidence |
|---|---|---|
| Merge is one of four experimental scenarios. | PAPER-SPECIFIED | Section IV-A, paper page 7; extracted lines 623–640 name intersection, roundabout, highway, and merge. |
| Every scenario is repeated 20 times with different random seeds. | PAPER-SPECIFIED | Section IV-A, page 7; extracted lines 632–636. |
| Seeds randomize initial positions, speeds, and expected destinations. | PAPER-SPECIFIED | Section IV-A, page 7; extracted lines 634–636. The Released Merge code does not fully implement the stated destination randomization; see Section 8. |
| Success means all CAVs safely finish their tasks and reach their destination. | PAPER-SPECIFIED | Section IV-A, page 7; extracted lines 641–643. |
| Merge reaches about 75% success after 10 interactions in the Memory study. | PAPER-SPECIFIED aggregate claim | Section IV-C, paper page 9; extracted lines 734–744. The paper does not expose its seeds, database lifecycle, or executable success evaluator. |
| Exact Merge CAV/HDV count, seed values/order, duration, policy frequency, action tuple, and reset API. | UNRESOLVED | Not specified in the available paper text. |
| PET and travel velocity are Merge metrics. | UNRESOLVED / not supported | Section IV-D restricts the compared-method experiment and PET/travel-velocity discussion to the unsignalized intersection (extracted lines 766–827). No evidence found that these are reported as Merge metrics. |

The paper's 20 repetitions support a future count of 20 episodes. Choosing exact seeds `0..19` and their order remains **OUR EXPERIMENT DESIGN**, not a paper claim.

## 4. Released Code Merge environment contract

### Identity and author runner

- Exact environment ID: `merge-multi-agent-v0`, registered to `highway_env.envs:MergeEnvMARL` (`highway_env/envs/merge_env_v1.py:340-343`). `highway_env/envs/__init__.py:1` exports this implementation.
- `MergeEnvMARL` subclasses `MergeEnv` and changes action/observation to multi-agent forms (`merge_env_v1.py:313-332`).
- The author runner includes Merge as a commented selectable alternative: a config of simulation frequency 20, policy frequency 5, duration 40, followed by `gym.make('merge-multi-agent-v0', config=config)` (`Run_multi_CAV_LLM.py:46-54`). The checked-in active line is Intersection, so Merge is included as an intended author path but is not the default executed scenario.
- If the commented author Merge config is activated, only simulation frequency differs from the environment default. Policy frequency and duration remain 5 Hz and 40 s (`merge_env_v1.py:42-44`).
- The author loop resets, constructs Memory, negotiates, decides per controlled vehicle, flattens actions, and performs one `env.step(tuple(action), env)` (`Run_multi_CAV_LLM.py:58-85`). Rendering/video/XLSX calls follow the transition (`:86-101`) and are recording side effects, not additional simulator transitions.

## 5. Controlled vehicle topology

The effective default is **three controlled CAVs and three initially requested HDVs**, not four controlled vehicles.

1. `MergeEnvMARL.default_config()` advertises `controlled_vehicles: 4` (`merge_env_v1.py:313-331`).
2. `AbstractEnv.__init__` copies that value to `self.num_CAV`, and `reset()` passes it into `_reset(num_CAV=self.num_CAV)` (`abstract.py:77,176-196`).
3. However, the default `traffic_density` is 3 (`merge_env_v1.py:51`), and the density-3 branch assigns `num_CAV = 3` regardless of whether a nonzero value was supplied; it also assigns `num_HDV = 3` (`:181-190`). This overrides the advertised 4.
4. `_make_vehicles()` appends controlled vehicles first: `num_CAV // 2` main-road vehicles, then the remaining ramp vehicles (`:221-278`). With three CAVs the stable construction order is one main-road CAV followed by two ramp CAVs. Three HDVs are then appended (`:280-296`).
5. A final early-collision cleanup can remove road vehicles (`:298-300`); it does not rewrite `controlled_vehicles`, but the exact background count after reset should be observed during RDP preflight.

All entries in `controlled_vehicles` are created using `self.action_type.vehicle_class` and are therefore action-controlled CAVs. HDVs are created using `other_vehicles_type` and exist in `road.vehicles`. Merge negotiation intentionally considers all road vehicles, unlike Intersection, which considers only controlled vehicles (`llm_controller/llm_agent_negotiation_system.py:39-63,142-160`).

The list order is deterministic by construction for a reset and is the order used by the action loop and `MultiAgentAction`. Vehicle positions and speeds vary, but ordering does not sort by position.

## 6. Action / joint-action contract

- **RELEASED-CODE:** `MergeEnvMARL` configures `MultiAgentAction` containing `DiscreteMetaAction` (`merge_env_v1.py:313-324`).
- `MultiAgentAction.space()` is a Gym tuple with one discrete subspace per current controlled vehicle. Its `act()` zips the supplied tuple with `agents_action_types` in controlled-vehicle order (`highway_env/envs/common/action.py:225-250`).
- The base environment applies the joint action once, simulates `simulation_frequency // policy_frequency` internal physics ticks, then observes/rewards/terminates (`abstract.py:451-539`). These internal physics ticks are not extra policy decisions.
- The author runner explicitly flattens one result per controlled vehicle and calls `env.step(tuple(action), env)` (`Run_multi_CAV_LLM.py:77-85`). The same call shape is valid for Merge provided the tuple has exactly three entries at the effective default.
- The current action agent already routes both Merge and Intersection to the unchanged longitudinal subset `{IDLE:1, FASTER:3, SLOWER:4}` (`llm_controller/llm_agent_action.py:58-84`). Parser and mapping can therefore be reused without semantic change.
- Negotiation and per-CAV action flow are scenario-aware. Merge uses all `road.vehicles`, a 120 m reaction range, then decides only for `env.controlled_vehicles` (`llm_agent_negotiation_system.py:39-63,89-99,142-160`; `llm_agent_action.py:38-56`).

No action semantic modification is justified by this audit. A preflight must assert `len(env.controlled_vehicles) == 3`, `len(env.action_space.spaces) == 3`, and that the returned action list length equals three before any live step.

## 7. Termination and arrival semantics

### Released termination

`MergeEnv._is_terminal()` terminates only when:

1. any controlled vehicle has `crashed`, or
2. `steps >= duration * policy_frequency` (`merge_env_v1.py:138-147`).

With defaults (and the author commented config), the duration boundary is `40 * 5 = 200` policy steps. The first call to `step()` increments `steps` before simulation and termination evaluation (`abstract.py:465-475`), so a collision-free episode terminates on policy step 200. A future guard must be **at least 200**, with a larger guard such as 250 used only as protection. Intersection's 249-step boundary must not be copied.

There is no off-road termination in the Merge override and no arrival termination. The docstring saying “or when the access ramp has been passed” is inconsistent with the executable predicate and must not be treated as behavior.

Background-vehicle collisions are removed when no controlled CAV has crashed (`merge_env_v1.py:149-158`); they do not independently terminate the episode. `step()` records per-controlled-vehicle terminal flags using the same collision/duration conditions (`:127-136,144-147`).

### Arrival and success

Merge does expose `has_arrived(vehicle)`: destination lane endpoint contains `"d"` and longitudinal local coordinate is at least 15 m (`merge_env_v1.py:302-303`). Every created CAV and HDV is routed to fixed destination node `d` (`:262-296`). Released Code exposes no independent success field, does not terminate when all CAVs arrive, and the author runner does not aggregate success.

The paper rule can be operationalized as an explicitly **derived** metric:

`completion_status == environment_terminated AND all controlled vehicles have_arrived AND no controlled vehicle crashed`.

This is a defensible **OUR EXPERIMENT DESIGN derived from PAPER-SPECIFIED success language and RELEASED-CODE fields**, but it is not a Released metric. It must be frozen and fake-tested before a batch. Because duration termination is normal in Merge, `environment_terminated` alone is not success.

## 8. Seed/reset/randomization contract

- `reset(is_training=False, testing_seeds=N)` directly seeds global NumPy and Python `random`, resets counters/state, rebuilds the scene, and returns the observation (`highway_env/envs/common/abstract.py:176-211`). This compatibility API is reusable.
- Merge road construction passes `self.np_random`, but vehicle spawn-point selection, speed, and location noise use global `np.random`; the explicit reset seeding therefore governs those current calls (`merge_env_v1.py:217,230-259`).
- CAV/HDV spawn points are randomly selected without replacement. Initial speed and location noise are randomized (`:230-259`).
- Destinations are not randomized: every vehicle plans to node `d` (`:262-296`). This conflicts with the paper's general statement that expected destinations are randomized and is a fidelity gap, not permission to modify the simulator.
- `AbstractEnv.__init__` calls an initial `reset()` (`abstract.py:44-87`), but the runner's explicit testing reset reconstructs the environment for the requested seed. A preflight should confirm repeat-reset identity in the actual RDP dependency stack.
- Seeds `0..19`, their order, and a future Merge manifest remain **OUR EXPERIMENT DESIGN**. No manifest should be created until the preflight validates this contract.

## 9. Memory OFF applicability

The generic policy-cycle function in `scripts/minimal_ollama_full_episode.py:185-250` already preserves the author-derived order: negotiation, action decision over controlled vehicles, flatten, exactly one joint `env.step()`. With `memory_factory=None`, it passes `memory=None`; the action module only retrieves/updates when `memory_mode == "on"` (`llm_agent_action.py:38-56,152-188`). The runtime-only import of `llm_controller.memory` is also inside the ON branch (`minimal_ollama_full_episode.py:340-353`). Thus OFF can still avoid `DrivingMemory` import/instantiation.

However, the executable runner is hard-coded to Intersection in its description, default output directory, metadata, and `gym.make()` (`minimal_ollama_full_episode.py:253-270,289-300,332-333`). It cannot yet run a correctly labelled Merge experiment. Before RDP, introduce a thin scenario selection interface (or a separate thin Merge wrapper) that selects only approved IDs and derives metadata/output naming from the selected ID. Do not alter `run_episode`, prompts, parser, action mapping, negotiation, safety, or simulator code.

`environment_terminal_reason()` and outcome collection are structurally reusable because Merge exposes `has_arrived`; nevertheless, scenario-specific tests must freeze Merge's 200-step duration and confirm that arrival is not treated as the environment's termination trigger (`minimal_ollama_full_episode.py:104-138`).

## 10. Released-style Memory ON applicability

Stage 1H is mechanically applicable after the same scenario-selection change:

- `DrivingMemory` accepts an explicit persistence directory and otherwise derives `./db/<env.spec.id>` (`llm_controller/memory.py:9-25`).
- The action agent retrieves top-2 using the last two prompt lines, inserts the formatted experience into the existing prompt, and immediately writes one record after each controlled-vehicle decision (`llm_agent_action.py:38-56,122-149,152-188`).
- The write occurs before joint `env.step()`, and later CAVs in the same cycle may see earlier CAV writes. This remains Released-style behavior and must not be “fixed.”
- With three effective controlled vehicles, expected writes are **three per completed policy cycle**, not four. A 200-step collision-free duration episode would therefore attempt 600 writes. Failed `addMemory()` calls are printed and swallowed by the existing Released method (`memory.py:53-60`), so DB counts remain an integrity observation, not an assumed guarantee.
- Merge and Intersection prompts follow the same longitudinal action branch, but scene descriptions, conflict participants, 120 m reaction range, and query text differ. Prompt/query equality must be checked with fake agents before RDP; no Merge-specific prompt rewrite is authorized.

Released-style Memory ON remains **not paper-faithful Memory** because writes are pre-transition heuristic records rather than evaluations of the prior action's observed outcome.

## 11. DB lifecycle

A future Merge ON batch may reuse the Stage 1I lifecycle only as **OUR EXPERIMENT DESIGN / Released-code-derived design**:

fresh absent Merge-specific DB at batch start → persistent across cycles → persistent across ordered seeds → never clear between seeds → no retries or replacement seeds.

The current Intersection ON orchestrator hard-codes `memory-db/intersection-multi-agent-v0` and is not reusable unchanged (`scripts/run_intersection_memory_on_batch.py:11-35,59-107`). A future Merge orchestrator must use `memory-db/merge-multi-agent-v0`, scenario-correct metadata, a Merge manifest, and a minimum guard compatible with 200 steps.

If paths are constructed from exact environment IDs as above, Intersection and Merge DBs are isolated by distinct directories. Isolation is not guaranteed by Chroma itself if a caller passes the same explicit path; the future orchestrator must reject an existing or cross-scenario path and record the resolved absolute DB identity.

## 12. Metrics / success-definition status

| Metric | Status |
|---|---|
| Per-step joint action, reward, terminated, timing, environment step | Reliable runner instrumentation; OUR EXPERIMENT DESIGN. |
| Controlled-CAV collision | Available from `vehicle.crashed`; Released field. |
| Controlled-CAV arrival | Available from `MergeEnv.has_arrived`; Released field. |
| Success | No independent Released metric. Use only the frozen derived rule in Section 7, labelled derived. |
| Duration termination | Exact 200-step Released boundary at current defaults. |
| Background collision | Background crashed vehicles can be removed; not a stable aggregate outcome without extra instrumentation. Do not invent one. |
| PET / travel velocity | Not established as Merge paper metrics and not reliably produced by the current minimal runner; unavailable. |
| LLM call/parser failure count | Unavailable unless reliably instrumented without semantic change. Preserve raw errors/tracebacks. |

Reward is useful for record integrity, but it is not the paper success definition. The Merge reward is an average over controlled vehicles (`merge_env_v1.py:55-90`) and must not be converted into success.

## 13. Reusable Intersection infrastructure

Reusable without behavioral change:

- `ChatBackend` and chat/embedding model separation;
- policy-cycle order in `run_episode` and one joint transition per cycle;
- JSON/JSONL serialization, unique run directories, metadata, traceback and cleanup recording;
- no retry/fallback/replacement policy;
- ordered batch/result-integrity schema after scenario fields become parameters;
- text-only archival with source/destination hashes;
- OFF path's lazy avoidance of `DrivingMemory`;
- ON embedding adapter and Released-style retrieval/update functions.

Not reusable as-is:

- Intersection environment ID/output labels;
- four-action assertions and expected four writes per step;
- 250-minimum/249-boundary assumptions;
- Intersection seed manifest;
- Intersection success evidence and result baselines;
- Intersection ON DB path and archive protocol name;
- any PET/travel-velocity interpretation.

## 14. Merge-specific required changes

No Released controller or simulator change is required or authorized. Before RDP preflight, the minimal reproduction infrastructure needs:

1. scenario selection limited to `intersection-multi-agent-v0` and `merge-multi-agent-v0` in the single-episode runner, including correct metadata/output defaults;
2. scenario-aware terminal-reason tests with Merge's 200-step boundary and collision precedence;
3. an explicit post-reset topology assertion/record (three controlled CAVs at current code, action tuple arity three, background count observed);
4. Merge-specific fake tests for negotiation → three decisions → one joint step, joint ordering, OFF no-Memory import/instantiation, and ON three writes per completed policy cycle;
5. a future Merge-only seed manifest and OFF/ON batch wrappers only after preflight approval;
6. Merge-specific DB namespace and fresh-path rejection.

These are runner/test/instrumentation changes. Prompts, parser, action mapping, negotiation, safety, Memory semantics, and `highway_env` must remain unchanged.

## 15. Risks / unresolved items

1. **Configuration contradiction:** `controlled_vehicles=4` is overridden to 3. Formal work must use observed effective topology, not the config label.
2. **Runner hard-coding:** the current single-episode and both batch runners identify Intersection.
3. **Termination/arrival separation:** reaching destinations does not terminate Merge; a result may terminate by duration with arrival arrays requiring explicit evaluation.
4. **Paper/code randomization gap:** Released Merge fixes destination `d`, while the paper says expected destinations are randomized.
5. **Background cleanup:** road vehicle count may change when crashed HDVs are removed.
6. **Memory history confounding:** cumulative ON results depend on ordered prior seeds and same-cycle visibility.
7. **DB path safety:** an explicitly supplied shared path could mix scenarios unless the future orchestrator enforces isolation.
8. **Runtime gate:** repository-local Gym 0.15.3 behavior, tuple arity, reset reproducibility, prompt creation, and one real step have not yet been validated on RDP for Merge.
9. **Success metric:** derivation is defensible but not an author-implemented metric; it requires approval/freeze before the formal batch.
10. **Paper details:** actual seed values, exact CAV count, Merge-specific configuration, database lifecycle, interaction unit, and per-scenario raw results remain unresolved.

These items make an immediate 20-seed batch unsafe.

## 16. Proposed next RDP preflight

The next stage should implement and locally fake-test only the thin scenario parameterization, then perform this bounded RDP sequence:

1. verify branch/commit, clean tracked state, Python/package versions, Ollama/model digests, and repository-local import resolution;
2. static/preflight print of resolved Merge configuration without an episode: environment ID, class, duration 40, policy frequency 5, simulation frequency (15 default or explicitly frozen author-comment 20), controlled count, road vehicle count, action-space tuple arity, ordered vehicle IDs/lane indices, and reset seed;
3. repeat reset with one approved temporary seed and compare initial topology/state identity; do not create the formal seed manifest yet;
4. Memory OFF fake transport, one policy cycle, exactly three action outputs and one `env.step(tuple(action), env)`; preserve errors without retry/fallback;
5. only after review, a bounded one-seed/one-to-three-step live Merge smoke test;
6. separately, a fresh temporary Merge DB ON smoke confirming top-2 retrieval contract, three attempted writes per completed policy cycle, same-cycle visibility, and no Intersection DB access;
7. inspect metadata/JSONL/error artifacts, then decide whether to freeze a Merge seed manifest and authorize an OFF formal batch.

The preflight must explicitly choose simulation frequency 15 (environment default) or 20 (author runner's commented Merge config). Because the author runner supplies 20 when selecting Merge, **20 Hz is the stronger Released-runner candidate**, but this selection must be recorded rather than silently assumed.

## 17. Fidelity classification table

| Item | Classification | Status |
|---|---|---|
| Merge among evaluated scenarios | PAPER-SPECIFIED | Confirmed. |
| 20 repetitions, different random seeds | PAPER-SPECIFIED | Confirmed; exact seeds absent. |
| `merge-multi-agent-v0` / `MergeEnvMARL` | RELEASED-CODE | Confirmed. |
| Commented Merge config: simulation 20 Hz, policy 5 Hz, duration 40 s | RELEASED-CODE intended runner path | Confirmed but inactive in checked-in runner. |
| Effective 3 CAV + requested 3 HDV topology | RELEASED-CODE behavior | Confirmed statically; RDP observation required. |
| Tuple of three discrete meta-actions in controlled order | RELEASED-CODE behavior | Confirmed statically. |
| Collision or 200 policy steps termination | RELEASED-CODE behavior | Confirmed. |
| `has_arrived` destination-lane predicate | RELEASED-CODE behavior | Confirmed; not a terminal predicate. |
| All-arrived/no-collision derived success | PAPER-SPECIFIED + OUR EXPERIMENT DESIGN | Defensible, requires protocol freeze. |
| Seeds `0..19` and ascending order | OUR EXPERIMENT DESIGN | Not yet frozen for Merge. |
| Ollama `qwen2.5:7b` and Ollama embeddings | MODEL/BACKEND SUBSTITUTION | Reusable after preflight. |
| Cumulative fresh-batch Released-style Memory ON | OUR EXPERIMENT DESIGN / Released-code-derived | Reusable with Merge-specific DB; not paper-faithful. |
| Three writes per policy step | Released-style implementation consequence | Expected at effective topology; validate with fake/DB counts. |
| PET/travel velocity for Merge | UNRESOLVED | Do not report. |

## 18. Final readiness verdict

**STAGE_1J_READY_WITH_OPEN_ITEMS**

The source contract is sufficiently established to design the next bounded Merge preflight, but the repository is **not ready for a formal 20-seed Merge batch**. Required open items are thin scenario parameterization, Merge-specific topology/termination/fake tests, an approved simulation-frequency choice, a frozen derived-success rule, RDP reset/action-space validation, and scenario-isolated OFF/ON orchestration. No core algorithm or simulator modification is indicated.
