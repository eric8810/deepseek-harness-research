# Cordis 框架研究

本目录是对 DeepSeek Harness 框架底座——vendored Cordis——从机制到安全审计的完整研究链：机制 → 使用 → 意图 → 管线 → 解剖 → 词汇 → 审计。全部笔记基于对 `vendor/`、`packages/` 源码与 Agent Notes 的只读分析，产出日期 2026-08-15 ~ 08-16。

## 阅读顺序

| 顺序 | 文档 | 内容 |
|---|---|---|
| 1 | [core-model.md](core-model.md) | 机制：ctx 是什么、store/bus 两种台面交互、fiber 生命周期与重载规则，一页架构 |
| 2 | [business-usage.md](business-usage.md) | 使用：harness 如何从空树拼出插件树（补丁层语义）、业务插件长什么样、模块间依赖设计 |
| 3 | [design-rationale.md](design-rationale.md) | 意图：从使用代码反推的十条设计原则（会话日志唯一事实源、能力缝三段式、策略是插件等），每条附官方依据 |
| 4 | [runtime-pipeline.md](runtime-pipeline.md) | 管线：一次工具调用经过的五道门、六层分层原因、循环驱动 |
| 5 | [agent-loop.md](agent-loop.md) | 解剖：agent loop 的依赖清单、kick → turn → step 驱动循环、工具调度 |
| 6 | [llm-vocabulary.md](llm-vocabulary.md) | 词汇：LLM 缝的三个 merge-extensible 联合（ContentBlock / FinishReason / MessageSource） |
| 7 | [audit-wave1-2026-08-15.md](audit-wave1-2026-08-15.md) | 审计第一波：六 agent 方向性安全审查（威胁模型 + Critical/High 发现） |
| 8 | [audit-wave2-2026-08-15.md](audit-wave2-2026-08-15.md) | 审计第二波：逐文件穷尽 + 二轮对抗 + 不可信输入可达性 |
| 9 | [audit-wave3-2026-08-15.md](audit-wave3-2026-08-15.md) | 审计第三波：端到端裁决（修正前两波结论）+ 模糊测试新发现 |

## 链接约定

笔记中指向主仓库源码的链接（`../../../vendor/...`、`../../../packages/...`、`../../../.agents/...`）指向 [deepseek-harness](https://github.com/deepseek-ai/deepseek-harness) 主仓库文件，仅当本仓库检出于主仓库的 `docs/research/` 目录时解析；独立 clone 时这些链接无效。
