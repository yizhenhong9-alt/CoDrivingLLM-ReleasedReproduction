# Stage 1N — Highway Released-Code Experiment Contract Audit

## 1. Scope

This document is a static, documentation-only audit of the Highway experiment contract in author Released commit `f9e71fed08c1772cf4009ed61dfe91177019cf7d`. It does not reset or step an environment, contact an LLM or embedding service, initialize memory/Chroma, create a database, define a seed manifest, or implement a Highway runner. The repository state examined before this audit was branch `codex/released-reproduction` at `ea88bd137aa3271f7a53a59190d7563fb7e62d39`.

The decision gate is intentionally strict: reproducing the author's executable behavior and operationalizing the paper's stated success concept are different questions.

## 2. Evidence hierarchy

| Class | Meaning in this audit |
|---|---|
| **PAPER EXPLICIT** | A statement or figure in the CoDrivingLLM paper. |
| **RELEASED CODE ACTUAL** | Behavior statically established from the author Released baseline. |
| **OUR EXPERIMENT DESIGN** | A future choice needed where the paper/code do not define an executable contract. It is not author evidence. |
| **UNRESOLVED** | Evidence is absent or static inspection cannot establish the runtime fact. |

PaperReconstruction is not used as author evidence. Current reproduction code is cited only to assess compatibility, never to redefine the Released contract.

## 3. Paper Highway contract

Paper references below use the PDF page number and the printed IEEE page number.

| Item | Paper evidence | Classification |
|---|---|---|
| Scenario | Section IV-A lists four scenarios and Figure 4(c) labels the Highway case; the text calls it a “four-way highway scenario” (PDF p. 7 / IEEE p. 11900). | Explicitly specified |
| Road topology | Figure 4(c) depicts a straight, multi-lane highway populated by CAVs and HDVs. Exact lane count, length, directionality, and road graph are not stated in prose. “Four-way” is a scenario label, not an executable topology specification. | Inferable visually, not explicit |
| CAV/HDV counts | Figure 4(c) contains vehicle labels, but the paper does not state authoritative numerical counts or which depicted vehicles are simulator-controlled. | Not specified |
| Controlled vehicles | Cooperative CAV decision-making is described generally; the Highway control topology and action-space cardinality are not specified. | Not specified |
| Randomization | Section IV-A states that each scenario is repeated 20 times with different random seeds that randomly generate initial positions, speeds, and expected destinations (PDF p. 7 / IEEE p. 11900). | Explicitly specified |
| Repetitions/seeds | 20 repetitions using different random seeds (same source). The exact 20 seed values and RNG lifecycle are absent. | Repetition count explicit; seed list/lifecycle not specified |
| Success | Section IV-A defines success as all CAVs safely finishing their tasks and reaching their destinations (PDF p. 7 / IEEE p. 11900). | Explicit concept; executable Highway predicate not specified |
| LLM | Section IV-A identifies GPT-4o mini as the base model (PDF p. 7 / IEEE p. 11900). | Explicitly specified |
| Negotiation/cooperation | The framework is cooperative and the ablation discusses the negotiation/reasoning submodule. Section IV-B says car-following dominates Highway and success remains high with or without the reasoning submodule (PDF p. 8 / IEEE p. 11901). Highway-specific invocation frequency and participants are not defined. | General behavior explicit; executable Highway contract not specified |
| Memory | Section IV-C/Figure 7 reports Highway memory performance reaching 100% after five interactions and attributes this to simpler conflict patterns (PDF pp. 8–9 / IEEE pp. 11901–11902). DB lifecycle, per-agent query/write timing, top-k, and cross-seed persistence are not specified. | Outcome explicit; lifecycle not specified |
| PET | Section IV-D discusses PET for the unsignalized-intersection comparison and successful cases; no executable Highway PET contract, conflict-point rule, or aggregation is stated. | Highway-specific metric not specified |
| Travel velocity | Section IV-D discusses travel velocity for successful-case method comparison, but does not give a Highway-specific sampling/weighting/aggregation contract. | Highway-specific executable contract not specified |

## 4. Released runner Highway path

`Run_multi_CAV_LLM.py` is unchanged by Stage 1N.

