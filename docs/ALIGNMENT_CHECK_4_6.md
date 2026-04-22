# 4.6 对齐检查记录

> 注：该文件保留 4.6 检查记录的文件名。  
> 自 2026-04-08 起，阶段一已进一步按“阶段一4.8”改为 `FR` 方案，不再使用 `theta_sr / theta_c / SR_theta_c`。

对照文件：

- `C:\Users\hai20\Desktop\毕设\阶段一4.6.txt`
- `C:\Users\hai20\Desktop\毕设\阶段二4.6.txt`

检查日期：2026-04-06  
补充更新：2026-04-08

## 阶段一（已由 4.8 方案覆盖）

当前代码的阶段一实现以 4.8 为准：

- 可行性硬约束使用 `FR`、`eta_cap`、`hotspot_coverage`。
- 可行解排序使用 `N_act`、`eta_cap`、`hotspot_coverage`。
- `f_reg` 不再进入正式 fitness。
- 主路 + 瓶颈触发备路（`alpha`）与近优路径阈值（`eta_x`）保留。
- 静态价值 `V_k^(0)` 基于需求强度与可达性权重保留。

4.6 版本中的以下阶段一残留已清理：

- `theta_sr`
- `theta_c`
- `near_completion_ratio`
- `SR_theta_c`
- `sr_theta_c`
- `sr_near`

## 阶段二（4.6 检查项仍有效）

- 模式为“两子模块”：常态基线 + 事件驱动临机插入：已对齐（当前结果标签为 `solver_mode=stage2_emergency_insert`）。
- 阶段二当前只处理临机任务，不再保留 full MILP 或 rolling MILP 主链。
- 临机处理三层流程：无扰动插入 -> 受限单任务抢占 -> best-effort：已对齐。
- 到达时分段切割：已对齐。
- 规划视窗使用 `[arrival, deadline]`：已对齐（未使用旧 insertion horizon）。

## 本次清理的旧残留

- 已删除旧名兼容 wrapper，当前只保留正式入口。
- 二阶段配置模型移除旧字段：
  - `insertion_horizon_seconds`
  - `affected_task_limit`
  - `best_effort_on_failure`
- 删除过时且乱码的旧二阶段参数表文档。
- 新增唯一参数总表：`docs/PARAMETER_SETTINGS.md`。
