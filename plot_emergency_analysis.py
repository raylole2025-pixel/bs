import json
import os
import matplotlib.pyplot as plt
import numpy as np

# 配置支持中文字体显示
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'SimSun', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

# 配置输出目录
out_dir = r'd:\Codex_Project\bs_1.0_4.22\results\dataset_analysis'
os.makedirs(out_dir, exist_ok=True)

# 基础常态任务集 (作为背景对比)
normal_path = r'd:\Codex_Project\bs_1.0_4.22\results\stage1\normal\normal_tasks.json'

# 临机任务集路径 (Stage 2)
emg_base_dir = r'd:\Codex_Project\bs_1.0_4.22\results\stage2\normal'
smoke_path = os.path.join(emg_base_dir, 'smoke', 'emergency_tasks.json')
stress_path = os.path.join(emg_base_dir, 'stress', 'emergency_tasks.json')
adv_path = os.path.join(emg_base_dir, 'adversarial', 'emergency_tasks.json')

def load_tasks(path):
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        # 有些可能是 {"tasks": [...]} 的结构，有些是直接的列表
        return data.get('tasks', []) if isinstance(data, dict) else data

# 加载数据
normal_tasks = load_tasks(normal_path)
datasets = {
    'EMG1': load_tasks(smoke_path),
    'EMG2': load_tasks(adv_path),
    'EMG3': load_tasks(stress_path)
}

# 统一颜色
colors = {'EMG1': '#ff7f0e', 'EMG2': '#9467bd', 'EMG3': '#d62728'}

print(f"Normal tasks: {len(normal_tasks)}")
print(f"EMG1 (Smoke) tasks: {len(datasets['EMG1'])}")
print(f"EMG2 (Adversarial) tasks: {len(datasets['EMG2'])}")
print(f"EMG3 (Stress) tasks: {len(datasets['EMG3'])}")

# ==========================================
# 图1: 突发时间聚集度 (Arrival Burstiness) - 散点图
# ==========================================
print("1. 生成突发时间聚集度散点图...")
plt.figure(figsize=(12, 6))

# 绘制常态任务 (浅色背景)
normal_arrivals = [t['arrival'] for t in normal_tasks]
normal_mbps = [t['avg_required_Mbps'] for t in normal_tasks]
plt.scatter(normal_arrivals, normal_mbps, color='lightgray', label='Normal72 (常态任务)', alpha=0.6, s=30)

# 绘制临机任务
for name, tasks in datasets.items():
    if not tasks: continue
    arrivals = [t['arrival'] for t in tasks]
    mbps = [t['avg_required_Mbps'] for t in tasks]
    plt.scatter(arrivals, mbps, label=name, color=colors[name], alpha=0.9, s=80, edgecolors='white')

plt.xlabel('到达时间 Arrival Time (s)')
plt.ylabel('带宽需求 (Mbps)')
plt.title('常态任务与临机任务的到达分布及带宽需求对比')
plt.legend()
plt.grid(True, linestyle='--', alpha=0.5)
plt.tight_layout()
plt.savefig(os.path.join(out_dir, '6_emg_burstiness.png'), dpi=300)
plt.close()

# ==========================================
# 图2: 时间窗紧迫性对比 (Deadline Tightness) - 散点密度图
# ==========================================
print("2. 生成时间窗紧迫性散点图...")
plt.figure(figsize=(10, 6))

# 常态任务时间窗
normal_windows = [t['deadline'] - t['arrival'] for t in normal_tasks]
plt.scatter(normal_windows, normal_mbps, color='lightgray', label='Normal72 (常态任务)', alpha=0.6, s=30)

# 临机任务时间窗
for name, tasks in datasets.items():
    if not tasks: continue
    windows = [t['deadline'] - t['arrival'] for t in tasks]
    mbps = [t['avg_required_Mbps'] for t in tasks]
    plt.scatter(windows, mbps, label=name, color=colors[name], alpha=0.9, s=80, edgecolors='white', marker='^')

plt.xlabel('时间窗长度 Deadline - Arrival (s)')
plt.ylabel('带宽需求 (Mbps)')
plt.title('常态任务与临机任务的时间窗及带宽需求对比')
plt.axvline(x=2000, color='red', linestyle='--', alpha=0.3, label='紧迫边界线') # 假设2000s为一个较紧迫的边界
plt.legend()
plt.grid(True, linestyle='--', alpha=0.5)
plt.tight_layout()
plt.savefig(os.path.join(out_dir, '7_emg_tightness.png'), dpi=300)
plt.close()

# ==========================================
# 图3: 动态带宽冲击效应 (Dynamic Bandwidth Impact) - 堆叠面积图
# ==========================================
print("3. 生成动态带宽冲击效应图...")
max_time = max(max(t['deadline'] for t in normal_tasks), 
               max(max([t['deadline'] for t in tasks] + [0]) for tasks in datasets.values()))
times = np.arange(0, max_time + 100, 100)

fig, axes = plt.subplots(3, 1, figsize=(12, 10), sharex=True, sharey=True)
fig.suptitle('临机任务对系统常态带宽需求的动态冲击对比', fontsize=16)

# 预先计算常态带宽需求
normal_bw = [sum(t['avg_required_Mbps'] for t in normal_tasks if t['arrival'] <= time <= t['deadline']) for time in times]

for i, (name, tasks) in enumerate(datasets.items()):
    ax = axes[i]
    if not tasks:
        ax.text(0.5, 0.5, f"No tasks found for {name}", ha='center', va='center', transform=ax.transAxes)
        continue
        
    emg_bw = [sum(t['avg_required_Mbps'] for t in tasks if t['arrival'] <= time <= t['deadline']) for time in times]
    
    # 绘制基础常态面积
    ax.fill_between(times, 0, normal_bw, color='#1f77b4', alpha=0.5, label='Normal72 常态负载')
    # 绘制叠加的紧急任务面积
    total_bw = [n + e for n, e in zip(normal_bw, emg_bw)]
    ax.fill_between(times, normal_bw, total_bw, color=colors[name], alpha=0.8, label=f'{name} 突发冲击')
    
    ax.set_ylabel('带宽需求 (Mbps)')
    ax.legend(loc='upper right')
    ax.grid(True, linestyle='--', alpha=0.5)

axes[-1].set_xlabel('仿真时间 (s)')
plt.tight_layout(rect=[0, 0.03, 1, 0.95]) # 调整布局以适应主标题
plt.savefig(os.path.join(out_dir, '8_emg_impact.png'), dpi=300)
plt.close()

print(f"\n临机任务分析图表已成功生成并保存在: {out_dir}")