1. The Merge override is commented at `Run_multi_CAV_LLM.py:46-50`.
2. Intersection is the active environment at line 54; `gym.make('highway-v0')` is present but commented at line 55. Highway therefore is a dormant selectable path, not the default run.
3. The outer loop is `range(100)` at line 58, not the paper's 20 repetitions.
4. Each repetition creates an MP4 writer and XLSX workbook/output (`Run_multi_CAV_LLM.py:16`, `:59-61`), calls `env.reset()` without an explicit seed (`:64`), and loops until the environment returns `terminated` (`:65`).
5. Every policy cycle constructs `DrivingMemory(env)` (`:68`), constructs and invokes the negotiation agent (`:71-72`), constructs the action agent and requests actions for every `env.controlled_vehicles` entry (`:75-77`), flattens the returned arrays (`:80`), and calls exactly one `env.step(tuple(action), env)` (`:85`).
6. It renders interactively and as RGB frames, appends MP4 frames, and logs state rows to XLSX (`:86`, `:90-94`); it closes the writer after termination (`:102`).
7. In the pristine Released `llm_agent_action.py`, memory retrieval and update calls are commented. The runner's per-cycle `DrivingMemory` construction can still initialize external memory infrastructure, but no active Released action-path retrieval/update results from those commented calls.

The runner assumes the number/order returned by `env.controlled_vehicles`: it requests one decision per listed controlled vehicle and preserves that iteration order in the flattened tuple. It never adapts the tuple to the environment's declared single discrete action space.

## 5. Environment registration

The exact registration chain is:

`highway-v0` → `highway_env.envs:HighwayEnv` (`highway_env/envs/highway_env.py:151-154`) → class `HighwayEnv` (`:13-21`). `HighwayEnvFast` is a separate variant and is not selected by the Released runner.

The class builds a straight road through `RoadNetwork.straight_road_network(...)` (`highway_env/envs/highway_env.py:63-66`). The helper creates parallel lanes between nodes `"0"` and `"1"`, with a default length of 10,000 (`highway_env/road/road.py:289-301`). It is not a crossing/four-arm road graph.

## 6. Effective Highway config

| Setting | Base/default | Highway default / author override | Effective dormant Highway path |
|---|---:|---:|---:|
| Observation | — | `Kinematics`, observation neighbor count 15 (`highway_env/envs/highway_env.py:24-32`) | `Kinematics` |
| Action | `DiscreteMetaAction` (`highway_env/envs/common/abstract.py:107-115`) | `DiscreteMetaAction` (`highway_env/envs/highway_env.py:33-38`) | `DiscreteMetaAction` |
| Lanes | — | 4 (`highway_env/envs/highway_env.py:40`) | 4 straight parallel lanes |
| Controlled vehicles | — | 4 (`:42`) | 4 |
| Background `vehicles_count` | — | 20 (`:41`) | 20; total road vehicles are 24 after creation |
| Simulation frequency | 15 Hz (`highway_env/envs/common/abstract.py:114`) | no Highway override | 15 Hz |
| Policy frequency | 5 Hz (`:115`) | no Highway override | 5 Hz |
| Duration | — | 40, commented as seconds (`highway_env/envs/highway_env.py:44`) | Actual termination compares policy-step counter directly with 40 |
| Off-road terminal | — | false (`:49`) | disabled |
| Collision terminal | — | first controlled vehicle's `crashed` flag (`:113-117`) | enabled only for `self.vehicle` |
| Runner override | commented Merge-only dict | none for Highway | defaults above |

## 7. Controlled/background vehicle topology

The previous shorthand “Highway is single-agent” is incomplete and must not be repeated as a vehicle-count claim.

- `_create_vehicles()` splits 20 background vehicles among four controlled-vehicle creation groups (`highway_env/envs/highway_env.py:68-88`).
- In each group it creates the controlled vehicle first with `Vehicle.create_random(speed=25, lane_id=None, spacing=2)`, converts it to the configured action vehicle class, and appends it to both `controlled_vehicles` and `road.vehicles` (`:73-83`). Creation/decision order is therefore deterministic list order 0 through 3.
- It then creates autonomous background vehicles using `other_vehicles_type`, which defaults to `IDMVehicle`, and appends them to `road.vehicles` (`:84-88`; default type in `highway_env/envs/common/abstract.py:116`).
- `controlled_vehicles` is configurable, but the dormant author Highway path supplies no override, so the effective count is four.
- The action type is not `MultiAgentAction`; the available multi-agent wrapper (`highway_env/envs/common/action.py:225-250`) is never selected by Highway config.

