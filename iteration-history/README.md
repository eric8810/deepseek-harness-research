# 迭代历史分析（Iteration History）

本目录是 DeepSeek Harness 仓库同一段 git 历史（2026-06-10 → 2026-08-13，author date）的两条互补观察线：**代码侧的迭代弧线**与**人类侧的纠错脉冲**，外加两者的共享数据源。全部文档只读 git 历史与仓库内既有文档产出，不包含对工作树的改动。

## 两条观察线

| 文档 | 观察对象 | 结论 |
|---|---|---|
| [core-iteration-analysis.md](core-iteration-analysis.md) | `packages/core` 组（含扁平布局祖先与已移出的历史包）的 886 条提交 | P0–P6 七个阶段：从「先立门禁」到「日志唯一事实来源」到「发布前规范化」，附关键 commit 索引与反复回炉点 |
| [human-discovery-timeline.md](human-discovery-timeline.md) | 人类发现问题的时刻（revert、fix 链、快照重录、搏斗日、决策笔记六类信号） | 「发现→打回→重来」脉冲；大改之后必然跟着人类密集纠错，峰值 07-27~08-01 与 08-07~08-12 |

两篇互为对照面：[human-discovery-timeline.md](human-discovery-timeline.md) 的「修正叙事」以本目录 [core-iteration-analysis.md](core-iteration-analysis.md) 的七阶段弧线为 agent 侧节奏基准，叠加人类侧脉冲后得到完整的工作流图景。

## 数据

[module-iteration-stats.csv](module-iteration-stats.csv) 是全仓库模块级的提交统计（Func/Maint 二分、周分布、首末提交日期），由 `git log` 生成；[core-iteration-analysis.md](core-iteration-analysis.md) 用它对 core 组做交叉校验。

## 方法口径

两篇的时间窗口与数据源一致，但分类口径不同：`core-iteration-analysis.md` 按提交消息关键词做功能/维护二分（631 功能 vs 505 维护的差异来源见其「备注（不确定性）」节），`human-discovery-timeline.md` 按六类「人类发现问题」信号聚合。口径差异不影响各自结论。
