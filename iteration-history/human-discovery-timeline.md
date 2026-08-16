# 人类调试痕迹时间线（"华点"分析）

> 分析日期：2026-08-16。数据范围：`git log --no-merges`（author date，2026-06-10 ~ 08-13，HEAD）。本文记录"在 agent 撰写代码的前提下，人类在哪些时间点发现了问题"的判定方法与结果。只读 git 历史产出，不涉及工作树改动。

## 一、判定方法：六类信号

人类发现问题会在历史里留下双份痕迹（当场的行为 + 事后的记录）：

| 信号 | 判定方式 | 实测命中量 |
|---|---|---|
| revert | subject 以 revert 开头 | 27 次 |
| fix 链 | fix again / actually / properly / attempt / redo / re-apply / review round N 等措辞 | 99 次 |
| 发现类措辞 | race / root cause / regression / unexpected / "it turns out" / flaky / leak 等 | 52 次 |
| 快照重录 | re-record / update snapshot / golden | 139 次（07-30 单日 25 次） |
| 搏斗日 | 单模块单日 ≥5 个非 merge 提交（按 hash 去重） | 峰值：ui-conversation 07-30 单日 68 次 |
| 决策笔记 | `.agents/notes/implemented/**` 中标题含 race/fail/leak/crash/wrong/harden/reject/error/ownership 等词 | 66 篇 |

补充：`docs/postmortems` 为空——团队不用正式事故复盘，决策笔记即复盘。

## 二、华点时间轴（人类发现问题的时刻）

- **06-18~06-20 agent 生命周期有竞态**。ownership 契约笔记 + "close the window-2 early-whenIdle race"。发现：取消/卸载语义不能想当然。
- **06-20 日志被 trace 事件撑爆**。"collapse trace-only session events"——第一次意识到日志体积问题。
- **07-09 run_code 卡片标题 bug 的 root cause 在 Zed**。"the run_code program IS the execute-card title (root cause: Zed shows nothing else)"——外部编辑器渲染行为导致 UI 设计失误。
- **07-14 scope 在序列化边界漏了**。revert "share scope carrier across built JSON-RPC"。
- **07-19~20 不变量检查全是形状空转**。"assert runtime relationships, not API shapes"——方法论级修正：之前检查的是 API 形状而非真实运行时关系。
- **07-22 测试绑定 macOS 行为，Linux 上炸**。产出 cross-platform test fixtures 笔记 + "修 fixture，不许修 normalizer"规则。
- **07-27~31 崩溃修复会误伤活着的会话**。"keep crash repair away from live sessions"、"fail fast on an impossible crash marker"、crash marker publication race 一串。
- **07-29 live/replay 等价性声明被证伪**。长 commit 承认 "the live/replay equivalence claim was stated unconditionally but does not cover `tool/call`"，由 bug report 引出；补了 replay-only 分支的说明与 fixture。
- **07-30 agent 改崩了，人还原整棵树**。"revert: restore the reviewer-approved tree"；同天 host 侧评审打到 round 14（"shared hanging-lister fake"）。
- **07-30 原型链污染边角**。"guard langFromPath against Object.prototype extension keys"——典型人工 code review 才能抓到的点。
- **07-31 静默失败会挂死终端**。"fail-loud releases the terminal"——策略转向"宁可大声失败"。
- **08-03 fs 工具错误对模型不可用；调试用不变量不该进发布配置**（fs tool error remedy、omit invariants from shipped config）。
- **08-07 取消语义又藏一个竞态**（cancel-convergence wake latch）——06 月焊到 08 月仍在漏。
- **08-09 preset 组合打破 roster 不变量**（broken preset roster rows）。
- **08-10 旧 runtime 读不了新日志**（session log version mechanism）——发布前最后一颗格式雷。
- **08-12 Windows junction 删不掉**（unlink fixture junctions before delete）——平台兼容最后一颗雷。

## 三、修正叙事：人机工作流的真相

代码侧的弧线（7 个阶段、每周一个主题）是 agent 产出的节奏；人类侧是叠加其上的另一条线：**发现→打回→重来**的脉冲。两个密集纠错段：

1. **07-27~08-01**：跟在 07-30 web 卡片（read/search/plan card）大重做之后；
2. **08-07~08-12**：跟在 08-10 前后命名契约/重组之后。

规律：**大改之后必然跟着人类的密集纠错**。

工作流分工：agent 负责铺，人负责抓错——评审打到第 14 轮、断言方式被推翻、等价性声明被 bug report 证伪、快照重录需要人签字。人类的价值不在写代码，在"这个声明真的成立吗"和"这个边角你试过吗"。

## 四、可复现性

- 信号 1~4：`git log --no-merges --pretty=format:'%H|%ad|%s' --date=short` 后按上表正则过滤。
- 信号 5：`git log --no-merges --name-only --pretty=format:'%H|%ad'`，按"日期+模块"聚合去重。
- 信号 6：文件名正则过滤 `.agents/notes/implemented/**/*.md`。