Therefore the topology is **four declared controlled vehicles but single-discrete-action execution**. Statically, the first controlled vehicle is the only vehicle receiving the externally supplied meta-action. Runtime confirmation should verify identities/order and resulting trajectories, but the consumption rule itself is explicit in code.

## 8. Action contract

### Mapping

`DiscreteMetaAction.ACTIONS_ALL` (`highway_env/envs/common/action.py:140-146`) defines:

| ID | Semantic action |
|---:|---|
| 0 | `LANE_LEFT` |
| 1 | `IDLE` |
| 2 | `LANE_RIGHT` |
| 3 | `FASTER` |
| 4 | `SLOWER` |

The LLM ActionAgent uses the same five Highway mappings (`llm_controller/llm_agent_action.py:64-84`) and returns one-element NumPy action arrays after parsing (`:189-194`).

### End-to-end container behavior

1. Author runner: collects four one-element results, flattens them, and passes `tuple(action)`.
2. Simulator API declaration: action space is `spaces.Discrete(5)` (`highway_env/envs/common/action.py:210-211`), so its nominal contract is one integer.
3. Actual fork implementation: `DiscreteMetaAction.act()` uses the scalar directly when input is not a tuple; when it is a tuple, it indexes `action[0]` and ignores all remaining entries (`:217-221`). A list is not specially handled and would be used as a dictionary key/index, so it is not a supported substitute.
4. Current generic runner: `scripts/minimal_ollama_full_episode.py:321-386` likewise builds all controlled-vehicle decisions and sends `tuple(action)` exactly once per policy cycle (`:351`). Highway is not in `APPROVED_SCENARIOS` (`:16`), so this path is not currently selectable.

The Released author runner therefore supplies four syntactically accepted values, but only the first is executed. Additional tuple entries are silently ignored. Preserving this behavior reproduces Released execution; changing to genuine four-agent control would require a simulator/action semantic change and would no longer be a minimal Released reproduction.

## 9. Negotiation behavior

The effective Highway has four controlled CAVs, not one. Negotiation is nevertheless weakly grounded:

- The negotiation object is initialized with `len(env.controlled_vehicles)` and stores that list (`llm_controller/llm_agent_negotiation_system.py:8-16`).
- The Released runner invokes negotiation once every policy cycle before all four ActionAgent decisions.
- For non-intersection scenarios, conflict detection and prompt-scene construction use all `env.road.vehicles`, so all 24 vehicles may appear as candidates (`llm_controller/llm_agent_negotiation_system.py:39-63`, `:142-175`). HDVs remain autonomous environment vehicles; they do not receive ActionAgent decisions and are not independent LLM agents.
- Conflict detection compares sampled routes. Highway creation never calls `plan_route_to`, and `record_route_xy()` returns no route points when a route is absent (`:65-96`, `:128-140`). Consequently, static evidence predicts empty conflict relationships for the default Highway path.
- `send_to_chatgpt()` still constructs and sends the plural traffic-police negotiation prompt even if the conflict list is empty (`:178-197`). Its response is passed to every ActionAgent prompt, although without identified conflicts it is effectively redundant.

This is **STATICALLY SUPPORTED, RUNTIME CONFIRMATION REQUIRED** for the exact empty-conflict output and prompt contents. Stage 1N does not remove the redundant call or contact an LLM.

## 10. Termination contract

`HighwayEnv._is_terminal()` (`highway_env/envs/highway_env.py:113-117`) terminates when:

1. `self.vehicle.crashed` — collision of `self.vehicle`, which resolves to `controlled_vehicles[0]` (`highway_env/envs/common/abstract.py:90-92`); collisions of controlled vehicles 1–3 are not independently checked by this predicate.
2. `self.steps >= self.config["duration"]` — actual boundary 40 policy calls.
3. `offroad_terminal and not self.vehicle.on_road` — disabled by default.

There is no arrival condition. `AbstractEnv.step()` increments `self.steps` once per policy call (`highway_env/envs/common/abstract.py:451-475`) and `_simulate()` executes `15 // 5 = 3` internal simulation substeps (`:520-539`).

