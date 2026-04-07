# BS3 参数设置总表（唯一入口）

本文件是当前项目参数的统一入口，覆盖代码默认值、脚本参数默认值和兼容字段。  
更新时间：2026-04-06（对应“阶段一4.6 / 阶段二4.6”对齐检查后）。

## 1. 场景 JSON（核心运行参数）

### 1.1 `stage1` 默认值（来源：`bs3/models.py`）

| 参数 | 默认值 |
| --- | --- |
| `rho` | `0.2` |
| `t_pre` | `1800.0` |
| `d_min` | `600.0` |
| `theta_c` | `0.95` |
| `theta_sr` | `0.90` |
| `theta_cap` | `0.08` |
| `theta_hot` | `0.80` |
| `hot_hop_limit` | `4` |
| `bottleneck_factor_alpha` | `0.85` |
| `eta_x` | `0.90` |
| `static_value_snapshot_seconds` | `600` |
| `q_eval` | `4` |
| `omega_sr` | `4/9` |
| `omega_cap` | `3/9` |
| `omega_hot` | `2/9` |
| `elite_prune_count` | `6` |

### 1.2 `stage1.ga` 默认值（来源：`bs3/models.py`）

| 参数 | 默认值 |
| --- | --- |
| `population_size` | `60` |
| `crossover_probability` | `0.9` |
| `mutation_probability` | `0.2` |
| `max_generations` | `100` |
| `stall_generations` | `20` |
| `top_m` | `5` |
| `max_runtime_seconds` | `null` |

派生值（不可直接配置）：
- `elite_count = ceil(0.1 * population_size)`
- `immigrant_count = ceil(0.1 * population_size)`

### 1.3 `stage2` 默认值（来源：`bs3/models.py`）

| 参数 | 默认值 |
| --- | --- |
| `k_paths` | `2` |
| `completion_tolerance` | `1e-6` |
| `label_keep_limit` | `null`（内部可选） |

派生值（来源：`bs3/models.py`）：
- `effective_label_keep_limit = label_keep_limit or max(8 * k_paths, 1)`

### 1.4 其他核心字段（场景根节点）

| 参数 | 说明 |
| --- | --- |
| `capacities.A/B/X` | A 域、B 域、跨域统一链路容量 |
| `planning_end` | 规划时域终点 |
| `nodes.A/B` | 两域节点集合 |
| `intra_domain_links[]` | 域内时变链路（含 `delay`/`distance_km`） |
| `candidate_windows[]` | 跨域候选窗口（含 `start/end/delay/distance_km/value`） |
| `tasks[]` | 任务集合（`reg`/`emg`） |
| `hotspots.A[]` | A 域热点区域定义 |

## 2. Apps 脚本参数默认值

### 2.1 `apps/run_scenario_pipeline.py`
- `--seed=None`
- `--output=None`

### 2.2 `apps/preprocess_stk_access.py`
- `--output-dir=mydata/topology/stage1_preprocess_user`
- `--snapshot=60`
- `--min-intra=60.0`
- `--min-cross=300.0`
- `--a-planes=5 --a-sats=9`
- `--b-planes=8 --b-sats=10`

### 2.3 `apps/build_stage1_template_from_preprocess.py`
- `--output=inputs/templates/stage1_scenario_template.json`
- `--cap-a=600.0 --cap-b=2000.0 --cap-x=1000.0`
- `--theta=0.90`（兼容别名）
- `--theta-sr=None --theta-cap=0.08 --theta-hot=0.80 --theta-c=0.95`
- `--rho=0.20 --t-pre=1800.0 --d-min=600.0`
- `--hot-hop-limit=4 --alpha=0.85 --eta-x=0.90`
- `--snapshot-seconds=600 --q-eval=4`
- `--omega-sr=4/9 --omega-cap=3/9 --omega-hot=2/9`
- `--elite-prune-count=6`
- `--scenario-name=stage1-from-stk-preprocess`

### 2.4 `apps/run_stage1_workbook_batch.py`
- `--base-scenario=inputs/templates/stage1_scenario_template.json`
- `--output-root=outputs/active/stage1/taskset_runs`
- `--seed=7 --sheets=[medium48,stress96]`
- `--cap-a=600.0 --cap-b=2000.0 --cap-x=1000.0`
- `--theta=0.95 --theta-sr=0.90 --theta-cap=0.08 --theta-hot=0.80 --theta-c=0.95`
- `--rho=0.20 --t-pre=1800.0 --d-min=600.0`
- `--hot-hop-limit=4 --alpha=0.85 --eta-x=0.90`
- `--snapshot-seconds=600 --q-eval=4`
- `--omega-sr=4/9 --omega-cap=3/9 --omega-hot=2/9`
- `--elite-prune-count=6`
- `--population-size=60 --crossover-probability=0.90 --mutation-probability=0.20`
- `--max-generations=100 --stall-generations=20 --top-m=5 --max-runtime-seconds=None`
- `--screen-pool-size=450 --screen-block-seconds=900.0`
- `--run-stage2=False --stage2-k-paths=2`
- `--skip-artifacts=False --disable-distance-enrichment=False`
- 距离文件默认目录：`mydata/distances/*_20260323/*.csv`
- `--light-speed-kmps=299792.458 --intra-proc-delay-sec=0.0002 --cross-proc-delay-sec=0.0010`
- `--max-cross-distance-km=5000.0`

### 2.5 `apps/run_stage2_workbook_sheet.py`
- `--output-root=outputs/active/stage2/taskset_runs`
- `--candidate-index=0`
- `--k-paths=None`（不传则沿用场景 `stage2.k_paths`）

## 3. Tools 脚本参数默认值

### 3.1 `tools/compute_isl_distances.py`
- `--max-distance-km=5000.0`
- `--constellation-id=1 --planes=5 --sats-per-plane=9`
- `--label=domain1`

### 3.2 `tools/compute_cross_domain_link_distances.py`
- 无可选默认项（除必填输入外）

### 3.3 `tools/enrich_scenario_distances.py`
- `--light-speed-kmps=299792.458`
- `--intra-proc-delay-sec=0.0`
- `--cross-proc-delay-sec=0.0`

### 3.4 `tools/compare_stage1_greedy_baselines.py`
- `--seed=7`

## 4. 兼容字段与旧版本残留处理

### 4.1 Stage1 兼容键（读取时仍支持）
- `theta_eta0 -> theta_cap`
- `near_completion_ratio -> theta_c`
- `alpha -> bottleneck_factor_alpha`
- `viol_weight_sr/cap/hot -> omega_sr/cap/hot`

### 4.2 Stage2 兼容行为（对齐 4.6 后）
- 仅保留 `k_paths`、`completion_tolerance`、`label_keep_limit` 作为有效配置键。
- 旧键 `insertion_horizon_seconds`、`affected_task_limit`、`best_effort_on_failure` 不再进入配置模型；即使出现在 JSON 中也会被忽略。

## 5. 与“阶段一4.6 / 阶段二4.6”对齐结论（代码层）

- Stage1 可行性判据：`SR_theta_c`、`eta_cap`、`hotspot_coverage`（已对齐）。
- Stage1 可行解排序优先项：`N_act`、`SR_theta_c`、`eta_cap`、`hotspot_coverage`（已对齐）。
- Stage1 中 `f_reg` 已移除（已对齐）。
- Stage2 运行模式为 `two_phase_event_insert`（已对齐）。
- Stage2 插入流程包含：无扰动插入 -> 受限单任务抢占 -> best-effort（已对齐）。
- 临机任务规划视窗按 `arrival -> deadline` 构建（已对齐）。
