# repeat-tool-reminder —— 重复工具调用提醒（guard）

本文件是 `@deepseek-ai/dsh-repeat-tool-reminder` 注入给模型的**重复调用提醒**逐字原文，共两档：gentle 首阈值提醒 `GENTLE_REMINDER`（[`index.ts`](../../../../packages/guard/repeat-tool-reminder/src/index.ts#L63)）与 detailed 后续阈值提醒 `detailedReminder`（[`index.ts`](../../../../packages/guard/repeat-tool-reminder/src/index.ts#L69)）。

注入路径：`tools/post-execute` 瀑布监听器在连续相同调用计数命中配置阈值（默认 `[3, 5, 8]`）时，把提醒放进该步决策的 `additionalContexts` 头部（[`index.ts`](../../../../packages/guard/repeat-tool-reminder/src/index.ts#L213)）；循环在该步工具结果之后把它作为注入的 `user/message` 追加进日志。source 为 `{ kind: 'plugin', plugin: 'repeat-tool-reminder', form: 'notice', summary: '<tool> × <count>' }`。被阻止的调用也会收到提醒；guard 从不改写工具结果本身。

## gentle 首阈值提醒（GENTLE_REMINDER）

```text
You are repeating the exact same tool call with identical arguments. Carefully analyze the previous result before calling again: if the task is not complete, try a different approach or different arguments instead of repeating the call.
```

## detailed 后续阈值提醒（detailedReminder(toolName, count, canonicalArguments)）

```text
Repeated tool call detected:
- tool: ${toolName}
- consecutive_calls: ${count}
- arguments: ${canonicalArguments}
The repeated calls are not making progress. Do not call this tool with these exact arguments again. Inspect the latest result and choose a different action, different arguments, or finish the task if enough evidence has been gathered.
```

`${toolName}` / `${count}` / `${canonicalArguments}` 是模板字面量在注入时刻的插值：canonicalArguments 是参数 JSON 深键排序后的字符串，仅其头部 `argumentsPreviewChars`（默认 500）字符进入模型可见文本（[`index.ts`](../../../../packages/guard/repeat-tool-reminder/src/index.ts#L118)）。相关机制见 [context-inventory.md](../context-inventory.md) 的「工具延迟上下文与 post-execute 上下文」一节。
