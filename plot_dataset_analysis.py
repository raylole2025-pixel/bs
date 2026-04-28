import json
import os
import matplotlib.pyplot as plt
import numpy as np

# 配置支持中文字体显示 (使用系统自带的黑体或雅黑)
plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'SimSun', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False # 正常显示负号

# 配置输出目录
out_dir = r'd:\Codex_Project\bs_1.0_4.22\results\dataset_analysis'
os.makedirs(out_dir, exist_ok=True)

# 任务集文件路径
light_path = r'd:\Codex_Project\bs_1.0_4.22\results\stage1\light\Light60_tasks.json'
normal_path = r'd:\Codex_Project\bs_1.0_4.22\results\stage1\normal\normal_tasks.json'
heavy_path = r'd:\Codex_Project\bs_1.0_4.22\results\stage1\heavy\Heavy84_tasks.json'

def load_tasks(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

# 加载数据 (保留数据集原始英文名称)
datasets = [
    ('Light60', load_tasks(light_path)),
    ('Normal72', load_tasks(normal_path)),
    ('Heavy84', load_tasks(heavy_path))
]

# 统一配色方案
colors = ['#2ca02c', '#1f77b4', '#d62728'] # 绿, 蓝, 红

# 确定统一的时间轴范围
max_time = max(max(t['deadline'] for t in tasks) for _, tasks in datasets)
times = np.arange(0, max_time + 100, 100)

print("1. 生成并发度折线图...")
plt.figure(figsize=(10, 5))
for (name, tasks), color in zip(datasets, colors):
    concurrency = [sum(1 for t in tasks if t['arrival'] <= time <= t['deadline']) for time in times]
    plt.plot(times, concurrency, label=name, color=color, linewidth=2, alpha=0.8)
plt.xlabel('仿真时间 (s)')
plt.ylabel('活跃任务数 (并发度)')
plt.title('任务并发度随时间变化趋势')
plt.legend()
plt.grid(True, linestyle='--', alpha=0.7)
plt.tight_layout()
plt.savefig(os.path.join(out_dir, '1_concurrency_zh.png'), dpi=300)
plt.close()

print("2. 生成带宽需求堆叠面积图 (总量对比)...")
plt.figure(figsize=(10, 5))
for (name, tasks), color in zip(datasets, colors):
    bw = [sum(t['avg_required_Mbps'] for t in tasks if t['arrival'] <= time <= t['deadline']) for time in times]
    plt.plot(times, bw, label=name, color=color, linewidth=2, alpha=0.8)
    plt.fill_between(times, bw, alpha=0.2, color=color)
plt.xlabel('仿真时间 (s)')
plt.ylabel('总带宽需求 (Mbps)')
plt.title('系统总带宽需求随时间变化趋势')
plt.legend()
plt.grid(True, linestyle='--', alpha=0.7)
plt.tight_layout()
plt.savefig(os.path.join(out_dir, '2_bandwidth_demand_zh.png'), dpi=300)
plt.close()

# 用户说1、2、4、5比较好，图3（箱线图）可以选择性生成或不生成，我们继续生成但转中文
print("3. 生成任务时间窗分布箱线图...")
plt.figure(figsize=(8, 6))
time_windows = [[t['deadline'] - t['arrival'] for t in tasks] for _, tasks in datasets]
bp = plt.boxplot(time_windows, tick_labels=[name for name, _ in datasets], patch_artist=True)
for patch, color in zip(bp['boxes'], colors):
    patch.set_facecolor(color)
    patch.set_alpha(0.6)
for median in bp['medians']:
    median.set(color='black', linewidth=2)
plt.ylabel('时间窗长度 (s)')
plt.title('任务时间窗分布对比')
plt.grid(True, axis='y', linestyle='--', alpha=0.7)
plt.tight_layout()
plt.savefig(os.path.join(out_dir, '3_time_windows_zh.png'), dpi=300)
plt.close()

print("4. 生成任务类型分布簇状柱状图...")
plt.figure(figsize=(8, 6))
classes = ['A', 'B', 'C']
x = np.arange(len(classes))
width = 0.25

for i, ((name, tasks), color) in enumerate(zip(datasets, colors)):
    counts = [sum(1 for t in tasks if t.get('task_class') == c) for c in classes]
    plt.bar(x + (i - 1) * width, counts, width, label=name, color=color, alpha=0.8)

plt.xlabel('任务优先级类型 (Class)')
plt.ylabel('任务数量 (个)')
plt.title('各测试集任务类型分布对比')
plt.xticks(x, classes)
plt.legend()
plt.grid(True, axis='y', linestyle='--', alpha=0.7)
plt.tight_layout()
plt.savefig(os.path.join(out_dir, '4_task_classes_zh.png'), dpi=300)
plt.close()

print("5. 生成总体规模对比图...")
fig, ax1 = plt.subplots(figsize=(8, 6))
names = [name.split(' ')[0] for name, _ in datasets]
task_counts = [len(tasks) for _, tasks in datasets]
# data 的单位是 Mb (Megabits)，转换为 GB (Gigabytes): / 8 / 1024
total_data = [sum(t['data'] for t in tasks) / 8192 for _, tasks in datasets] 

x = np.arange(len(names))
width = 0.35

bar1 = ax1.bar(x - width/2, task_counts, width, label='常态任务数量 (左轴)', color='#1f77b4')
ax1.set_ylabel('常态任务数量 (个)', color='#1f77b4')
ax1.tick_params(axis='y', labelcolor='#1f77b4')
ax1.set_xticks(x)
ax1.set_xticklabels(names)

ax2 = ax1.twinx()
bar2 = ax2.bar(x + width/2, total_data, width, label='总数据量 (右轴)', color='#ff7f0e')
ax2.set_ylabel('总数据量 (GB)', color='#ff7f0e')
ax2.tick_params(axis='y', labelcolor='#ff7f0e')

plt.title('常态任务集规模对比')
# 合并图例
lines, labels = ax1.get_legend_handles_labels()
lines2, labels2 = ax2.get_legend_handles_labels()
ax2.legend(lines + lines2, labels + labels2, loc='upper left')

fig.tight_layout()
plt.savefig(os.path.join(out_dir, '5_overall_scale_zh.png'), dpi=300)
plt.close()

print(f"\n所有中文图表已成功生成并保存在: {out_dir}")
