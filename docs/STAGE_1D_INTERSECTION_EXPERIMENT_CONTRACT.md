# Stage 1D — Intersection Reproduction Experiment Contract

## 0. 文件狀態與證據邊界

- 正式專案：`C:\Thesis\CoDrivingLLM-ReleasedReproduction`
- 審核基準：作者 Released commit `f9e71fed08c1772cf4009ed61dfe91177019cf7d`
- 本文件建立時工作 branch：`codex/released-reproduction`
- 本文件建立前 HEAD：`cfc92bf89d974e7c5160c6d6fb305fdd2c3cce48`
- 本階段僅做 read-only audit 與 protocol documentation；未修改 Python、未呼叫 Ollama、未執行 simulator。
- 已知 RDP seed 0 單回合成功只證明 runner 可完成一次 episode，不是論文數值復現證據。

證據優先序為：(1) Paper；(2) pinned Released Code；(3) tracked released artifacts；(4) 現行 reproduction runner。任何由本團隊補定、但論文未明文規定的控制條件，一律標示 **OUR EXPERIMENT DESIGN**。

行號皆指 pinned commit 的檔案內容；未查得的設定標成 `UNRESOLVED`，不以推測補齊。

## 1. Paper Intersection experiment specification

### 1.1 明確證據索引

| Paper location | 原文所支持的內容（意譯） | 明確性 | 是否需推論 |
|---|---|---:|---:|
| Sec. IV-A, printed p.11900（PDF p.7）, Experiment Settings | 模擬環境基於 highway-env；四種情境包含 single-lane unsignalized intersection、roundabout、four-way highway、merge。 | 明確 | 否 |
| Sec. IV-A, printed p.11900（PDF p.7） | base LLM 為 GPT-4o mini。 | 明確 | 否 |
| Sec. IV-A, printed p.11900（PDF p.7） | 所有情境以不同 random seeds 重複 20 次，用以隨機產生車輛初始位置、速度與預期目的地。 | 明確 | 否；但種子值與清單未提供 |
| Sec. IV-A, printed p.11900（PDF p.7） | 所有方法皆以 success rate 為評估指標；success 定義為所有 CAV 安全完成任務並抵達目的地。 | 明確 | 否 |
| Fig. 5 / Sec. IV-B, printed p.11900（PDF p.7） | Intersection reasoning-module ablation 比較 without state-sharing、without intent-sharing、without negotiation 與完整 CoDrivingLLM。 | 明確 | 否；這不是 Memory ON/OFF |
| Fig. 7 / Sec. IV-C, printed p.11902（PDF p.9） | Memory module 隨 interaction 數（0、5、10、20+）增加的 performance evaluation；文字主張 interactions 增加時 success rate 改善。 | 明確 | 若解讀成 matched Memory OFF/ON 則需要、且缺乏依據 |
| Fig. 8 / Sec. IV-C, printed p.11902（PDF p.9） | 一個 intersection case 比較 without memory 與 with memory 的決策結果。 | 明確 | 若推廣成多回合統計 ablation 則需要、且不成立 |
| Sec. IV-D / Table I, printed pp.11902–11903（PDF pp.9–10） | Intersection 與 FCFS、iDFST、MCTS、Cooperative Game、MADQN、Dilu 比較；報告 success rate。 | 明確 | 否 |
| Sec. IV-D / Tables II–III, printed p.11903（PDF p.10） | 僅成功案例納入 safety/efficiency；safety 用 PET 的 average/max/min，efficiency 用 travel velocity 的 average/max/min。 | 明確 | PET 的完整計算/聚合實作仍未提供 |
| Fig. 9 / Sec. IV-D, printed p.11903（PDF p.10） | 顯示 PET 分布；文字將 PET < 1.5 s 稱為 severe conflict。 | 明確 | 否 |

### 1.2 Paper 沒有明確給出的項目

- 20 個 random seed 的實際值、排列與 seed manifest。
- Intersection 的 CAV 數字（Sec. IV-A 未明文列出數量；不可只由圖示推定）。
- 每個 ablation panel / memory interaction level 是否各自恰為 20 episodes；Sec. IV-A 的總括敘述支持「各情境 20 repeats」，但未逐項說明其套用方式。
- Memory 條件之間是否使用完全相同的 seeds、模型採樣狀態或 matched initial states。
- Memory database 的 reset、預熱、累積與跨回合保存邊界。
- GPT-4o mini 的完整 model revision、temperature、seed、API 版本與其他 sampling 參數。
- episode reward、episode steps、runtime、LLM calls、token usage 並非 Sec. IV 所列論文評估指標。

