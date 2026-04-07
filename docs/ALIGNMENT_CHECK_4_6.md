# 4.6 对齐检查记录

对照文件：

- `C:\Users\hai20\Desktop\毕设\阶段一4.6.txt`
- `C:\Users\hai20\Desktop\毕设\阶段二4.6.txt`

检查日期：2026-04-06

## 阶段一（4.6）对齐项

- 可行性硬约束使用 `SR_theta_c`、`eta_cap`、`hotspot_coverage`：已对齐。
- 可行解排序使用 `N_act`、`SR_theta_c`、`eta_cap`、`hotspot_coverage`：已对齐。
- `f_reg` 不再进入正式 fitness：已对齐。
- 主路 + 瓶颈触发备路（`alpha`）与近优路径阈值（`eta_x`）：已对齐。
- 静态价值 `V_k^(0)` 基于需求强度与可达性权重：已对齐。

## 阶段二（4.6）对齐项

- 模式为“两子模块”：常态基线 + 事件驱动临机插入：已对齐（`solver_mode=two_phase_event_insert`）。
- 临机处理三层流程：无扰动插入 -> 受限单任务抢占 -> best-effort：已对齐。
- 到达时分段切割：已对齐。
- 规划视窗使用 `[arrival, deadline]`：已对齐（未使用旧 insertion horizon）。

## 本次清理的旧残留

- 重命名为更清晰文件名并保留旧名兼容 wrapper。
- Stage2 配置模型移除旧字段：
  - `insertion_horizon_seconds`
  - `affected_task_limit`
  - `best_effort_on_failure`
- 删除过时且乱码的 `docs/stage2_parameter_table.md`。
- 新增唯一参数总表：`docs/PARAMETER_SETTINGS.md`。