The config comment describes duration as seconds, and `AbstractEnv.__init__` computes `T = duration * policy_frequency = 200` (`:69`), but Highway termination does not use `T`. Thus:

- nominal seconds-to-policy conversion: `40 × 5 = 200` policy steps;
- **RELEASED CODE ACTUAL termination boundary: 40 policy steps**, approximately 8 simulated seconds at 5 policy Hz.

Reporting 200 as the executable boundary would contradict the actual predicate.

## 11. Arrival/destination semantics

- Highway vehicle creation does not call `ControlledVehicle.plan_route_to()` (`highway_env/vehicle/controller.py:59-69`). Controlled and background routes remain unset.
- `Vehicle.destination` returns the end of the route when one exists; otherwise it returns the vehicle's current position (`highway_env/vehicle/kinematics.py:219-224`). Treating this fallback as arrival would make a naive destination equality trivially true and is not a defensible success rule.
- Highway does not implement `has_arrived`; only other scenario classes provide scenario-specific arrival predicates.
- Termination neither tests destination nor route endpoint. The 10,000-unit straight road is finite in construction, but reaching its endpoint is not an episode completion condition and is implausible within the actual 40-cycle boundary.
- Current `environment_terminal_reason()` calls `env.has_arrived(...)` for non-Merge scenarios (`scripts/minimal_ollama_full_episode.py:234-252`) and would raise `AttributeError` for Highway at normal termination. `reliable_outcomes()` handles missing arrival only for summary extraction (`:255-274`), not in that terminal-reason path.

Success derivation classification: **C. currently unavailable**. A future executable success metric would require **OUR EXPERIMENT DESIGN** (for destinations/routes and a completion predicate), and that design would not be directly supported by Released Highway fields.

## 12. Seed/randomization contract

`AbstractEnv.reset(is_training=True)` seeds both NumPy and Python `random` from internal `self.seed`, then increments that seed (`highway_env/envs/common/abstract.py:176-200`). The author runner calls `env.reset()` without an explicit seed, so one process starts from configured seed 0 and uses sequential internal seeds 0, 1, … across its 100 repetitions. An explicit test seed path also exists but is not used by the author runner.

`Vehicle.create_random()` (`highway_env/vehicle/kinematics.py:72-98`) establishes:

- controlled lane: randomized because `lane_id=None`;
- controlled longitudinal position: randomized spacing (0.9–1.1 factor), conditional on vehicles already on the lane;
- controlled speed: fixed at 25 because Highway passes `speed=25`;
- background lane/position: randomized through the same helper;
- background speed: randomized from the helper's default speed range (23–25) when no speed is supplied;
- route/destination: not assigned/randomized;
- IDM `randomize_behavior()` is called, but the Released `IDMVehicle.randomize_behavior()` implementation is `pass` (`highway_env/vehicle/behavior.py:56-57`), so it introduces no parameter randomization.

Both NumPy and Python global RNGs are seeded. No statically identified Highway creation randomness escapes those seeds; runtime confirmation remains appropriate for transitive dependency behavior.

| Paper claim | Released implementation | Status |
|---|---|---|
| Random initial positions | Lane and longitudinal placement are seed-driven/randomized, with sequential-spawn constraints. | MATCH (within Released construction) |
| Random initial speeds | Controlled CAV speed is fixed at 25; background speed is randomized only in a narrow default range. | PARTIAL / controlled-speed MISMATCH |
| Random expected destinations | No route or destination assignment; fallback destination is current position. | MISMATCH |
| Different random seeds across 20 repetitions | Runner uses implicit sequential seeds, but runs 100 repetitions and does not record an explicit 20-seed manifest. | PARTIAL |

## 13. Paper-vs-Released gap matrix

| Topic | PAPER EXPLICIT | RELEASED CODE ACTUAL | Gap |
|---|---|---|---|
| Scenario | Four-way Highway | Four parallel straight lanes | Paper topology underspecified; label cannot establish exact graph |
| Agents | Cooperative CAV framework | 4 controlled + 20 IDM vehicles | Counts not stated by paper |
| Control | Not specified | One discrete action consumed; 3 additional LLM decisions ignored | Material executable ambiguity/mismatch |
| Repetitions | 20 | 100 | Mismatch |
| Randomization | positions, speeds, destinations | positions/lanes randomized; controlled speeds fixed; destinations absent | Partial/mismatch |
| Success | all CAVs safe and at destination | first-CAV collision or 40-step timeout; no arrival | Cannot operationalize paper success |
| Model | GPT-4o mini | OpenAI chat path in Released code | Model intent aligns; exact API/config reproducibility incomplete |
| Memory | Highway learning curve reported | object constructed every cycle, retrieval/update commented | Released runner does not implement reported learning behavior |
| Time limit | not specified | actual 40 policy calls despite 40-second comment | Code/comment inconsistency |

