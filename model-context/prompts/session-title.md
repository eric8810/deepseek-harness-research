# session-title —— 会话标题生成的辅助提示词（session-title-llm）

本文件是 `@deepseek-ai/dsh-session-title-llm` 为**会话标题辅助模型调用**构造的逐字提示词原文，共两块：system 指令 `systemPrompt(config)`（[`index.ts`](../../../../packages/session/session-title-llm/src/index.ts#L186)）与人类消息 JSON 帧 `frameMessages(messages)`（[`index.ts`](../../../../packages/session/session-title-llm/src/index.ts#L196)）。

这是一次不经 agent-loop 的辅助 `ctx.llm.stream()` 调用（`purpose: 'session-title'`），请求事实先以 `session/title-llm-request` 事件落日志（[`index.ts`](../../../../packages/session/session-title-llm/src/index.ts#L262)）；生成的标题文本经 `session/title` 事件发布，不进入模型历史。

## system 指令（systemPrompt(config)）

```text
Create a concise title for an AI coding-assistant session from the supplied human messages.
Return only the title on one line, **in plain text of natural language**, with no quotes, prefix, explanation, Markdown, XML, or terminal control codes. No code is allowed.
Use the language of the messages.
Aim for about ${config.targetWords} words in non-CJK languages or ${config.targetCjkCharacters} CJK characters.
```

`${config.targetWords}` / `${config.targetCjkCharacters}` 是模板字面量在构造时刻的插值（配置为必填正整数）。

## 人类消息 JSON 帧（frameMessages(messages)）

```text
Generate the session title from this JSON array of human messages:
${JSON.stringify(messages)}
```

`${JSON.stringify(messages)}` 是所选 `SessionTitleUserMessage` 子集的 JSON 序列化（按 UTF-8 字节数受 `maxInputBytes` 上限约束，[`index.ts`](../../../../packages/session/session-title-llm/src/index.ts#L240)）。两条消息的 `source` 均为 `{ kind: 'plugin', plugin: 'dsh-session-title-llm' }`（[`index.ts`](../../../../packages/session/session-title-llm/src/index.ts#L246)）。

调度与消息收集见 [context-inventory.md](../context-inventory.md) 的「辅助 LLM 调用（非 loop 请求）」一节。