## 2. Released Code actual experiment behavior

### 2.1 主迴圈與 episode lifecycle

`Run_multi_CAV_LLM.py` 的可驗證行為：

1. line 54 建立 `intersection-multi-agent-v0`。
2. line 58 執行 `for i in range(100)`；每次迭代配置一個輸出 workbook/video。
3. line 64 呼叫 `env.reset()`；line 65 進入 `while not terminated`。
4. 每個 policy cycle 先建立/呼叫 negotiation（lines 71–72），再對 CAV 執行 action decision（lines 75–77），flatten joint action（line 80），最後只呼叫一次 `env.step(tuple(action), env)`（line 85）。
5. lines 86、90、101 有 render/video 副作用；每 cycle 記錄車輛 `t, x, y, v, theta, background_veh?` 至 xlsx。

所以 pinned code 可確定的是：在沒有例外且每回合自然結束的前提下，外層嘗試 100 次 reset/episode loop。它沒有保存明確 seed manifest，也沒有宣告這 100 次等同 Paper 的 20 evaluation trials。

### 2.2 Intersection termination 與 reward

`highway_env/envs/intersection_env.py`：

- lines 98–103：termination 條件包含 controlled vehicle collision、所有 controlled vehicles 到達、`steps >= duration * policy_frequency - 1`，以及（若設定啟用）off-road。
- default `duration=50`，policy frequency 繼承為 5，因此時間上限條件是 `steps >= 249`；這是 simulator implementation，不是 Paper 明列的 trial protocol。
- lines 71–85：reward 是 controlled vehicles 個別 reward 的 cooperative average，包含 collision/high-speed/arrival components。
- lines 279–282：arrival 由 `has_arrived()` 的 lane/longitudinal position 實作判定。
- lines 208–216：建立 controlled vehicles 前，background traffic 先進行 3 秒 simulation warm-up。這是 reset/scene construction 的 simulator 副作用，不是 LLM policy cycle，也不應被 batch runner 額外重複。

### 2.3 Released artifacts 與 aggregation

- tracked raw xlsx 每個 vehicle sheet 紀錄 `t, x, y, v, theta, background_veh?`，不是完整 experiment manifest。
- `results_summary.xlsx` 的欄位為 file、vehicle sheet pair、兩個 time、time difference、兩個 conflict points；它顯示曾有離線衝突彙整，但 repository 未找到可追溯產生它的 aggregation Python script，也不足以證明 Paper PET 的完整公式與納入規則。
- tracked Intersection folders包含 `0shot`、`2shot`、`5shot`、`AUCTION`、`DQN`、`FIFO`、`no-negotiation`；檔案數量不一致，不能直接反推一個統一、完整的論文 trial manifest。
- 原始 runner 未建立 Paper Table I–III 所需的完整成功率/PET/速度統計報表。

## 3. Episode count evidence

| Evidence | 可安全宣稱 | 不可宣稱 |
|---|---|---|
| Paper Sec. IV-A | 每個情境使用不同 random seeds 重複 20 次。 | seed 值；所有 ablation level 必然各 20 次；與 Released 100-loop 相同。 |
| `Run_multi_CAV_LLM.py:58` | code 固定進入 `range(100)`；正常完成時意圖執行 100 個外層 episode iterations。 | 這 100 次是 Paper trials、100 個預先定義 seeds、或論文 Table 的直接來源。 |
| tracked artifacts | 部分資料夾有 20 個 numbered raw workbooks，另有不完整或額外檔案。 | 每個資料夾都是完整 matched 20-trial experiment；檔名必然等於 environment seed。 |

結論：Paper protocol 的數量是 **20 repeats per scenario**；Released entry script 的實際控制流是 **100 loop iterations**。兩者不一致，且不能透過重新命名互相等同。

## 4. Seed progression

### 4.1 實際程式路徑

`highway_env/envs/common/abstract.py`：

- default config `seed=0`（line 128）。
- constructor 設 `self.np_random=np.random` 與 `self.seed=config["seed"]`（lines 44–52），並在 construction 過程呼叫一次 `reset()`（line 87）。
- `reset(is_training=True)`（lines 176–200）以 `self.seed` 同時 seed NumPy global RNG 與 Python `random`（lines 183–185），再令 `self.seed += 1`（line 191）並建立場景。
- `testing_seeds` 只有 `is_training=False` 分支才會使用；原始 runner 的 `env.reset()` 未傳 `False`，故不使用 testing seed list。
- `intersection_env.py` 的初始位置、目的地、background vehicle spawn 與 behavior randomization 使用上述 RNG（例如 lines 223–229、244–269）。

