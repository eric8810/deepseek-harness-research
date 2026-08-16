# Page 40 视觉复核（最终版：luna 首轮 + sol 裁决 + txt 核实）

- 模型: gpt-5.6-luna（首轮）、gpt-5.6-sol（裁决）
- 状态: 发现问题（33 处行内公式缺词，全部经文本层与 sol 双重确认）

## Display formulas

本页无 display 公式。

## 确认的修正

Page 40 的表格与证明段落中，LlamaParse 把行内公式开头的标识符（dom / id / pr / step / installed / edit / Inactive）丢到了公式外或完全丢失。修正方式：合并回公式内。

| # | 原文（md） | 修正 | 依据 |
|---|---|---|---|
| 1-2 | `dom($F_\gamma$)`（Table 1 O-Insert / O-Remove 行） | `$\operatorname{dom}(F_\gamma)$` | sol 发现；txt: `dom(𝐹𝛾)` |
| 3-13 | `id$_\Gamma$`（表格 Ψ^t 列、L-Divert/L-Raise/L-Leave 行及证明正文） | `$\mathrm{id}_\Gamma$` | txt: `idΓ` |
| 14-16 | `pr$_1 \circ i$`（L-Iter / L-Finish / L-Divert 行及证明正文） | `$\mathrm{pr}_1 \circ i$` | txt: `pr1 ∘ 𝑖` |
| 17-24 | `step$^t$`（Lemma 54 前提及证明） | `$step^t$` | txt: `step𝑡` |
| 25-29 | `$_n^t \wedge$`、`$_n^{t+1} \Rightarrow$`、`$_n$`（installed 蕴含式） | `$installed_n^t \wedge$`、`$installed_n^{t+1} \Rightarrow$`、`$installed_n$` | txt: `installed𝑡𝑛` 等 |
| 30-31 | `$^t \circ \Psi^t$`、`$^t$`（edit 分解） | `$edit^t \circ \Psi^t$`、`$edit^t$` | txt: `edit𝑡 ∘ Ψ𝑡` |
| 32-33 | `$\theta_n \neq -$`（installed_n 定义） | `$\theta_n \ne \mathrm{Inactive}(-)$` | sol 发现；txt: `𝜃𝑛 ≠ 𝖨𝗇𝖺𝖼𝗍𝗂𝗏𝖾(−)` |

## 备注

- 本页是全文唯一此类系统性问题页（全 md 扫描 31 处可疑跨度全在本页；sol 追加 2 处）。
- `Inactive(−)` 中的 − 是占位符，原文如此，非解析错误（Table 1 的 O-Insert 行才是 `Inactive(⊥)`）。