## 14. Memory-OFF applicability

Verdict: **READY WITH ORCHESTRATION-ONLY CHANGE for executing the Released behavior; blocked for a defensible formal paper-success experiment.**

The existing OFF path can keep `DrivingMemory` unimported/uninstantiated, avoiding embeddings and Chroma, preserve negotiation → four ActionAgent calls → one `env.step` per policy cycle, and preserve the author tuple behavior. Future orchestration must add Highway scenario selection/config validation, explicitly accept the “only action[0] executes” contract, implement Highway-specific termination labeling at actual step 40, and mark arrival/success unavailable. No Merge/Intersection arrival assumption may be reused.

## 15. Released-style Memory-ON applicability

Verdict: **READY WITH ORCHESTRATION-ONLY CHANGE for technical pipeline execution; not ready as a defensible formal Highway experiment.**

Stage 1H conditionally queries and immediately writes memory once for each entry in `controlled_vehicles` (`llm_controller/llm_agent_action.py:38-56`, `:122-149`). With the effective count of four:

- expected queries per policy cycle: **4**;
- expected writes per successfully completed policy cycle: **4**;
- expected invariant after `N` completed cycles in a fresh/known database: **4 × N new records**, subject to a failure before all four per-agent calls completing;
- query `top_k`: **2**;
- write timing: **pre-step**, immediately after each CAV decision;
- same-cycle cross-CAV visibility: **relevant for database semantics** because later controlled CAVs can see earlier same-cycle writes, although actions 1–3 are not executed by the simulator;
- action usefulness: compromised by the single-action consumption defect.

A future Highway Memory-ON run must use a scenario-isolated persistent namespace/DB. Cumulative cross-seed persistence could reuse the Stage 1H lifecycle only as **OUR EXPERIMENT DESIGN**; the paper does not specify that lifecycle. Stage 1N creates no DB.

## 16. Success metric decision gate

**HIGHWAY_SUCCESS_METRIC_UNAVAILABLE_FROM_RELEASED_FIELDS**

Reason: the paper requires every CAV to safely complete its task and reach its destination, while Released Highway assigns no routes/expected destinations, implements no `has_arrived`, does not terminate on arrival, and exposes a `destination` fallback equal to current position that cannot be interpreted as task completion. Adding a route, endpoint, travel-distance threshold, or timeout-as-success would invent unsupported destination semantics. Formal Highway batch preparation must stop at this gate.

## 17. PET and travel-velocity availability

| Metric | Released availability | Decision |
|---|---|---|
| Success rate | Environment termination/collision fields exist, but no paper-compatible arrival/task-completion field exists. | Unavailable for paper-defined Highway success |
| PET | Not directly computed/logged. Default straight parallel-lane geometry and route-less vehicles do not supply a paper-defined conflict-point/event/aggregation contract. | Unavailable |
| Travel velocity | Instantaneous per-vehicle speeds are available and the author XLSX logger records vehicle state, so a descriptive statistic could be designed. The paper's successful-case filter cannot be reproduced because success is unavailable, and weighting/aggregation is not specified. | Raw speed available; formal paper metric unavailable |

## 18. Current reproduction compatibility

The requested `scripts/run_released_full_episode.py` does not exist at the audited HEAD. The relevant generic implementation is `scripts/minimal_ollama_full_episode.py`.

Hidden assumptions/gaps in that implementation are:

1. `APPROVED_SCENARIOS` contains only Intersection and Merge.
2. It deliberately creates a multi-value tuple from every controlled vehicle; this reproduces the author Highway bug/quirk but does not constitute multi-agent simulator control.
3. Generic non-Merge termination calls missing `env.has_arrived`, so Highway would fail during terminal-reason extraction.
4. Generic reliable-outcome extraction can label arrival unavailable, but success policy is not defined.
5. Existing Memory ON count assumptions in scenario batch audit code may be scenario-specific; Highway's correct Released-style count is four queries/writes per completed cycle, not one.
6. Merge-specific validation, arrival vectors, 200-step conventions, success rules, and batch aggregation must not leak into Highway.