### 4.2 預設 progression（implicit，不是明示 manifest）

| 時點 | reset 使用的 environment seed | reset 後 `self.seed` | 場景是否進入外層 episode |
|---|---:|---:|---|
| `gym.make(...)` 內 constructor reset | 0 | 1 | 否；隨後被 runner reset 取代 |
| outer loop `i=0` reset | 1 | 2 | 是 |
| outer loop `i=1` reset | 2 | 3 | 是 |
| … | … | … | … |
| outer loop `i=99` reset | 100 | 101 | 是 |

因此在預設建構、無額外 reset 且不中斷的條件下，原始 100-loop episode 場景推得使用 seeds **1…100**。這是由 implementation control flow 推導的 implicit progression，不是 Paper 提供的 explicit seed list。

### 4.3 determinism 邊界

- environment seed 控制 simulator 使用的 NumPy/Python RNG；同 seed 有助重建 initial scene。
- 它不控制遠端 GPT/Ollama 生成、server/model revision、sampling、並行與硬體差異。
- 所以相同 environment seed 不代表整個 LLM-driven episode deterministic；完整紀錄至少還需 model identity、backend、sampling configuration、Git commit、environment versions 與原始輸出。

## 5. Memory ON/OFF evidence

### 5.1 Paper specification

- Algorithm 1 lines 10–11 描述 relevant memory retrieval；line 16 描述評估 interaction impact 並加入 memory database。
- Sec. III 描述 retrieval 與累積過往經驗的 database。
- Sec. IV-C Fig. 7 是不同 interaction counts 的 memory performance；Fig. 8 是單一 case 的 without/with memory 對照。
- Paper 沒有提供可直接執行的 binary Memory ON/OFF matched protocol，也沒有明文給出相同 seeds、DB lifecycle 或每個條件的完整 episode manifest。

### 5.2 Released implementation

- `Run_multi_CAV_LLM.py:68` 在**每個 policy cycle**建立 `DrivingMemory(env)`，不是只在 episode 邊界建立。
- `llm_controller/memory.py` constructor 立即建立 `OpenAIEmbeddings` 與 persistent Chroma，路徑為 `./db/<env.spec.id>`；資料可跨 object、cycle、episode，甚至跨 process run 保存，除非外部刪除。
- `llm_controller/action.py:159–160` 將 retrieval 呼叫註解並設 `past_memory=''`。
- controller 的 memory update 呼叫亦被註解（line 46）。
- 因而 active Released path 是「Memory infrastructure 被初始化，但 retrieval OFF、update OFF」；repository 沒有可直接切換、實驗隔離明確的 Memory ON/OFF runner。

### 5.3 Current reproduction 與未來設計

- Stage 1C Memory-OFF runner 傳 `memory=None`，不 import/instantiate `DrivingMemory`，藉此避免 OpenAIEmbeddings/Chroma/DB side effects；這是 **ADAPTATION**，不是原作者 active entry script 的原貌。
- 未來 Memory ON protocol 在 retrieval/update semantics 與 DB lifecycle 尚未經人工定義及實作前，不得聲稱已重現 Paper memory experiment。
- 若要比較 ON/OFF，使用相同 seed manifest、隔離 DB、記錄 prepopulation 與更新順序，均屬 **OUR EXPERIMENT DESIGN**。

## 6. Metrics evidence

