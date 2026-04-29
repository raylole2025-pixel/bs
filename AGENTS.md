# AGENTS.md

本文件面向后续接手本仓库的大模型/代码代理。它不是用户说明书，而是快速建立项目心智模型、定位改动点、避免误改实验产物的工作指南。

## 项目一句话

BS3 是一个 Python 3.11+ 的两阶段跨域链路规划与滚动调度框架：

- Stage1：面向常态任务，筛选跨域候选窗口，运行 GA/贪心/GRASP 等方法，输出固定的跨域激活计划。
- Stage2：复用 Stage1 的 `selected_plan` 和 `baseline_trace`，插入临机任务，按“直接插入 -> 受限抢占 -> best-effort”处理扰动与恢复。

核心包在 `bs3/`，命令行入口在 `apps/` 和 `tools/`，保留实验结果在 `results/`。

## 先读顺序

1. `README.md`：运行入口、目录摘要、默认路径。
2. `docs/PROJECT_FILE_GUIDE.md`：入口脚本与模块职责总览。
3. `docs/PARAMETER_SETTINGS.md`：当前唯一参数总表，优先于旧参数文档。
4. 本文件：代理协作规则、核心数据流、常见验证方式。

不要一上来全文读取 `inputs/templates/stage1_scenario_template.json` 或 `results/` 下的大 JSON/图片输出；这些文件很大，先按任务定位到具体结果或字段。

## 代码结构

- `bs3/models.py`：核心 dataclass。常见对象包括 `Scenario`、`CandidateWindow`、`ScheduledWindow`、`Task`、`Stage1Result`、`Stage1BaselineTrace`、`Stage2Result`。
- `bs3/scenario.py`：场景 JSON 解析、校验、图构建、路径生成。所有 JSON 场景应通过 `load_scenario()` 进入核心逻辑。
- `bs3/stage1.py`：Stage1 主算法，包含 `Stage1GA`、静态贪心、Geo-LQ 贪心、GRASP multi-start，以及 `run_stage1()` 分发入口。
- `bs3/stage1_static_value.py`：计算候选窗口静态价值 `V_reg` / `V_hot`。
- `bs3/stage1_screening.py`：候选窗口池筛选与粗分段保底。
- `bs3/stage1_taskset_runner.py`：从任务集 JSON 合成 Stage1 场景、距离补全、筛选、运行、导出结果。
- `bs3/stage1_visualization.py`：Stage1 运行产物导出，包括 CSV/PNG。
- `bs3/stage2.py`：Stage2 门面函数 `run_stage2()`，要求传入固定计划或 `Stage1Result`。
- `bs3/stage2_two_phase_scheduler.py`：Stage2 事件驱动临机插入核心实现，文件很长，改动前先用函数/类名定位。
- `bs3/regular_routing_common.py`：Stage1/Stage2 共享的常态任务路由辅助逻辑。
- `bs3/distance_enrichment.py`：用距离时序/汇总数据补全链路距离、时延和权重。
- `bs3/stk_access_preprocess.py`、`bs3/hotspot_builder.py`：STK 预处理与热点生成辅助。

## 主要入口

Stage1 JSON 任务集：

```powershell
python apps/run_stage1_json_taskset.py path/to/regular_tasks.json --seed 7
```

Stage1 -> Stage2 简单管线：

```powershell
python apps/run_scenario_pipeline.py examples/sample_scenario.json --seed 7 --output result.json
```

固定 Stage1 结果 + 临机任务 JSON：

```powershell
python tools/run_stage2_fixed_stage1_smoke.py --base-scenario path/to/scenario.json --stage1-result path/to/stage1_result.json --task-json path/to/mixed_or_emg_tasks.json
```

Stage2 批量临机验证：

```powershell
python tools/run_stage2_emergency_validation.py --scenario path/to/scenario.json --stage1-result path/to/stage1_result.json --suite smoke
```

测试：

```powershell
python -m unittest discover -s tests
```

如果只改了某一块，优先跑对应测试文件，例如：

```powershell
python -m unittest tests.test_stage1_json_taskset_runner
python -m unittest tests.test_stage2_pipeline_smoke
```

## 场景与数据契约

场景 JSON 的关键根字段：

- `nodes.A` / `nodes.B`：两个域的节点集合。
- `capacities.A` / `capacities.B` / `capacities.X`：A 域、B 域和跨域链路统一容量。
- `intra_domain_links[]`：域内时变链路，字段含 `id/u/v/domain/start/end/delay/weight/distance_km`。
- `candidate_windows[]`：候选跨域窗口，字段含 `id/a/b/start/end/value/delay/distance_km`。
- `tasks[]`：任务，字段含 `id/src/dst/arrival/deadline/data/weight/max_rate/type/preemption_priority`，`type` 只能是 `reg` 或 `emg`。
- `stage1`、`stage1.ga`、`stage2`：运行参数。
- `hotspots.A[]`：A 域热点区域，影响 Stage1 热点覆盖约束和候选价值。

约定：

