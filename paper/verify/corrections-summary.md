# 公式校验汇总报告

论文: *A Programming Paradigm for Spatiotemporal Composability*（88 页，2026-08-13 草案）
解析产物: `papers/cordis-spatiotemporal-composability.md`（LlamaParse agentic 层）
**最终版**: `papers/cordis-spatiotemporal-composability.verified.md`（所有已确认修正 + 格式化清理，原始 md 未动）

## 方法

1. **自动对账**：PDF 自带文本层（txt，字形级精确）与 md 的 LaTeX 逐页符号比对 → `report-reconciliation.md`
2. **视觉复核**：46 个公式密集页逐页渲染（170 DPI）→ gpt-5.6-luna 逐页核对 display/inline 公式 → `corrections/page-NN.md`
3. **裁决**：luna 发现问题的 6 页交给 gpt-5.6-sol 二次确认，所有修正再用 txt 文本层逐条核实

## 确认的错误（共 6 页，37 处）

| 页 | 位置 | 原文（md，错） | 修正 | 确认方式 |
|---|---|---|---|---|
| 7 | 公式 (2) | `...`（三个句点） | `\ldots` | luna + sol |
| 18 | Definition 24 | `\cong_k`（2 处） | `\simeq_k` | luna + sol + txt（≃） |
| 25 | Theorem 40 证明 | `V_k` | `\mathcal{V}_k` | luna + sol + txt（𝒱） |
| 40 | Table 1 + Lemma 54 证明 | 33 处行内公式开头缺词（dom/id/pr/step/installed/edit/Inactive） | 见 `corrections/page-40.md` 明细表 | luna + sol + txt |
| 46 | claim (2) 证明 | `\theta_m^{b'}` | `\theta_n^{b'}` | luna + sol + txt（𝜃𝑛） |
| 51 | 5.1 证明 | `\epsilon^{t+1}` | `edit^{t+1}` | luna + sol + txt（edit𝑡+1） |

页 40 占 33 处，是唯一的系统性失败页（表格+密集行内公式导致 LlamaParse 丢词）。

## 复核为正确的部分

- 其余 40 个公式密集页：display 公式全部 OK，inline 数学无错误
- 对账报告中其余符号差异（`\neq`/`\mid`/`⊨`/上下标/`≔`/`\longrightarrow`）均为字体映射与表示方式差异，非解析错误（详情见 `report-reconciliation.md` 与复核过程中的逐页核实）

## 与公式正确性无关、但建议处理的格式化问题

- `\eqno(N)` 共 42 处：纯 LaTeX 原文残留，KaTeX/MathJax 不支持 → 已在最终版全部改为 `\tag{N}` ✓
- 每页残留的页码裸行和 `---` 分页线 → 已在最终版移除 ✓
- 第 1 页页眉 "deepseek logo" 文本 → 已在最终版移除 ✓

以上修正均通过 `papers/merge.py` 应用（带计数断言），生成 `papers/cordis-spatiotemporal-composability.verified.md`，原始 md 全程未改动。合并时可重跑 `merge.py` 或在最终版基础上手工审阅 diff。
