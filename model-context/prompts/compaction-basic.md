# Compaction 摘要提示词（compaction-basic）

来源：[summarizer.ts](../../../../packages/compaction/compaction-basic/src/summarizer.ts) 的 `COMPACTION_INSTRUCTION` 数组（第 31–66 行），元素以 `'\n'` 连接（第 66 行）。该指令不是独立的 summarizer system prompt，而是作为重放会话之后、最后一条 `user/message` 的内容送入模型（[summarizer.ts#L24](../../../../packages/compaction/compaction-basic/src/summarizer.ts#L24)）。

## 指令原文（COMPACTION_INSTRUCTION，summarizer.ts:31-66）

```text
You are now acting as a compaction engine for this AI coding assistant. Condense the conversation ABOVE into a structured checkpoint that lets another model resume the work with no loss of essential context.

Output EXACTLY the Markdown structure below: keep every section, in order. Use terse bullets, not prose paragraphs. Write "(none)" for an empty section — never drop a section.

## Primary Request and Intent
- [the user's original and evolving goals; quote verbatim where the exact wording matters]

## Key Technical Concepts
- [technologies, frameworks, patterns, and conventions in play]

## Files and Code
- [exact path: why it matters, key changes or snippets]

## Errors and Fixes
- [error: how it was resolved, plus any related user feedback]

## Pending Jobs
- [explicitly requested work not yet completed]

## Current Work
- [precisely what was in progress at this checkpoint]

## Next Step
- [the single next action, directly in line with the most recent request, or "(none)"]

## Critical Context
- [decisions and their rationale, constraints, user preferences, open questions, data needed to continue]

Rules:
- Write concise English engineering prose. Preserve exact file paths, commands, error strings, identifiers, numeric values, function signatures, and syntax fragments.
- Capture user feedback and explicit instructions faithfully, especially corrections.
- Do NOT mention this summarization request or that the context was compacted.
- Output only the checkpoint text: do not call any tool or take any other action.
- If the conversation already contains a <compacted-summary> block, it is a PRIOR checkpoint. Do not copy it forward verbatim: preserve still-true facts, drop stale ones, and merge newer information into a single consolidated summary under the same structure.
```

源码第 65 行是模板字符串，`${SUMMARY_OPEN_TAG}` 在运行时替换为 `<compacted-summary>`（[summarizer.ts#L21](../../../../packages/compaction/compaction-basic/src/summarizer.ts#L21)），上面的最后一条 Rules 已作此展开。

## 替换节点框架（frameSummary，summarizer.ts:189-195）

落地到日志的 checkpoint user 消息内容 = `CHECKPOINT_PREAMBLE` + 空行 + `<compacted-summary>` + 摘要文本 + `</compacted-summary>`（[summarizer.ts#L189](../../../../packages/compaction/compaction-basic/src/summarizer.ts#L189)）。`frameSummary` 的实现为：前导块 `{ type: 'text', text: CHECKPOINT_PREAMBLE + '\n\n' + SUMMARY_OPEN_TAG }`，中间是摘要块，末尾块 `{ type: 'text', text: SUMMARY_CLOSE_TAG }`。

### CHECKPOINT_PREAMBLE（summarizer.ts:69-70）

```text
This is an automatically generated checkpoint condensing an earlier span of the conversation to free up context. Treat the captured context as established background and build on it without restating it. Continue the task directly from the messages that follow, without acknowledging this checkpoint.
```

## 标签

`<compacted-summary>` / `</compacted-summary>`（[summarizer.ts#L21](../../../../packages/compaction/compaction-basic/src/summarizer.ts#L21)、[summarizer.ts#L22](../../../../packages/compaction/compaction-basic/src/summarizer.ts#L22)）。

## 生成机制要点

- 调用为一次 `ctx.llm.stream(options)`，`options` 携带 `maxTokens`（默认 8192，[config.ts#L91](../../../../packages/compaction/compaction-basic/src/config.ts#L91)）、`sessionId`、`purpose: 'compaction'`，并把调用方信号转发给流（[summarizer.ts#L153](../../../../packages/compaction/compaction-basic/src/summarizer.ts#L153)）。
- 目标模型解析顺序：显式 `summarizationProvider`/`summarizationModel` 配置 → 最新路由请求（`requestHeader()`）→ AgentOptions（[summarizer.ts#L128](../../../../packages/compaction/compaction-basic/src/summarizer.ts#L128)）。
- 输出只保留文本块，`contentHasImage` 时抛 `LlmError('UNSUPPORTED_CONTENT')`（[summarizer.ts#L217](../../../../packages/compaction/compaction-basic/src/summarizer.ts#L217)）；finish 为 `max-tokens` 时抛截断错误（[summarizer.ts#L198](../../../../packages/compaction/compaction-basic/src/summarizer.ts#L198)）。
- 摘要内容随后被验证必须小于被遮蔽内容（`estimateMessage(checkpoint) < shadowedTokenCount`），否则整个压缩事务失败（[region.ts#L373](../../../../packages/compaction/compaction-basic/src/region.ts#L373)）。