## 19. Minimum future implementation

No implementation is authorized in Stage 1N. If the decision gate is separately resolved, the minimum future work would likely be:

### Modify

- `scripts/minimal_ollama_full_episode.py`: add an explicit Highway scenario adapter/config contract, actual Highway terminal reason, arrival-unavailable handling, and action-consumption disclosure without changing the simulator.
- New Highway-specific batch orchestration/test files: only after an approved success rule and seed protocol exist.
- Documentation/patch register: label all choices as OUR EXPERIMENT DESIGN.

### Add

- A Highway formal protocol document.
- A fixed seed manifest only after protocol approval.
- A Highway Memory-OFF batch runner and pure fake/static tests; later a separate Memory-ON runner/lifecycle if approved.

### Must remain untouched

`Run_multi_CAV_LLM.py`, `highway_env/`, prompt/parser/safety/action mapping, negotiation semantics, `llm_agent_action.py` semantics, `memory.py`, `embedding_backend.py`, requirements, prior raw artifacts/DB, and PaperReconstruction.

If the goal changes from “Released behavior” to genuine four-CAV Highway control or paper-compatible destination completion, then a core semantic change is required and must be separately designed, not hidden inside orchestration.

## 20. Runtime facts still requiring RDP confirmation

No runtime confirmation was performed. Later, non-formal smoke validation would need to confirm:

- effective config values and exact 4+20 identities/order;
- only controlled vehicle 0 responds to a four-entry tuple while entries 1–3 are ignored;
- controlled vehicles 1–3 behavior when not externally acted upon;
- conflict dictionary is empty and negotiation still makes one call per cycle;
- actual termination at policy step 40 and first-controlled-only collision semantics;
- reproducibility of lane/position/background-speed creation under an explicit seed;
- no hidden dependency introduces unseeded randomness;
- Highway-specific orchestration does not call `has_arrived`;
- Memory ON produces four pre-step queries/writes per fully completed cycle and uses an isolated DB.

These checks are not permission to run a Highway episode or create a database.

## 21. Protected-file verification

Stage 1N adds only this documentation file. It does not modify `Run_multi_CAV_LLM.py`, `highway_env/`, controller/memory/embedding semantics, prompts, parser, safety, action mapping, requirements, Stage 1F/1I/1L/1M raw artifacts or DB, or PaperReconstruction. `runs/` remains untracked and untouched.

## 22. Tests

The existing Local suite is to be run with:

```powershell
python -m unittest discover -s tests -p "test_*.py"
```

Observed result on 2026-10-11: **66 tests ran and all passed (`OK`)**. The argparse usage/error text printed during discovery is an expected assertion path in the existing tests; it did not fail the suite. No Highway environment was reset or stepped by Stage 1N, and no new runtime Highway test was added.

## 23. Remaining unresolved items

- Exact paper-author seed values and RNG lifecycle.
- Paper-author Highway lane/count/control topology beyond Figure 4.
- A destination/task-completion predicate derivable without inventing semantics.
- Highway PET conflict definition and aggregation.
- Travel-velocity sampling, weighting, and successful-case filtering.
- Whether reported paper Highway results used code/configuration not present in the Released commit.
- Whether the 40-vs-200 duration inconsistency is accidental.
- Whether the four-decision/first-action-only behavior was used for the paper's Highway results.

## 24. Final verdict

**STAGE_1N_HIGHWAY_CONTRACT_BLOCKED**

The author Released behavior can be described and could later be executed with orchestration-only support, but it cannot currently support a defensible formal paper-success Highway experiment. The blocking decision gate is `HIGHWAY_SUCCESS_METRIC_UNAVAILABLE_FROM_RELEASED_FIELDS`; additionally, the Released topology creates four controlled CAVs while executing only the first tuple action, omits expected destinations, and terminates at 40 policy calls rather than the nominal 200 implied by a 40-second setting at 5 Hz. No Highway seed manifest or batch runner should be created until these issues are explicitly resolved as OUR EXPERIMENT DESIGN or additional author evidence is found.
