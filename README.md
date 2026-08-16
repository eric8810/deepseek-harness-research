# DeepSeek Harness Research

这是 [deepseek-harness](https://github.com/deepseek-ai/deepseek-harness) 的 companion 研究仓库，随主仓库检出于其 `docs/research/` 目录。内容为 2026-08-15 ~ 08-16 两天的探索产出：从框架底座到模型上下文拼装、从仓库迭代复盘到 Cordis 论文研读。全部为研究记录，不是官方文档。

## 四层结构

| 层 | 目录 | 内容 |
|---|---|---|
| 框架底座 | [cordis/](cordis/) | vendored Cordis 研究链：机制 → 使用 → 意图 → 管线 → 解剖 → 词汇 → 三轮安全审计 |
| 产品拼装 | [model-context/](model-context/) | 模型上下文拼装逐项拆解：进入模型请求的每一段内容的来源、注册点、拼装时机与最终形态，附逐字 prompt 与代码摘录 |
| 过程复盘 | [iteration-history/](iteration-history/) | 仓库自身迭代的双轨分析：core 组 P0–P6 代码弧线 × 人类「发现→打回→重来」纠错脉冲 |
| 论文研读 | [paper/](paper/) | Cordis 时空可组合性论文：原文（md/pdf）、四模型读后感、14 轮追问式讨论记录、公式全解与逐页勘误 |

## 阅读入口

- 想了解「模型看到的内容由什么保证可审计」：从 [model-context/README.md](model-context/README.md) 入手，这是最完整的一块。
- 想了解底层框架怎么运作：从 [cordis/README.md](cordis/README.md) 入手。
- 想了解 agent 写代码的真实工作流：从 [iteration-history/README.md](iteration-history/README.md) 入手。
- 想了解框架的学术表达及其价值边界：从 [paper/cordis-stc-discussion-record.md](paper/cordis-stc-discussion-record.md) 入手。

## 链接约定

文档中指向主仓库源码与笔记的链接（`../../../packages/...`、`../../../.agents/...` 等）仅当本仓库检出于主仓库的 `docs/research/` 目录时解析；独立 clone 时这些链接无效。仓库内四层之间的相对链接始终有效。