| Metric | Paper 定義 | Released Code 有無 | 可直接取得 | 需要後處理 | Fidelity |
|---|---|---|---:|---:|---|
| Success rate | 所有 CAV 安全完成任務並到達目的地的 trials 比率 | 無 batch aggregate；termination/arrival/collision primitives 有 | 單回合基礎狀態可取 | 是 | PARTIAL / UNRESOLVED aggregation |
| Collision rate | 未作為 Table I 獨立主指標；success 定義含安全 | `vehicle.crashed`、`cav_crashed` info | 是 | 若報率則是 OUR EXPERIMENT DESIGN | UNRESOLVED paper definition |
| Arrival | success 定義的一部分 | `has_arrived()`、all-arrived termination | 是 | 成功判定需組合 collision | MATCH at primitive level |
| Episode reward | Paper Sec. IV 未列 | simulator reward 有 | 是 | sum/mean protocol需定義 | IMPLEMENTATION_ONLY |
| Episode steps | Paper Sec. IV 未列 | simulator `steps` 有 | 是 | 否 | IMPLEMENTATION_ONLY |
| Travel time | Paper 文字討論通行效率，但 Tables 報 travel velocity | raw `t` 可見；無完整 aggregate contract | 部分 | 是 | UNRESOLVED |
| Average speed / travel velocity | Table III 報成功 cases 的 average/max/min travel velocity | raw per-vehicle `v` 有；abstract env 中 average-speed info 被註解 | raw 可取 | 是；公式/權重需釐清 | UNRESOLVED |
| Efficiency | Sec. IV-D 以 travel velocity 評估 | 無論文同等 aggregator | 否 | 是 | PAPER_ONLY / UNRESOLVED |
| Safety / PET | Table II 報成功 cases PET average/max/min；PET <1.5 s severe conflict | tracked summary 有 time difference/conflict points，無產生 script及完整公式 | 不能可靠直接取得論文值 | 是 | UNRESOLVED |
| LLM calls | Paper 未列為 evaluation metric | 原 entry script無可靠 aggregate | runner可觀測時計數 | 可選 | IMPLEMENTATION_ONLY |
| Token usage | Paper 未列 | 無 | 否 | backend需額外支援 | IMPLEMENTATION_ONLY |
| Runtime | Paper 未列為主評估 metric | 無正式 aggregate | runner wall-clock可取 | 可選 | IMPLEMENTATION_ONLY |
| Memory retrieval/update | Paper演算法描述 retrieval/update | active calls被註解；DB仍初始化 | active call count 可判為 0 | Memory ON 未實作 | PAPER_ONLY / implementation gap |

注意：表中 `PARTIAL` 是文字說明，不是下一節 classification vocabulary。不得自行建立 PET、efficiency 或 success 的新公式來填補 `UNRESOLVED`。

## 7. Paper vs Released Code matrix

| Experiment Item | Paper | Released Code | Current Reproduction | Classification |
|---|---|---|---|---|
| Scenario | single-lane unsignalized intersection | `intersection-multi-agent-v0` | 同 Released env | MATCH |
| Number of CAVs | Sec. IV-A 未明文數字 | multi-agent config `controlled_vehicles=4` | 4 | UNRESOLVED |
| Number of episodes | 20 repeats per scenario | `range(100)` | 現有 full-episode runner一次一回合 | UNRESOLVED |
| Seed | different random seeds；值未列 | implicit constructor/reset progression；預設 episodes 1…100 | CLI explicit `--seed` | ADAPTATION |
| Episode termination | 未提供完整程式條件 | collision / all arrived / duration / optional off-road | 沿用 env termination，另有 max-steps guard | ADAPTATION |
| Memory | Paper描述 retrieval/update與interaction study | DB infrastructure 初始化，但 retrieval/update calls OFF | Memory OFF=`None`，避免初始化 | ADAPTATION |
| Model | GPT-4o mini | OpenAI chat path/model設定 | Ollama `qwen2.5:7b` | MODEL_SUBSTITUTION |
| Prompt | CoDrivingLLM prompt pipeline | released prompt字串 | 保持 released prompt | MATCH |
| Negotiation | reasoning/negotiation framework | released negotiation module | 重用同 module | MATCH |
| Safety | framework safety/action checking | released safety implementation | 重用同 implementation | MATCH |
| Metrics | success；成功 cases PET與travel velocity | raw state/reward與少量 summary artifacts，無完整論文 aggregator | runner紀錄 reward/steps/termination與可得狀態 | UNRESOLVED |
| Result aggregation | Tables/Figures 報跨 trials 統計 | 未找到可重建 Tables I–III 的 tracked script | 尚無 batch aggregation | PAPER_ONLY |
| 100-loop/video/xlsx side effects | 未規定 | 原 entry script實作 | minimal runner改用隔離 JSON output | IMPLEMENTATION_ONLY |

## 8. Qwen2.5:7b model substitution implications

目前可以宣稱：

> Released implementation pipeline reproduction with local LLM substitution.

目前不可宣稱：

> numerical reproduction of the paper.

原因是 Paper 使用 GPT-4o mini，而現行 backend/model 是 Ollama `qwen2.5:7b`；模型、sampling 與服務條件皆可能改變 negotiation、parsed action、episode trajectory 和最終統計。此差異固定分類為 `MODEL_SUBSTITUTION`。不得為了靠近論文數值而調整 prompt、parser、fallback、safety 或 action mapping；那會混入演算法變更且破壞 Released-Code fidelity。

## 9. Protocol A — Released-Code Fidelity（建議，不實作）

目標是盡量忠實呈現 pinned implementation，而不是冒充 Paper 20-trial protocol。

