# stress__default

- case_type: `file_json`
- rho: `default` -> `0.2`
- baseline_source: `stage1_result`
- emergency_count: `20`
- solver_mode: `stage2_emergency_insert`
- cr_reg_before / after: `0.5866666666666667` -> `0.5266666666666666`
- cr_emg: `0.6`
- n_preemptions: `11`
- regular_completion_rate_dropped: `True`
- strict_baseline_degenerate: `False`

## Emergency Diagnostics

- direct_success_task_ids: `EMG_MIX_STR_001, EMG_MIX_STR_002, EMG_MIX_STR_004, EMG_MIX_STR_020`
- controlled_preemption_task_ids: `EMG_MIX_STR_003, EMG_MIX_STR_011, EMG_MIX_STR_013, EMG_MIX_STR_016, EMG_MIX_STR_017, EMG_MIX_STR_018, EMG_MIX_STR_019`
- failed_task_ids: `EMG_MIX_STR_005, EMG_MIX_STR_006, EMG_MIX_STR_007, EMG_MIX_STR_008, EMG_MIX_STR_009, EMG_MIX_STR_010, EMG_MIX_STR_012, EMG_MIX_STR_014`
- degraded_regular_tasks: `N72X_049, N72X_050, N72X_051`