- 时间单位是秒，数据单位通常是 Mb，速率单位通常是 Mbps。
- `load_scenario()` 会校验节点域、时间区间、任务正值、热点权重、Stage1 权重和为 1。
- 若链路/window 有 `distance_km` 且没有显式 `delay`，加载器会用光速折算传播时延。
- `Scenario.metadata["_runtime_cache"]` 是运行期缓存；写出 JSON 前通常要移除，参考 `json_ready_scenario_payload()`。

## Stage1 心智模型

Stage1 的常规流程：

1. 从模板场景和 regular taskset 生成场景 payload。
2. 可选距离补全：默认读取 `mydata/distances/` 下的距离时序和 pair summary。
3. 可选跨域距离硬过滤：默认 `max_cross_distance_km=5000`。
4. 非 `geo_greedy` 方法会计算静态价值并筛选候选窗口。
5. `run_stage1()` 按 `method` 分发到 GA、静态贪心、stop-when-feasible、GRASP 或 Geo-LQ 贪心。
6. 输出 `selected_plan`、`selected_solution`、`best_feasible`、`baseline_trace` 和诊断信息。

当前正式 Stage1 可行性以 `docs/PARAMETER_SETTINGS.md` 为准：

- 硬约束：`FR == 1`、`eta_cap <= theta_cap`、`hotspot_coverage >= theta_hot`。
- 可行解排序重点：`N_act`、`eta_cap`、`hotspot_coverage`。
- 旧字段 `theta`、`theta_sr`、`theta_c`、`near_completion_ratio` 不再生效。

## Stage2 心智模型

Stage2 不重新选择 Stage1 跨域窗口主方案。它读取固定计划：

- `selected_plan`：Stage1 选出的 `ScheduledWindow` 列表。
- `baseline_trace`：Stage1 常态任务基线回放，用于判断可用容量、抢占、恢复和退化。

`run_stage2()` 必须拿到 `plan`、`baseline_trace` 或完整 `stage1_result`。无计划会抛错。Stage2 当前主链是 `run_stage2_two_phase_event_insert()`，不再保留 full MILP / rolling MILP 主链。

输出重点：

- `cr_reg`、`cr_emg`：常态/临机完成率。
- `n_preemptions`：抢占次数。
- `u_cross`、`u_all`：资源利用指标。
- `metadata["emergency_insertions"]`、`metadata["recovery_events"]`：临机插入与恢复诊断。

## 结果与输入目录

- `inputs/templates/stage1_scenario_template.json`：默认 Stage1 基础模板，很大，按需读取。
- `mydata/stk_access/`：原始 STK access 导出。
- `mydata/topology/stage1_preprocess_user/`：预处理后的拓扑、hop matrix、热点摘要。
- `mydata/distances/`：默认距离时序和 pair summary。
- `results/stage1/{light,normal,heavy}` 与 `results/stage2/normal/{smoke,adversarial,stress}`：保留的基准结果。
- `results/stage1/json_taskset_runs/`、`results/stage1/workbook_runs/`、`results/stage2/`：默认新输出位置。

`results/` 中很多内容是实验产物。除非用户明确要求重跑或清理，不要删除、覆盖或批量格式化结果文件。

## 依赖与环境

- `pyproject.toml` 声明 Python `>=3.11`，核心依赖 `networkx>=3.0`。
- 绘图和结果分析脚本还会用到 `matplotlib`、`numpy`。
- workbook 读取逻辑在 `apps/run_stage1_workbook_batch.py` 中使用标准库 `zipfile` 和 XML 解析，不依赖 openpyxl。

## 修改建议

- 改场景解析或数据模型：同步检查 `bs3/models.py`、`bs3/scenario.py`、`scenario_to_dict()` 和相关测试。
- 改 Stage1 指标/参数：先读 `docs/PARAMETER_SETTINGS.md`，再更新 `bs3/models.py`、`bs3/scenario.py`、`bs3/stage1.py`、入口脚本参数和测试。
- 改候选窗口筛选：重点看 `stage1_static_value.py`、`stage1_screening.py`、`stage1_taskset_runner.py` 的调用顺序。
- 改 Stage2 插入策略：先定位 `TwoPhaseEventDrivenScheduler` 里的相关策略函数，再跑 Stage2 smoke 测试和临机输入测试。
- 改 CLI 输出：保持 JSON 字段兼容，尤其是 `selected_plan`、`selected_solution`、`baseline_trace_file`、`baseline_trace`。
- 不要把 `_runtime_cache` 写入持久结果。
- 不要把 `outputs/` 当作新输出目录；当前约定使用 `results/`。

## 当前测试覆盖线索

- `tests/test_stage1_current_logic.py`：Stage1 当前逻辑、指标、排序和基线。
- `tests/test_stage1_json_taskset_runner.py`：JSON taskset runner、Stage1 方法切换、导出契约。
- `tests/test_stage2_pipeline_smoke.py`：Stage1 -> Stage2 基础回放和临机容量策略。
- `tests/test_stage2_emergency_inputs.py`：临机任务输入归一化。
- `tests/test_taskset_workbook.py`：workbook 任务集读取。

改完后至少跑与改动相关的测试；如果涉及核心模型、Stage1/Stage2 交接面或 JSON 契约，跑完整 `python -m unittest discover -s tests`。