1. 固定並保存 pinned source commit、branch、dirty state、Python/package versions、OS、model/backend完整 identity。
2. 保留 original sequential-reset semantics；若從乾淨 process/default seed 啟動，記錄 constructor seed 0 被消耗，以及 episodes 預期 seed 1…100。這個 manifest 是 implementation-derived，不是 Paper seed list。
3. 保留 negotiation → action decisions → joint `env.step(tuple(action), env)`，每 policy cycle 一次 step；不新增 fallback/retry。
4. 清楚選定是否重現原 entry script 的 render、MP4、xlsx 與 `DrivingMemory` 初始化副作用。若為可靠性移除，逐項標 `ADAPTATION`。
5. 原始 active memory semantics 應記作 retrieval OFF / update OFF，但 infrastructure initialization ON；不要稱為 Paper Memory OFF。
6. 逐回合隔離輸出並保存 failure/traceback；失敗回合不替補、不靜默重跑。
7. 報告 100 attempted iterations、completed、failed 與 termination reasons，不把 100 自稱 Paper trials。

其中輸出隔離、manifest、failure policy 與 metadata schema 均為 **OUR EXPERIMENT DESIGN**；只服務可稽核性，不改決策語意。

## 10. Protocol B — Controlled Thesis Reproduction（建議，不實作）

目標是在 Qwen2.5:7b/Ollama 下建立可重複的本研究 baseline。

1. **OUR EXPERIMENT DESIGN**：先採 20-entry explicit seed manifest，以對齊 Paper 的 repeat count；seed值由研究者凍結並版本化，不宣稱是作者原 seeds。
2. **OUR EXPERIMENT DESIGN**：所有比較條件使用相同 manifest、相同 episode order、相同 simulator/package versions。
3. model 固定 `qwen2.5:7b`、記錄 Ollama/model digest、endpoint、sampling options 與 timeout；持續標記 `MODEL_SUBSTITUTION`。
4. Memory OFF 使用已驗證的 `memory=None` 隔離；Memory ON 在另階段完成明確的 retrieval/update、prepopulation、DB reset/persistence contract 後才可納入。
5. **OUR EXPERIMENT DESIGN**：每個 condition/run 使用全新 output directory；metadata、step records、summary、traceback 皆原子化保存，不覆寫。
6. **OUR EXPERIMENT DESIGN**：backend/parser/simulator error 視為 failed trial，不 retry、不替代 action；分母與排除規則須在執行前凍結。
7. success 僅依 Paper文字與 simulator可靠 primitives判定：所有 controlled CAV arrived 且無 controlled CAV collision；max-steps/runtime error 不算 environment success。
8. Paper PET/velocity aggregate 在公式、sampling unit、成功-case filter與權重釐清前標 `UNRESOLVED`；先保存足夠 raw trajectory，不先捏造指標。
9. 統計同時呈現 attempted/completed/success/failed counts、success rate，以及模型與條件；不以單一 seed 0 成功代表整體 performance。

## 11. Remaining unresolved questions / gates

1. Paper 使用的 20 個 seed 值與順序是什麼？
2. 「所有情境重複20次」是否逐一套用每個 reasoning ablation、memory interaction level與comparison method？
3. Paper Intersection 精確 CAV 數與 simulator commit/config 是什麼？
4. GPT-4o mini 的確切 snapshot與sampling參數是什麼？
5. Fig. 7 的 0/5/10/20+ interaction 如何建立、累積與清空 memory DB？各 level 有多少 trials，是否 matched seeds？
6. Table II PET 的完整演算法、vehicle-pair納入規則、時間單位/頻率與跨 episode aggregation 為何？
7. Table III travel velocity 是按 timestep、vehicle、episode或成功 trial 如何加權？
8. tracked `results_summary.xlsx` 的產生程式、版本與資料完整性為何？
9. Paper success 分母如何處理 API/parser/runtime failure？未敘明。

這些問題阻止「論文數值復現」宣稱，但不阻止下一階段設計一個明確標示 adaptation/model substitution 的 batch runner。

## 12. Batch-runner design readiness decision

結論：**READY_FOR_BATCH_RUNNER_DESIGN**。

理由：已足以凍結兩條互不混淆的設計路徑：Protocol A 重現 Released 100-loop implementation semantics；Protocol B 以 Paper 明文的 20 repeats 為數量基礎，另用 **OUR EXPERIMENT DESIGN** 固定 manifest 與可稽核失敗規則。尚未解決的 PET/velocity 公式、作者 seed 清單與 Memory ON lifecycle 必須保留為 gates，因此目前只適合「設計」batch runner，不代表已可宣稱 Paper numerical reproduction，也不授權執行 batch experiments。
